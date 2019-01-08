# Copyright (c) 2017-2018, EPFL/Blue Brain Project
#                          Raphael.Dumusc@epfl.ch
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

set(TEST_FILES
  http.cpp
  jsonRpc.cpp
  jsonRpcAsync.cpp
  jsonRpcCancellable.cpp
  jsonRpcClientServer.cpp
  websockets.cpp
)
if(${Libwebsockets_VERSION} VERSION_GREATER 2.0.0)
  list(APPEND TEST_FILES jsonRpcHttp.cpp)
endif()

function(add_boost_test SOURCE_FILE_NAME)
  get_filename_component(TEST_EXECUTABLE_NAME ${SOURCE_FILE_NAME} NAME_WE)
  if(TARGET ${TEST_EXECUTABLE_NAME})
    set(TEST_EXECUTABLE_NAME Rockets-${TEST_EXECUTABLE_NAME})
  endif()

  add_executable(${TEST_EXECUTABLE_NAME} ${SOURCE_FILE_NAME})
  target_compile_definitions(${TEST_EXECUTABLE_NAME} PRIVATE -DBOOST_TEST_DYN_LINK)
  target_link_libraries(${TEST_EXECUTABLE_NAME} Rockets Boost::unit_test_framework)

  add_test(NAME ${TEST_EXECUTABLE_NAME} COMMAND ${TEST_EXECUTABLE_NAME})
endfunction()

foreach(FILE ${TEST_FILES})
  add_boost_test(${FILE})
endforeach()
