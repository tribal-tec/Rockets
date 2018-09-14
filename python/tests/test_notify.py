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

from jsonrpcserver.exceptions import InvalidParams

got_ping = asyncio.Future()
hello_param = asyncio.Future()

@methods.add
async def ping():
    global got_ping
    got_ping.set_result(True)

@methods.add
async def hello(name):
    global hello_param
    hello_param.set_result(name)

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
    assert_false(client.connected())


def test_reconnect():
    client = rockets.Client(server_url)
    client.notify('something_to_connect')
    assert_true(client.connected())
    client.disconnect()
    assert_false(client.connected())
    client.notify('something_to_reconnect')
    assert_true(client.connected())


def test_no_param():
    client = rockets.Client(server_url)
    client.notify('ping')
    asyncio.ensure_future(got_ping)
    assert_true(got_ping)


def test_param():
    client = rockets.Client(server_url)
    client.notify('hello', {'name':'world'})
    asyncio.get_event_loop().run_until_complete(hello_param)
    assert_equal(hello_param.result(), 'world')


def test_method_not_found():
    client = rockets.Client(server_url)
    client.notify('pong')

if __name__ == '__main__':
    import nose
    nose.run(defaultTest=__name__)
