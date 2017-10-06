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

#include "jsoncpp/json11.hpp"

using namespace json11;

#include <map>

namespace rockets
{
namespace
{
const std::string reservedMethodPrefix = "rpc.";
const char* reservedMethodError =
    "Method names starting with 'rpc.' are "
    "reserved by the standard / forbidden.";

Json makeParseErrorObject()
{
    return Json::object{{"code", -32700}, {"message", "Parse error"}};
}

Json makeInvalidRequestObject()
{
    return Json::object{{"code", -32600}, {"message", "Invalid Request"}};
}

Json makeMethodNotFoundObject()
{
    return Json::object{{"code", -32601}, {"message", "Method not found"}};
}

Json _makeErrorResponse(const Json& error, const Json& id = Json())
{
    return Json::object{{"jsonrpc", "2.0"}, {"error", error}, {"id", id}};
}

Json _makeErrorResponse(const int code, const std::string& message,
                        const Json& id = Json())
{
    return Json::object{{"jsonrpc", "2.0"},
                        {"code", code},
                        {"message", message},
                        {"id", id}};
}

Json _makeResponse(const std::string& result, const Json& id)
{
    return Json::object{{"jsonrpc", "2.0"}, {"result", result}, {"id", id}};
}

bool _isValidJsonRpcRequest(const Json& object)
{
    const auto params = object["params"];
    return object["jsonrpc"].string_value() == "2.0" &&
           object["method"].is_string() &&
           (params.is_null() || params.is_object() || params.is_array()) &&
           (object["id"].is_null() || object["id"].is_number() ||
            object["id"].is_string());
}

inline bool begins_with(const std::string& string, const std::string& other)
{
    return string.compare(0, other.length(), other) == 0;
}
} // anonymous namespace

class JsonRpc::Impl
{
public:
    std::string processBatchBlocking(const Json& array)
    {
        if (array.array_items().empty())
            return _makeErrorResponse(makeInvalidRequestObject()).dump();

        return processValidBatchBlocking(array).dump();
    }

    Json processValidBatchBlocking(const Json& array)
    {
        std::vector<Json> responses;
        for (const auto& entry : array.array_items())
        {
            if (entry.is_object())
            {
                const auto response = processCommandBlocking(entry);
                if (!response.is_null())
                    responses.push_back(response);
            }
            else
                responses.push_back(
                    _makeErrorResponse(makeInvalidRequestObject()));
        }
        return Json{responses};
    }

    Json processCommandBlocking(const Json& request)
    {
        auto promise = std::make_shared<std::promise<Json>>();
        auto future = promise->get_future();
        auto callback = [promise](Json response) {
            promise->set_value(std::move(response));
        };
        processCommand(request, callback);
        return future.get();
    }

    void processCommand(const Json& request, std::function<void(Json)> callback)
    {
        if (!_isValidJsonRpcRequest(request))
        {
            callback(_makeErrorResponse(makeInvalidRequestObject()));
            return;
        }

        const auto id = request["id"];
        const auto methodName = request["method"].string_value();
        const auto params = request["params"].dump();

        const auto method = methods.find(methodName);
        if (method == methods.end())
        {
            callback(_makeErrorResponse(makeMethodNotFoundObject(), id));
            return;
        }

        const auto& func = method->second;
        func(params, [callback, id](const JsonRpc::Response rep) {
            // No reply for valid "notifications" (requests without an "id")
            if (id.is_null())
            {
                callback(Json());
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
    std::string err;
    const auto document = Json::parse(request, err);
    if (document.is_object())
    {
        auto stringifyCallback = [callback](const Json obj) {
            callback(obj.dump());
        };
        _impl->processCommand(document, stringifyCallback);
    }
    else if (document.is_array())
        callback(_impl->processBatchBlocking(document));
    else
        callback(_makeErrorResponse(makeParseErrorObject()).dump());
}
}
