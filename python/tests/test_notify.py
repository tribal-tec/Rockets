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

import asyncio
import websockets
from jsonrpcserver.aio import methods

from nose.tools import assert_true, assert_false, assert_equal, raises
from mock import Mock, patch
import rockets

got_ping = False
hello_param = None

@methods.add
async def ping():
    global got_ping
    got_ping = True

@methods.add
async def hello(param):
    global hello_param
    hello_param = param

async def server_handle(websocket, path):
    request = await websocket.recv()
    await methods.dispatch(request)

server_url = None
def setup():
    start_server = websockets.serve(server_handle, 'localhost')
    server = asyncio.get_event_loop().run_until_complete(start_server)
    global server_url
    server_url = 'localhost:'+str(server.sockets[0].getsockname()[1])


def test_connect():
    client = rockets.Client(server_url)
    assert_equal(client.url(), 'ws://'+server_url+ '/')
    assert_true(client.connected())


def test_no_param():
    client = rockets.Client(server_url)
    assert_false(got_ping)
    try:
        client.notify('ping')
    # Don't know why this closes the connection...
    except websockets.exceptions.ConnectionClosed:
        pass
    assert_true(got_ping)


def test_param():
    client = rockets.Client(server_url)
    try:
        client.notify('hello', 'world')
    # Don't know why this closes the connection...
    except websockets.exceptions.ConnectionClosed:
        pass
    assert_equal(hello_param, 'world')


def test_method_not_found():
    client = rockets.Client(server_url)
    try:
        client.notify('pong')
    # Don't know why this closes the connection...
    except websockets.exceptions.ConnectionClosed:
        pass


if __name__ == '__main__':
    import nose
    nose.run(defaultTest=__name__)
