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

from threading import Thread
from .async_client import AsyncClient
from .request_task import RequestTask


class Client:
    """
    The Client manages a websocket connection to handle messaging with a remote Rockets instance.

    It runs in a thread and provides methods to send notifications and requests in JSON-RPC format.
    """

    def __init__(self, url, loop=None):
        """
        Bla

        :param str url: The address of the remote running Rockets instance.
        :param asyncio.AbstractEventLoop loop: Event loop where this client should run in
        """
        if not loop:
            loop = asyncio.get_event_loop()

        if loop.is_running():
            loop = asyncio.new_event_loop()

            def _start_background_loop(loop):
                asyncio.set_event_loop(loop)
                loop.run_forever()

            self._thread = Thread(target=_start_background_loop, args=(loop,))
            self._thread.daemon = True
            self._thread.start()
        else:
            self._thread = None

        self._async_client = AsyncClient(url, loop)

    def url(self):
        """
        Returns the address of the remote running Rockets instance.

        :return: The address of the remote running Rockets instance.
        :rtype: str
        """
        return self._async_client.url()

    def connected(self):
        """
        Returns the connection state of this client.

        :return: true if the websocket is connected to the remote Rockets instance.
        :rtype: bool
        """
        return self._async_client.connected()

    def connect(self):
        """Connect this client to the remote Rockets server"""
        self._verify_environment()
        self._call_sync(self._async_client.connect())

    def disconnect(self):
        """Disconnect this client from the remote Rockets server."""
        self._verify_environment()
        self._call_sync(self._async_client.disconnect())

    def notify(self, method, params=None):
        """
        Invoke an RPC on the remote running Rockets instance without waiting for a response.

        :param str method: name of the method to invoke
        :param str params: params for the method
        """
        self._verify_environment()
        self._call_sync(self._async_client.notify(method, params))

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
        self._verify_environment()
        return self._call_sync(self._async_client.request(method, params, response_timeout))

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
        self._verify_environment()
        return self._call_sync(self._async_client.batch_request(methods, params, response_timeout))

    def start_request(self, method, params=None, response_timeout=None):
        """
        Invoke an RPC on the remote running Rockets instance and return the RequestTask.

        :param str method: name of the method to invoke
        :param dict params: params for the method
        :param int response_timeout: number of seconds before requests gets cancelled.
        :return: RequestTask object
        :rtype: RequestTask
        """
        # if self._thread:
        #     #self._async_client.loop().set_task_factory(lambda loop, coro: RequestTask(coro=coro, loop=loop))
        #     #task = self._async_client.loop().call_soon_threadsafe(self._async_client.request, method, params, response_timeout)
        #     #return task
        #     #return self._async_client.loop().call_soon_threadsafe(self._async_client.start_request, method, params, response_timeout)
        #     self._async_client.loop().set_task_factory(lambda loop, coro: RequestTask(coro=coro, loop=loop))
        #     #future = asyncio.run_coroutine_threadsafe(
        #     #    self._async_client.request(method, params, response_timeout),
        #     #    self._async_client.loop()
        #     #)
        #     #return asyncio.ensure_future(future)

        #     def target(loop, timeout=None):
                 future = asyncio.run_coroutine_threadsafe(self._async_client.request(method, params, response_timeout), self._async_client.loop())
        #         return future.result()

        #     return asyncio.get_event_loop().run_in_executor(None, target, asyncio.get_event_loop())

        task = self._async_client.start_request(method, params, response_timeout)
        if self._thread:
            new_code = False
            if new_code:
                async def dummy():
                    pass
                asyncio.run_coroutine_threadsafe(dummy(), self._async_client.loop()).result()
                return task

            asyncio.get_event_loop().set_task_factory(lambda loop, coro: RequestTask(coro=coro, loop=loop))

            async def coro():
                try:
                    #from threading import Event
                    #evt = Event()
                    #print("HERE!!!")
                    #await asyncio.sleep(1)
                    print("HERE!!!")
                    fut = asyncio.get_event_loop().create_future()
                    def _on_done(the_task):
                        print("DONE!!!")
                        #evt.set()
                        fut.set_result(the_task.result())
                    task.add_done_callback(_on_done)
                    #evt.wait()

                    await fut
                    return fut.result()
                except asyncio.CancelledError:
                    task.cancel()

            wrapper_task = asyncio.get_event_loop().create_task(coro())
            asyncio.ensure_future(wrapper_task, loop=asyncio.get_event_loop())
            return wrapper_task
        return task


    def start_batch_request(self, methods, params, response_timeout=None):
        """
        Invoke a batch RPC on the remote running Rockets instance and return the RequestTask.

        :param list methods: name of the methods to invoke
        :param list params: params for the methods
        :param int response_timeout: number of seconds to wait for the response
        :return: RequestTask object
        :rtype: RequestTask
        """
        task = self._async_client.start_batch_request(methods, params, response_timeout)
        if self._thread:
            async def dummy():
                pass
            asyncio.run_coroutine_threadsafe(dummy(), self._async_client.loop()).result()
        return task

    def _verify_environment(self):
        if not self._thread and self._async_client.loop().is_running():
            raise RuntimeError("Unknown working environment")

    def _call_sync(self, original_function):
        if self._thread:
            future = asyncio.run_coroutine_threadsafe(
                original_function,
                self._async_client.loop()
            )
            return future.result()
        return self._async_client.loop().run_until_complete(original_function)
