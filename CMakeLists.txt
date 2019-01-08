# Copyright (c) 2017-2019, EPFL/Blue Brain Project
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

cmake_minimum_required(VERSION 3.5 FATAL_ERROR)
project(Rockets VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Boost QUIET COMPONENTS unit_test_framework)
find_package(OpenSSL QUIET REQUIRED) # libwebsockets depends on that
find_package(Libwebsockets QUIET)
if(NOT Libwebsockets_FOUND) # Ubuntu package only has libwebsockets.pc
  find_package(PkgConfig QUIET REQUIRED)
  pkg_check_modules(Libwebsockets libwebsockets QUIET REQUIRED)
endif()
find_package(Threads QUIET REQUIRED)

# build a proper libwebsockets target
if(Libwebsockets_VERSION AND NOT TARGET libwebsockets)
  add_library(libwebsockets INTERFACE IMPORTED)
  if(APPLE) # add homebrew include dir
    list(APPEND _libwebsockets_include_dirs /usr/local/include)
  endif()
  list(APPEND _libwebsockets_include_dirs ${OPENSSL_INCLUDE_DIR})
  set_target_properties(libwebsockets PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${_libwebsockets_include_dirs}"
    INTERFACE_LINK_LIBRARIES websockets
  )
endif()

add_subdirectory(rockets)

option(ROCKETS_BUILD_APPLICATIONS "Build example applications" ON)
if(ROCKETS_BUILD_APPLICATIONS)
  add_subdirectory(apps)
endif()

if(TARGET Boost::unit_test_framework)
  include(CTest)
  enable_testing()
  add_subdirectory(tests)
endif()

#set(CPACK_PACKAGE_DESCRIPTION_FILE "${PROJECT_SOURCE_DIR}/README.md")
#set(ROCKETS_PACKAGE_DEB_DEPENDS libwebsockets-dev)
#include(CommonCPack)

#set(COMMON_PROJECT_DOMAIN ch.epfl.bluebrain)
#set(DOXYGEN_MAINPAGE_MD README.md)
#set(DOXYGEN_EXTRA_INPUT ${PROJECT_SOURCE_DIR}/README.md)
#include(DoxygenRule)
