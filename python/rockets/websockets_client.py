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
from typing import Any, Dict, Iterator, List, Optional, Union
from jsonrpcclient.parse import parse


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

    async def send(
        self,
        request: Union[str, Dict, List],
        trim_log_values: bool = False,
        validate_against_schema: bool = True,
        **kwargs: Any
    ) -> Response:
        """
        Async version of Client.send.
        """
        # Convert the request to a string if it's not already.
        request_text = request if isinstance(request, str) else json.dumps(request)
        self.log_request(request_text, trim_log_values=trim_log_values)
        response = await self.send_message(request_text, **kwargs)
        self.log_response(response, trim_log_values=trim_log_values)
        self.validate_response(response)
        response.data = parse(
            response.text, validate_against_schema=validate_against_schema
        )
        return response

    async def send_message(self, request: str, **kwargs: Any):  # type: ignore
        await self.socket.send(request)

        done = False
        while not done:
            async for message in self.socket:
                if isinstance(message, (bytes, bytearray, memoryview)):
                    continue
                json_response = json.loads(str(message))
                if 'method' in json_response and 'progress' in json_response['method']:
                    print(json_response['params']['amount'])
                else:
                    return Response(message)
