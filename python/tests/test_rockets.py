#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2016-2018, Blue Brain Project
#                          Raphael Dumusc <raphael.dumusc@epfl.ch>
#                          Daniel Nachbaur <daniel.nachbaur@epfl.ch>
#                          Cyrille Favreau <cyrille.favreau@epfl.ch>
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

from nose.tools import assert_true, assert_false, assert_equal, raises
from mock import Mock, patch
import rockets

TEST_VERSION = {
    'major': 0,
    'minor': 7,
    'patch': 0,
    'revision': 12345
}


def test_notify():
    client = rockets.Client('localhost:8200')
    client.notify('foo')


if __name__ == '__main__':
    import nose
    nose.run(defaultTest=__name__)
