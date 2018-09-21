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

"""Utils for the client"""

HTTP = 'http://'
HTTPS = 'https://'
WS = 'ws://'
WSS = 'wss://'


def set_ws_protocol(url):
    """
    Set the WebSocket protocol according to the resource url.

    :param str url: Url to be checked
    :return: Url preprend with ws for http, wss for https for ws if no protocol was found
    :rtype: str
    """
    if url.startswith(WS) or url.startswith(WSS):
        return url
    if url.startswith(HTTP):
        return url.replace(HTTP, WS, 1)
    if url.startswith(HTTPS):
        return url.replace(HTTPS, WSS, 1)
    return WS + url
