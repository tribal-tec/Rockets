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

from threading import Thread
from nose.tools import assert_true, assert_false, assert_equal
import rockets


async def server_handle(websocket, path):
    print("AAA")
    bla = await websocket.recv()
    print("AAA",bla)

server_url = None
def setup():
    # server_loop = asyncio.new_event_loop()

    # def _start_background_loop(loop):
    #     asyncio.set_event_loop(loop)
    #     loop.run_forever()

    # server_thread = Thread(target=_start_background_loop, args=(server_loop,))
    # server_thread.start()

    start_server = websockets.serve(server_handle, 'localhost')
    #server = asyncio.ensure_future(start_server, loop=server_loop)
    #future = asyncio.run_coroutine_threadsafe(start_server, server_loop)
    #server = future.result()
    server = asyncio.get_event_loop().run_until_complete(start_server)
    global server_url
    server_url = 'localhost:'+str(server.sockets[0].getsockname()[1])


def test_run_in_loop():
    async def runner():
        #client = rockets.Client('ws://'+server_url)
        client = rockets.Client('ws://localhost:8200')
        #assert_equal(client.url(), 'ws://'+server_url)
        assert_false(client.connected())
        client.notify('hello')
    asyncio.get_event_loop().run_until_complete(runner())


if __name__ == '__main__':
    #import nose
    #nose.run(defaultTest=__name__)
    setup()
    test_run_in_loop()
