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
from jsonrpcserver.response import RequestResponse
import json

from nose.tools import assert_true, assert_equal, raises
import rockets


@methods.add
async def ping():
    return 'pong'

@methods.add
async def double(value):
    return value*2

async def server_handle(websocket, path):
    request = await websocket.recv()

    json_request = json.loads(request)
    if isinstance(json_request, list) and any(i['method'] == 'test_cancel' for i in json_request):
        cancel_request = await websocket.recv()
        print("GOT CANCEL", cancel_request)
        response = RequestResponse(json_request['id'], 'CANCELLED')
    else:
        response = await methods.dispatch(request)
    if not response.is_notification:
        await websocket.send(str(response))

server_url = None
def setup():
    start_server = websockets.serve(server_handle, 'localhost')
    server = asyncio.get_event_loop().run_until_complete(start_server)
    global server_url
    server_url = 'localhost:'+str(server.sockets[0].getsockname()[1])


def test_batch():
    client = rockets.Client(server_url)
    assert_equal(client.batch_request(['double', 'double'], [[2], [4]]), [4, 8])


@raises(TypeError)
def test_invalid_args():
    client = rockets.Client(server_url)
    client.batch_request('foo', 'bar')


def test_method_not_found():
    client = rockets.Client(server_url)
    assert_equal(client.batch_request(['foo'], [['bar']]),
                 [{'code': -32601, 'message': 'Method not found'}])


@raises(rockets.request_error.RequestError)
def test_error_on_connection_lost():
    client = rockets.Client(server_url)
    # do one request, which finishes the server, so the second request will throw an error
    assert_equal(client.request('ping'), 'pong')
    assert_equal(client.batch_request(['double', 'double'], [[2], [4]]), [4, 8])


def test_cancel():
    client = rockets.Client(server_url)
    request_task = client.async_batch_request(['test_cancel', 'test_cancel'], [[],[]])

    def _on_done(value):
        assert_equal(value.result(), None)
        asyncio.get_event_loop().stop()

    async def _do_cancel():
        asyncio.sleep(10)
        request_task.cancel()

    request_task.add_done_callback(_on_done)

    asyncio.ensure_future(request_task)
    asyncio.ensure_future(_do_cancel())

    asyncio.get_event_loop().run_forever()

    assert_true(request_task.done())


if __name__ == '__main__':
    import nose
    nose.run(defaultTest=__name__)
