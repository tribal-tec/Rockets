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

#ifndef ROCKETS_JSONRPC_CLIENT_H
#define ROCKETS_JSONRPC_CLIENT_H

#include <rockets/jsonrpc/emitter.h>
#include <rockets/jsonrpc/receiver.h>
#include <rockets/jsonrpc/requester.h>

namespace rockets
{
namespace jsonrpc
{
/**
 * JSON-RPC client.
 *
 * The client can be used over any communication channel that provides the
 * following methods:
 *
 * - void sendText(std::string message);
 *   Used to send notifications and requests to the server.
 *
 * - void handleText(ws::MessageCallback callback);
 *   Used to register a callback for processing the responses from the server
 *   when they arrive (non-blocking requests) as well as receiving
 *   notifications.
 */
template <typename Communicator>
class Client : public Emitter, public Receiver, public Requester
{
public:
    Client(Communicator& comm)
        : communicator{comm}
    {
        communicator.handleText([this](std::string message) {
            if (!processResponse(message))
            {
                process(std::move(message), [this](std::string response) {
                    if (!response.empty())
                        communicator.sendText(std::move(response));
                });
            }
            return std::string();
        });
    }

private:
    void _sendNotification(std::string json) final
    {
        communicator.sendText(std::move(json));
    }
    void _sendRequest(std::string json) final
    {
        communicator.sendText(std::move(json));
    }
    Communicator& communicator;
};
}
}

#endif
