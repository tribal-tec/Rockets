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
import json
import websockets

from rx import Observable
from jsonrpc.jsonrpc2 import (
    JSONRPC20Request,
    JSONRPC20BatchRequest,
    JSONRPC20Response,
    JSONRPC20BatchResponse,
)

from .request_error import RequestError, SOCKET_CLOSED_ERROR
from .request_task import RequestTask


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
            await self._connect_ws()
        asyncio.get_event_loop().run_until_complete(_connect())

        def ws_loop(observer):
            asyncio.ensure_future(self._ws_loop(observer)) 

        self._ws_observable = Observable.create(ws_loop).publish().auto_connect()
        self._json_observable = self._ws_observable \
            .filter(lambda value: not isinstance(value, (bytes, bytearray, memoryview)))

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
            await self._connect_ws()
            if params:
                notification = JSONRPC20Request(method, params, is_notification=True)
            else:
                notification = JSONRPC20Request(method, is_notification=True)
            await self._ws.send(notification.json)
        asyncio.get_event_loop().run_until_complete(_notify(method, params))

    async def _async_request(self, method, params, response_timeout):
        await self._connect_ws()
        with async_timeout.timeout(response_timeout):
            request_id = next(self._id_generator)
            if params:
                if not isinstance(params, (list, tuple, dict)):
                    params = [params]
                request = JSONRPC20Request(method, params, _id=request_id)
            else:
                request = JSONRPC20Request(method, _id=request_id)

            def _to_response(value):
                response = JSONRPC20Response(**json.loads(value))
                if response.result:
                    return response.result
                raise RequestError(response.error['code'], response.error['message'])

            response_future = asyncio.Future()

            def _on_completed():
                if not response_future.done():
                    response_future.set_exception(SOCKET_CLOSED_ERROR)

            def _response_filter(value):                    
                response = json.loads(value)
                return 'id' in response and response['id'] == request_id

            self._json_observable \
                .filter(_response_filter) \
                .take(1) \
                .map(_to_response) \
                .subscribe(on_next=response_future.set_result,
                           on_completed=_on_completed,
                           on_error=response_future.set_exception)

            def _progress_filter(value):
                progress = json.loads(value)
                return 'method' in progress and progress['method'] == 'progress' and \
                    'params' in progress and 'id' in progress['params'] and \
                    progress['params']['id'] == request_id

            def _to_progress(value):
                progress = JSONRPC20Request.from_json(value)
                return (progress.params['operation'], progress.params['amount'])

            task = asyncio.Task.current_task()
            if task:
                progress_observable = self._json_observable \
                    .filter(_progress_filter) \
                    .map(_to_progress) \
                    .subscribe(task._call_progress_callbacks)

                def _done_callback(future):
                    progress_observable.dispose()                

                response_future.add_done_callback(_done_callback)

            await self._ws.send(request.json)
            await response_future
            return response_future.result()

    def async_request(self, method, params, response_timeout):
        loop = asyncio.get_event_loop()
        task_factory = lambda loop, coro: RequestTask(coro, loop=loop)
        loop.set_task_factory(task_factory)

        return asyncio.ensure_future(self._async_request(method, params, response_timeout))

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

        task = self.async_request(method, params, response_timeout)
        asyncio.get_event_loop().run_until_complete(task)        
        return task.result()

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
        #     await self._connect_ws()
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

    async def _connect_ws(self):
        """
        Connect websocket to _url if not connected yet/
        """
        if self.connected():
            return

        self._ws = await websockets.connect(self._url, subprotocols=['rockets'])
