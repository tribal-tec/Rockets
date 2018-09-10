#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2018, Blue Brain Project
#                     Daniel Nachbaur <daniel.nachbaur@epfl.ch>
#
# This file is part of Rockets <https://github.com/BlueBrain/Rockets>
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License version 3.0 as published
# by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
# All rights reserved. Do not distribute without further notice.

import json
from typing import Any

from websockets import WebSocketCommonProtocol  # type: ignore

from jsonrpcclient.async_client import AsyncClient
from jsonrpcclient.response import Response


class WebSocketsClient(AsyncClient):
    def __init__(
        self, socket: WebSocketCommonProtocol, *args: Any, **kwargs: Any
    ) -> None:
        """
            socket: Connected websocket (websockets.connect("ws://localhost:5000"))
            *args: Passed through to Client class.
            **kwargs: Passed through to Client class.
        """
        super().__init__(*args, **kwargs)
        self.socket = socket

    async def send_message(self, request: str, **kwargs: Any):  # type: ignore
        await self.socket.send(request)

        # json_request = json.loads(request)
        # if not 'id' in json_request:
        #     return None

        done = False
        while not done:
            response_text = await self.socket.recv()
            if isinstance(response_text, (bytes, bytearray)):
                continue
            json_response = json.loads(str(response_text))
            if 'method' in json_response and 'progress' in json_response['method']:
                print(json_response['params']['amount'])
            else:
                return Response(response_text)
