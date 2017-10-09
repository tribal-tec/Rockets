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

#include "client.h"

namespace rockets
{
namespace jsonrpc
{
Client::Client(ws::Client& client)
    : communicator{client}
{
    client.handleText([this](std::string message) {
        if (!processResponse(message))
        {
            process(std::move(message), [this](std::string response) {
                // TODO may not be thread-safe
                communicator.sendText(std::move(response));
            });
        }
        return std::string();
    });
}

void Client::_emit(std::string json)
{
    communicator.sendText(std::move(json));
}

void Client::_request(std::string json)
{
    communicator.sendText(std::move(json));
}
}
}