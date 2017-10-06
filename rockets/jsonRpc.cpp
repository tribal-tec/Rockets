/* Copyright (c) 2017, EPFL/Blue Brain Project
 *                     Raphael.Dumusc@epfl.ch
 *
 * This file is part of Rockets <https://github.com/BlueBrain/Rockets>
 *
 * This library is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License version 3.0 as published
 * by the Free Software Foundation.
 *
 * This library is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
 * details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

#include "jsonRpc.h"

#include "jsoncpp/json/json.h"

#include <map>

namespace rockets
{
namespace
{
const std::string reservedMethodPrefix = "rpc.";
const char* reservedMethodError =
    "Method names starting with 'rpc.' are "
    "reserved by the standard / forbidden.";

Json::Value _parse(const std::string& json)
{
    Json::Value document;
    const auto builder = Json::CharReaderBuilder();
    auto reader = std::unique_ptr<Json::CharReader>{builder.newCharReader()};
    reader->parse(json.c_str(), json.c_str() + json.size(), &document, nullptr);
    return document;
}

std::string to_string(const Json::Value& json)
{
    auto factory = Json::StreamWriterBuilder();
    factory["indentation"] = "    ";
    factory["enableYAMLCompatibility"] = true;
    return Json::writeString(factory, json);
}

Json::Value makeParseErrorObject()
{
    auto error = Json::Value{Json::objectValue};
    error["code"] = -32700;
    error["message"] = "Parse error";
    return error;
}

Json::Value makeInvalidRequestObject()
{
    auto error = Json::Value{Json::objectValue};
    error["code"] = -32600;
    error["message"] = "Invalid Request";
    return error;
}

Json::Value makeMethodNotFoundObject()
{
    auto error = Json::Value{Json::objectValue};
    error["code"] = -32601;
    error["message"] = "Method not found";
    return error;
}

Json::Value _makeJsonRpcObject()
{
    auto response = Json::Value{Json::objectValue};
    response["jsonrpc"] = "2.0";
    return response;
}

Json::Value _makeErrorResponse(const Json::Value& error,
                               const Json::Value& id = Json::Value())
{
    auto response = _makeJsonRpcObject();
    response["error"] = error;
    response["id"] = id;
    return response;
}

Json::Value _makeErrorResponse(const int code, const std::string& message,
                               const Json::Value& id = Json::Value())
{
    auto error = Json::Value{Json::objectValue};
    error["code"] = code;
    error["message"] = message;
    return _makeErrorResponse(error, id);
}

Json::Value _makeResponse(const std::string& result, const Json::Value& id)
{
    auto response = _makeJsonRpcObject();
    response["result"] = result;
    response["id"] = id;
    return response;
}

bool _isValidJsonRpcRequest(const Json::Value& object)
{
    const auto params = object["params"];
    return object["jsonrpc"].asString() == "2.0" &&
           object["method"].isString() &&
           (params.isNull() || params.isObject() || params.isArray()) &&
           (object["id"].isNull() || object["id"].isDouble() ||
            object["id"].isString());
}

inline bool begins_with(const std::string& string, const std::string& other)
{
    return string.compare(0, other.length(), other) == 0;
}
} // anonymous namespace

class JsonRpc::Impl
{
public:
    std::string processBatchBlocking(const Json::Value& array)
    {
        if (array.empty())
            return to_string(_makeErrorResponse(makeInvalidRequestObject()));

        return to_string(processValidBatchBlocking(array));
    }

    Json::Value processValidBatchBlocking(const Json::Value& array)
    {
        Json::Value responses;
        for (const auto& entry : array)
        {
            if (entry.isObject())
            {
                const auto response = processCommandBlocking(entry);
                if (!response.empty())
                    responses.append(response);
            }
            else
                responses.append(
                    _makeErrorResponse(makeInvalidRequestObject()));
        }
        return responses;
    }

    Json::Value processCommandBlocking(const Json::Value& request)
    {
        auto promise = std::make_shared<std::promise<Json::Value>>();
        auto future = promise->get_future();
        auto callback = [promise](Json::Value response) {
            promise->set_value(std::move(response));
        };
        processCommand(request, callback);
        return future.get();
    }

    void processCommand(const Json::Value& request,
                        std::function<void(Json::Value)> callback)
    {
        if (!_isValidJsonRpcRequest(request))
        {
            callback(_makeErrorResponse(makeInvalidRequestObject()));
            return;
        }

        const auto id = request["id"];
        const auto methodName = request["method"].asString();
        const auto params = to_string(request["params"]);

        const auto method = methods.find(methodName);
        if (method == methods.end())
        {
            callback(_makeErrorResponse(makeMethodNotFoundObject(), id));
            return;
        }

        const auto& func = method->second;
        func(params, [callback, id](const JsonRpc::Response rep) {
            // No reply for valid "notifications" (requests without an "id")
            if (id.isNull())
            {
                callback(Json::Value());
                return;
            }

            if (rep.error != 0)
                callback(_makeErrorResponse(rep.error, rep.result, id));
            else
                callback(_makeResponse(rep.result, id));
        });
    }
    std::map<std::string, JsonRpc::ResponseCallbackAsync> methods;
};

JsonRpc::JsonRpc()
    : _impl{new Impl}
{
}

JsonRpc::~JsonRpc()
{
}

void JsonRpc::bind(const std::string& method, ResponseCallback action)
{
    bindAsync(method,
              [this, action](const std::string& req, AsyncResponse callback) {
                  callback(action(req));
              });
}

void JsonRpc::bindAsync(const std::string& method, ResponseCallbackAsync action)
{
    if (begins_with(method, reservedMethodPrefix))
        throw std::invalid_argument(reservedMethodError);

    _impl->methods[method] = action;
}

void JsonRpc::notify(const std::string& method, NotifyCallback action)
{
    bind(method, [action](const std::string& request) {
        action(request);
        return JsonRpc::Response{"OK"};
    });
}

void JsonRpc::notify(const std::string& method, VoidCallback action)
{
    bind(method, [action](const std::string&) {
        action();
        return JsonRpc::Response{"OK"};
    });
}

std::string JsonRpc::process(const std::string& request)
{
    return processAsync(request).get();
}

std::future<std::string> JsonRpc::processAsync(const std::string& request)
{
    auto promise = std::make_shared<std::promise<std::string>>();
    auto future = promise->get_future();
    auto callback = [promise](std::string response) {
        promise->set_value(std::move(response));
    };
    process(request, callback);
    return future;
}

void JsonRpc::process(const std::string& request, ProcessAsyncCallback callback)
{
    const auto document = _parse(request);
    if (document.isObject())
    {
        auto stringifyCallback = [callback](const Json::Value obj) {
            callback(to_string(obj));
        };
        _impl->processCommand(document, stringifyCallback);
    }
    else if (document.isArray())
        callback(_impl->processBatchBlocking(document));
    else
        callback(to_string(_makeErrorResponse(makeParseErrorObject())));
}
}
