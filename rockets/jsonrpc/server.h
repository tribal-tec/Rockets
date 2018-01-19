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

#ifndef ROCKETS_JSONRPC_SERVER_H
#define ROCKETS_JSONRPC_SERVER_H

#include <rockets/jsonrpc/emitter.h>
#include <rockets/jsonrpc/receiver.h>
#include <rockets/ws/types.h>

#include <iostream>

namespace rockets
{
namespace jsonrpc
{
/**
 * JSON-RPC server.
 */
template <typename ServerT>
class Server : public Emitter, public Receiver
{
public:
    Server(ServerT& server)
        : communicator{server}
    {
        communicator.handleText(
            [this](std::string message, ws::ResponseCallback callback) {
                process(std::move(message), callback);
            });
    }

private:
    void _emit(std::string json) final
    {
        communicator.broadcastText(std::move(json));
    }
    ServerT& communicator;
};
}
}

#endif
