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

"""Client that support synchronous and asynchronous usage of the :class:`AsyncClient`."""

import asyncio

from threading import Thread
from .async_client import AsyncClient
from .utils import copydoc


class Client:
    """Client that support synchronous and asynchronous usage of the :class:`AsyncClient`."""

    def __init__(self, url, subprotocols=None, loop=None):
        """
        Setup the :class:`AsyncClient` for synchronous usage.

        In case the given loop is running, uses a second threaded client to achieve synchronous
        execution.

        :param str url: The address of the Rockets server.
        :param list subprotocols: The websocket protocols to use
        :param asyncio.AbstractEventLoop loop: Event loop where this client should run in
        """
        if not loop:
            loop = asyncio.get_event_loop()

        if loop.is_running():
            thread_loop = asyncio.new_event_loop()

            def _start_background_loop(loop):
                asyncio.set_event_loop(loop)
                loop.run_forever()

            self._thread = Thread(target=_start_background_loop, args=(thread_loop,))
            self._thread.daemon = True
            self._thread.start()

            self._client = AsyncClient(url, subprotocols=subprotocols, loop=thread_loop)
            self._async_client = AsyncClient(url, subprotocols=subprotocols, loop=loop)
        else:
            self._thread = None
            self._client = AsyncClient(url, subprotocols=subprotocols, loop=loop)
            self._async_client = self._client

    @copydoc(AsyncClient.url)
    def url(self):  # noqa: D102 pylint: disable=missing-docstring
        return self._client.url()

    @copydoc(AsyncClient.connected)
    def connected(self):  # noqa: D102 pylint: disable=missing-docstring
        return self._client.connected()

    @copydoc(AsyncClient.connect)
    def connect(self):  # noqa: D102 pylint: disable=missing-docstring
        self._verify_environment()
        self._call_sync(self._client.connect())

    @copydoc(AsyncClient.disconnect)
    def disconnect(self):  # noqa: D102 pylint: disable=missing-docstring
        self._verify_environment()
        self._call_sync(self._client.disconnect())

    @copydoc(AsyncClient.as_observable)
    def as_observable(self):  # noqa: D102 pylint: disable=missing-docstring
        return self._client.as_observable()

    @copydoc(AsyncClient.send)
    def send(self, message):  # noqa: D102 pylint: disable=missing-docstring
        self._verify_environment()
        self._call_sync(self._client.send(message))

    @copydoc(AsyncClient.notify)
    def notify(self, method, params=None):  # noqa: D102 pylint: disable=missing-docstring
        self._verify_environment()
        self._call_sync(self._client.notify(method, params))

    @copydoc(AsyncClient.request)
    def request(self, method, params=None, response_timeout=None):  # noqa: D102,D205 pylint: disable=C0111,W9011,W9012,W9015,W9016
        """
        :param int response_timeout: number of seconds to wait for the response
        :raises TimeoutError: if request was not answered within given response_timeout
        """
        self._verify_environment()
        return self._call_sync(self._client.request(method, params), response_timeout)

    @copydoc(AsyncClient.batch_request)
    def batch_request(self, requests, response_timeout=None):  # noqa: D102,D205 pylint: disable=C0111,W9011,W9012,W9015,W9016
        """
        :param int response_timeout: number of seconds to wait for the response
        :raises TimeoutError: if request was not answered within given response_timeout
        """
        self._verify_environment()
        return self._call_sync(self._client.batch_request(requests), response_timeout)

    @copydoc(AsyncClient.async_request)
    def async_request(self, method, params=None):  # noqa: D102 pylint: disable=missing-docstring
        return self._async_client.async_request(method, params)

    @copydoc(AsyncClient.async_batch_request)
    def async_batch_request(self, requests):  # noqa: D102 pylint: disable=missing-docstring
        return self._async_client.async_batch_request(requests)

    def _verify_environment(self):
        if not self._thread and self._client.loop().is_running():
            raise RuntimeError("Unknown working environment")

    def _call_sync(self, original_function, response_timeout=None):
        if self._thread:
            future = asyncio.run_coroutine_threadsafe(
                original_function,
                self._client.loop()
            )
            return future.result(response_timeout)
        return self._client.loop().run_until_complete(original_function)
