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
import itertools
import json

import async_timeout
import websockets
from jsonrpc.jsonrpc2 import (JSONRPC20Request, JSONRPC20Response)
from rx import Observable

from .request_error import SOCKET_CLOSED_ERROR, RequestError
from .request_progress import RequestProgress
from .request_task import RequestTask
from .utils import set_ws_protocol


class AsyncClient:
    """
    The Client manages a websocket connection to handle messaging with a remote Rockets instance.

    It runs in a thread and provides methods to send notifications and requests in JSON-RPC format.
    """

    def __init__(self, url, loop=None):
        """
        Initialize the Client, but don't setup the websocket connection yet.

        Convert the URL to a proper format and initialize the state of the client. Does not
        establish the websocket connection yet. This will be postponed to either the first notify
        or request.

        :param str url: The address of the remote running Rockets instance.
        :param asyncio.AbstractEventLoop loop: Event loop where this client should run in
        """
        self._url = set_ws_protocol(url)

        self._ws = None
        self._id_generator = itertools.count(0)

        self._loop = loop
        if not self._loop:
            self._loop = asyncio.get_event_loop()

        def ws_loop(observer):
            """Internal: synchronous wrapper for async _ws_loop"""
            asyncio.ensure_future(self._ws_loop(observer), loop=self._loop)

        # pylint: disable=E1101
        self._ws_observable = Observable.create(ws_loop).publish().auto_connect()
        # pylint: enable=E1101

        def _json_filter(value):
            try:
                json.loads(value)
                return True
            except ValueError:  # pragma: no cover
                return False

        self._json_stream = self._ws_observable \
            .filter(lambda value: not isinstance(value, (bytes, bytearray, memoryview))) \
            .filter(_json_filter) \
            .map(json.loads)

    def url(self):
        """
        Returns the address of the remote running Rockets instance.

        :return: The address of the remote running Rockets instance.
        :rtype: str
        """
        return self._url

    def connected(self):
        """
        Returns the connection state of this client.

        :return: true if the websocket is connected to the remote Rockets instance.
        :rtype: bool
        """
        return True if self._ws and self._ws.open else False

    def as_observable(self):
        """
        Returns the websocket stream as an rx observable to subscribe to it.

        :return: the websocket observable
        :rtype: rx.Observable
        """
        return self._ws_observable

    def loop(self):
        """
        Returns the event loop for this client.

        :return: event loop
        :rtype: asyncio.AbstractEventLoop
        """
        return self._loop

    async def connect(self):
        """Connect this client to the remote Rockets server"""
        if self.connected():
            return

        self._ws = await websockets.connect(self._url, subprotocols=['rockets'], loop=self._loop)

    async def disconnect(self):
        """Disconnect this client from the remote Rockets server."""
        if not self.connected():
            return

        await self._ws.close()

    async def send(self, message):
        """
        Send any message to the connected remote Rockets server.

        :param str message: The message to send
        """
        await self.connect()
        await self._ws.send(message)

    async def notify(self, method, params):
        """
        Invoke an RPC on the remote running Rockets instance without waiting for a response.

        :param str method: name of the method to invoke
        :param str params: params for the method
        """
        await self.connect()
        if params:
            notification = JSONRPC20Request(method, params, is_notification=True)
        else:
            notification = JSONRPC20Request(method, is_notification=True)
        await self._ws.send(notification.json)

    async def request(self, method, params, response_timeout):
        """
        Invoke an RPC on the remote running Rockets instance.

        :param str method: name of the method to invoke
        :param dict params: params for the method
        :param int response_timeout: number of seconds before requests gets cancelled.
        :return: future object
        :rtype: future
        """
        try:
            request_id = next(self._id_generator)
            await self.connect()
            with async_timeout.timeout(response_timeout):
                if params:
                    if not isinstance(params, (list, tuple, dict)):
                        params = [params]
                    request = JSONRPC20Request(method, params, _id=request_id)
                else:
                    request = JSONRPC20Request(method, _id=request_id)

                response_future = asyncio.Future(loop=self._loop)

                self._setup_response_filter(response_future, request_id)
                self._setup_progress_filter(response_future, request_id)

                await self._ws.send(request.json)
                await response_future
                return response_future.result()
        except asyncio.CancelledError:
            await self.notify('cancel', {'id': request_id})

    async def batch_request(self, methods, params, response_timeout):
        """
        Invoke a batch RPC on the remote running Rockets instance.

        :param list methods: name of the methods to invoke
        :param list params: params for the methods
        :param int response_timeout: number of seconds to wait for the response
        :return: future object
        :rtype: future
        :raises TypeError: if methods and/or params are not a list
        """
        if not isinstance(methods, list) and not isinstance(params, list):
            raise TypeError('Not a list of methods')

        if not methods:
            raise ValueError("Empty batch request not allowed")
        try:
            request_ids = list()
            await self.connect()
            with async_timeout.timeout(response_timeout):
                requests = list()
                for method, param in zip(methods, params):
                    request_id = next(self._id_generator)
                    requests.append(JSONRPC20Request(method, param, _id=request_id).data)
                    request_ids.append(request_id)

                request = JSONRPC20Request.from_data(requests)

                response_future = asyncio.Future(loop=self._loop)

                self._setup_batch_response_filter(response_future, request_ids)

                await self._ws.send(request.json)
                await response_future
                return response_future.result()
        except asyncio.CancelledError:
            for request_id in request_ids:
                await self.notify('cancel', {'id': request_id})

    def start_request(self, method, params=None, response_timeout=None):
        """
        Invoke an RPC on the remote running Rockets instance and return the RequestTask.

        :param str method: name of the method to invoke
        :param dict params: params for the method
        :param int response_timeout: number of seconds before requests gets cancelled.
        :return: RequestTask object
        :rtype: RequestTask
        """
        self._loop.set_task_factory(lambda loop, coro: RequestTask(coro=coro, loop=loop))

        task = self.request(method, params, response_timeout)
        return asyncio.ensure_future(task, loop=self._loop)

    def start_batch_request(self, methods, params, response_timeout=None):
        """
        Invoke a batch RPC on the remote running Rockets instance and return the RequestTask.

        :param list methods: name of the methods to invoke
        :param list params: params for the methods
        :param int response_timeout: number of seconds to wait for the response
        :return: RequestTask object
        :rtype: RequestTask
        """
        self._loop.set_task_factory(lambda loop, coro: RequestTask(coro=coro, loop=loop))

        task = self.batch_request(methods, params, response_timeout)
        return asyncio.ensure_future(task, loop=self._loop)

    async def _ws_loop(self, observer):
        """Internal: The loop for feeding an rxpy observer."""
        async for message in self._ws:
            observer.on_next(message)
        observer.on_completed()

    def _setup_response_filter(self, response_future, request_id):
        def _response_filter(value):
            return 'id' in value and value['id'] == request_id

        def _to_response(value):
            response = JSONRPC20Response(**value)
            if response.result:
                return response.result
            return response.error

        def _on_next(value):
            if not response_future.done():
                if isinstance(value, dict) and 'code' in value:
                    response_future.set_exception(RequestError(value['code'], value['message']))
                else:
                    response_future.set_result(value)

        def _on_completed():
            if not response_future.done():
                response_future.set_exception(SOCKET_CLOSED_ERROR)

        self._json_stream \
            .filter(_response_filter) \
            .take(1) \
            .map(_to_response) \
            .subscribe(on_next=_on_next,
                       on_completed=_on_completed)

    def _setup_batch_response_filter(self, response_future, request_ids):
        def _response_filter(value):
            for response in value:
                if 'id' not in response or response['id'] not in request_ids:
                    return False  # pragma: no cover
            return True

        def _to_response(value):
            responses = [JSONRPC20Response(**i) for i in value]
            result = list()
            for response in responses:
                if response.result:
                    result.append(response.result)
                else:
                    result.append(response.error)
            return result

        def _on_next(value):
            if not response_future.done():
                response_future.set_result(value)

        def _on_completed():
            if not response_future.done():
                response_future.set_exception(SOCKET_CLOSED_ERROR)

        self._json_stream \
            .filter(_response_filter) \
            .take(1) \
            .map(_to_response) \
            .subscribe(on_next=_on_next,
                       on_completed=_on_completed)

    def _setup_progress_filter(self, response_future, request_id):
        task = asyncio.Task.current_task()
        if task and isinstance(task, RequestTask):
            def _progress_filter(value):
                return 'method' in value and value['method'] == 'progress' and \
                    'params' in value and 'id' in value['params'] and \
                    value['params']['id'] == request_id

            def _to_progress(value):
                progress = JSONRPC20Request.from_data(value).params
                return RequestProgress(progress['operation'], progress['amount'])

            progress_observable = self._json_stream \
                .filter(_progress_filter) \
                .map(_to_progress) \
                .subscribe(task._call_progress_callbacks)  # pylint: disable=W0212

            def _done_callback(future):  # pylint: disable=W0613
                progress_observable.dispose()

            response_future.add_done_callback(_done_callback)
