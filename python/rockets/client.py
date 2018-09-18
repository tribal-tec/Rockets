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


class Client:
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
        self._url = 'ws://' + url + '/'

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
        self._json_stream = self._ws_observable \
            .filter(lambda value: not isinstance(value, (bytes, bytearray, memoryview)))

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

    def disconnect(self):
        """Disconnect this client from the remote Rockets server."""
        async def _disconnect():
            await self._ws.close()
        self._loop.run_until_complete(_disconnect())

    def notify(self, method, params=None):
        """
        Invoke an RPC on the remote running Rockets instance without waiting for a response.

        :param str method: name of the method to invoke
        :param str params: params for the method
        """
        self._loop.run_until_complete(self._async_notify(method, params))

    def async_request(self, method, params=None, response_timeout=None):
        """
        Invoke an RPC on the remote running Rockets instance and return the RequestTask.

        :param str method: name of the method to invoke
        :param dict params: params for the method
        :param int response_timeout: number of seconds before requests gets cancelled.
        :return: RequestTask object
        :rtype: RequestTask
        """
        self._loop.set_task_factory(lambda loop, coro: RequestTask(coro=coro, loop=loop))

        task = self._async_request(method, params, response_timeout, self._loop)
        return asyncio.ensure_future(task, loop=self._loop)

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
        self._loop.run_until_complete(task)
        return task.result()

    def async_batch_request(self, methods, params, response_timeout=None):
        """
        Invoke a batch RPC on the remote running Rockets instance and return the RequestTask.

        :param list methods: name of the methods to invoke
        :param list params: params for the methods
        :param int response_timeout: number of seconds to wait for the response
        :return: RequestTask object
        :rtype: RequestTask
        :raises TypeError: if methods and/or params are not a list
        """
        if not isinstance(methods, list) and not isinstance(params, list):
            raise TypeError('Not a list of methods')

        self._loop.set_task_factory(lambda loop, coro: RequestTask(coro=coro, loop=loop))

        task = self._async_batch_request(methods, params, response_timeout, self._loop)
        return asyncio.ensure_future(task, loop=self._loop)

    def batch_request(self, methods, params, response_timeout=5):
        """
        Invoke a batch RPC on the remote running Rockets instance and wait for its reponse.

        :param list methods: name of the methods to invoke
        :param list params: params for the methods
        :param int response_timeout: number of seconds to wait for the response
        :return: list of responses and/or errors of RPC
        :rtype: list
        :raises Exception: if request was not answered within given response_timeout
        """
        task = self.async_batch_request(methods, params, response_timeout)
        self._loop.run_until_complete(task)
        return task.result()

    async def _ws_loop(self, observer):
        """Internal: The loop for feeding an rxpy observer."""
        try:
            async for message in self._ws:
                observer.on_next(message)
        except websockets.exceptions.ConnectionClosed as e:  # pragma: no cover
            observer.on_error(e)
        observer.on_completed()

    async def _async_notify(self, method, params):
        await self._connect_ws()
        if params:
            notification = JSONRPC20Request(method, params, is_notification=True)
        else:
            notification = JSONRPC20Request(method, is_notification=True)
        await self._ws.send(notification.json)

    async def _async_request(self, method, params, response_timeout, loop):
        try:
            request_id = next(self._id_generator)
            await self._connect_ws()
            with async_timeout.timeout(response_timeout):
                if params:
                    if not isinstance(params, (list, tuple, dict)):
                        params = [params]
                    request = JSONRPC20Request(method, params, _id=request_id)
                else:
                    request = JSONRPC20Request(method, _id=request_id)

                response_future = asyncio.Future(loop=loop)

                self._setup_response_filter(response_future, request_id)
                self._setup_progress_filter(response_future, request_id)

                await self._ws.send(request.json)
                await response_future
                return response_future.result()
        except asyncio.CancelledError:
            await self._async_notify('cancel', {'id': request_id})

    async def _async_batch_request(self, methods, params, response_timeout, loop):
        try:
            request_ids = list()
            await self._connect_ws()
            with async_timeout.timeout(response_timeout):
                requests = list()
                for method, param in zip(methods, params):
                    request_id = next(self._id_generator)
                    requests.append(JSONRPC20Request(method, param, _id=request_id).data)
                    request_ids.append(request_id)

                request = JSONRPC20Request.from_data(requests)

                response_future = asyncio.Future(loop=loop)

                self._setup_batch_response_filter(response_future, request_ids)

                await self._ws.send(request.json)
                await response_future
                return response_future.result()
        except asyncio.CancelledError:  # pragma: no cover
            for request_id in request_ids:
                await self._async_notify('cancel', {'id': request_id})

    def _setup_response_filter(self, response_future, request_id):
        def _response_filter(value):
            response = json.loads(value)
            return 'id' in response and response['id'] == request_id

        def _to_response(value):
            response = JSONRPC20Response(**json.loads(value))
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

        def _on_error(value):  # pragma: no cover
            if not response_future.done():
                response_future.set_exception(value)

        self._json_stream \
            .filter(_response_filter) \
            .take(1) \
            .map(_to_response) \
            .subscribe(on_next=_on_next,
                       on_completed=_on_completed,
                       on_error=_on_error)

    def _setup_batch_response_filter(self, response_future, request_ids):
        def _response_filter(value):
            responses_json = json.loads(value)
            for response in responses_json:
                if 'id' not in response or response['id'] not in request_ids:
                    return False  # pragma: no cover
            return True

        def _to_response(value):
            responses_json = json.loads(value)
            responses = [JSONRPC20Response(**i) for i in responses_json]
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
                response_future.set_exception(SOCKET_CLOSED_ERROR)  # pragma: no cover

        def _on_error(value):  # pragma: no cover
            if not response_future.done():
                response_future.set_exception(value)

        self._json_stream \
            .filter(_response_filter) \
            .take(1) \
            .map(_to_response) \
            .subscribe(on_next=_on_next,
                       on_completed=_on_completed,
                       on_error=_on_error)

    def _setup_progress_filter(self, response_future, request_id):
        task = asyncio.Task.current_task()
        if task and isinstance(task, RequestTask):
            def _progress_filter(value):
                progress = json.loads(value)
                return 'method' in progress and progress['method'] == 'progress' and \
                    'params' in progress and 'id' in progress['params'] and \
                    progress['params']['id'] == request_id

            def _to_progress(value):
                progress = JSONRPC20Request.from_json(value).params
                return RequestProgress(progress['operation'], progress['amount'])

            progress_observable = self._json_stream \
                .filter(_progress_filter) \
                .map(_to_progress) \
                .subscribe(task._call_progress_callbacks)  # pylint: disable=W0212

            def _done_callback(future):  # pylint: disable=W0613
                progress_observable.dispose()

            response_future.add_done_callback(_done_callback)

    async def _connect_ws(self):
        """Internal: Connect websocket to self._url if not connected yet."""
        if self.connected():
            return

        self._ws = await websockets.connect(self._url, subprotocols=['rockets'], loop=self._loop)
