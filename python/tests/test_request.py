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
from jsonrpcserver.response import NotificationResponse

from nose.tools import assert_true, assert_false, assert_equal, raises
from mock import Mock, patch
import rockets

@methods.add
async def ping():
    return 'pong'

@methods.add
async def double(value):
    return value*2

async def server_handle(websocket, path):
    request = await websocket.recv()
    response = await methods.dispatch(request)
    if not response.is_notification:
        await websocket.send(str(response))

server_url = None
def setup():
    start_server = websockets.serve(server_handle, 'localhost')
    server = asyncio.get_event_loop().run_until_complete(start_server)
    global server_url
    server_url = 'localhost:'+str(server.sockets[0].getsockname()[1])


def test_no_param():
    client = rockets.Client(server_url)
    assert_equal(client.request('ping'), 'pong')


def test_param():
    client = rockets.Client(server_url)
    assert_equal(client.request('double', [2]), 4)


def test_param_as_not_a_list():
    client = rockets.Client(server_url)
    assert_equal(client.request('double', 2), 4)


def test_method_not_found():
    client = rockets.Client(server_url)
    try:
        client.request('foo')
    except rockets.RequestError as e:
        assert_equal(e.code, -32601)
        assert_equal(e.message, 'Method not found')
        

if __name__ == '__main__':
    import nose
    nose.run(defaultTest=__name__)
