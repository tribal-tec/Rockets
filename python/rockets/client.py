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

"""
The Client manages a websocket connection to handle messaging with a remote Rockets instance.

It runs in a thread and provides methods to send notifications and requests in JSON-RPC format.
"""

import asyncio
import async_timeout
import itertools
import websockets

from rx import Observable, Observer
from rx.concurrency import AsyncIOScheduler
from jsonrpc.jsonrpc2 import (
    JSONRPC20Request,
    JSONRPC20BatchRequest,
    JSONRPC20Response,
    JSONRPC20BatchResponse,
)

class Client:
    """
    The Client manages a websocket connection to handle messaging with a remote Rockets instance.

    It runs in a thread and provides methods to send notifications and requests in JSON-RPC format.
    """

    def __init__(self, url):
        """
        Initialize the Client, but don't setup the websocket connection yet.

        Convert the URL to a proper format and initialize the state of the client. Does not
        establish the websocket connection yet. This will be postponed to either the first notify
        or request.

        :param str url: The address of the remote running Rockets instance.
        """
        self._url = 'ws://' + url + '/'

        self._ws = None
        self._id_generator = itertools.count(0)

        async def _connect():
            await self._setup_websocket()
        asyncio.get_event_loop().run_until_complete(_connect())

        def ws_loop(observer):
            asyncio.ensure_future(self._ws_loop(observer)) 

        self._ws_observable = Observable.create(ws_loop).publish().auto_connect()

    async def _ws_loop(self, observer):    
        try:
            async for message in self._ws:
                observer.on_next(message)
        except websockets.exceptions.ConnectionClosed as e:
            observer.on_error(e)
        observer.on_completed()

    def url(self):
        """
        Returns the address of the remote running Rockets instance.

        :return: The address of the remote running Rockets instance.
        :rtype: str
        """
        return self._url

    def connected(self):
        """Returns true if the websocket is connected to the remote Rockets instance."""
        return True if self._ws and self._ws.open else False

    def disconnect(self):
        async def _disconnect():
            await self._ws.close(reason='I hate Rockets')
        asyncio.get_event_loop().run_until_complete(_disconnect())

    def notify(self, method, params=None):
        """
        Invoke an RPC on the remote running Rockets instance without waiting for a response.

        :param str method: name of the method to invoke
        :param str params: params for the method
        """
        async def _notify(method, params):
            await self._setup_websocket()
            if params:
                notification = JSONRPC20Request(method, params, is_notification=True)
            else:
                notification = JSONRPC20Request(method, is_notification=True)
            await self._ws.send(notification.json)
        asyncio.get_event_loop().run_until_complete(_notify(method, params))

    def request(self, method, params=None, response_timeout=5):
        """
        Invoke an RPC on the remote running Rockets instance and wait for its reponse.

        :param str method: name of the method to invoke
        :param dict params: params for the method
        :param int response_timeout: number of seconds to wait for the response
        :return: result or error of RPC
        :rtype: dict
        :raises Exception: if request was not answered within given response_timeout
        """
        response = asyncio.Future()
        async def _request(method, params, response_timeout):
            await self._setup_websocket()
            with async_timeout.timeout(response_timeout):
                if params:
                    request = JSONRPC20Request(method, params, _id=next(self._id_generator))
                else:
                    request = JSONRPC20Request(method, _id=next(self._id_generator))

                scheduler = AsyncIOScheduler()
                self._ws_observable.subscribe_on(scheduler).subscribe(on_next=lambda value: response.set_result(value),
                                              on_completed=lambda: print("Done!"),
                                              on_error=lambda error: print("Error Occurred: {0}".format(error)))

                await self._ws.send(request.json)

                #return response.data.result if response.data.ok else response.data.message
                #asyncio.ensure_future(response)
        asyncio.get_event_loop().run_until_complete(_request(method, params,
                                                                    response_timeout))
        asyncio.get_event_loop().run_until_complete(response)
        import json
        response_result = JSONRPC20Response(**json.loads(response.result()))
        return response_result.result if response_result.result else response_result.error

    def batch_request(self, methods, params, response_timeout=5):
        """
        Invoke a batch RPC on the remote running Rockets instance and wait for its reponse.

        :param list methods: name of the methods to invoke
        :param list params: params for the methods
        :param int response_timeout: number of seconds to wait for the response
        :return: list of responses and/or errors of RPC
        :rtype: list
        :raises TypeError: if methods and/or params are not a list
        :raises Exception: if request was not answered within given response_timeout
        """
        if not isinstance(methods, list) and not isinstance(params, list):
            raise TypeError('Not a list of methods')

        # async def _batch_request(methods, params, response_timeout):
        #     await self._setup_websocket()
        #     with async_timeout.timeout(response_timeout):
        #         requests = list()
        #         for method, param in zip(methods, params):
        #             requests.append(Request(method, param))
        #         response = await self._ws_client.send(requests)
        #         result = list()
        #         for data in response.data:
        #             if data.ok:
        #                 result.append(data.result)
        #             else:
        #                 result.append(data.message)
        #         return result
        # return asyncio.get_event_loop().run_until_complete(_batch_request(methods, params,
        #                                                                   response_timeout))

    async def _setup_websocket(self):
        """
        Setups websocket to handle binary (image) and text (all properties) messages.

        The websocket app runs in a separate thread to unblock all notebook cells.
        """
        if self.connected():
            return

        self._ws = await websockets.connect(self._url, subprotocols=['rockets'])
