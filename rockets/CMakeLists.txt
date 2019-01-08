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

set(ROCKETS_PUBLIC_HEADERS
  include/rockets/helpers.h
  include/rockets/server.h
  include/rockets/socketBasedInterface.h
  include/rockets/socketListener.h
  include/rockets/types.h
  include/rockets/http/client.h
  include/rockets/http/filter.h
  include/rockets/http/helpers.h
  include/rockets/http/request.h
  include/rockets/http/response.h
  include/rockets/http/types.h
  include/rockets/jsonrpc/asyncReceiver.h
  include/rockets/jsonrpc/cancellableReceiver.h
  include/rockets/jsonrpc/client.h
  include/rockets/jsonrpc/clientRequest.h
  include/rockets/jsonrpc/errorCodes.h
  include/rockets/jsonrpc/helpers.h
  include/rockets/jsonrpc/http.h
  include/rockets/jsonrpc/notifier.h
  include/rockets/jsonrpc/receiver.h
  include/rockets/jsonrpc/requester.h
  include/rockets/jsonrpc/response.h
  include/rockets/jsonrpc/responseError.h
  include/rockets/jsonrpc/server.h
  include/rockets/jsonrpc/types.h
  include/rockets/qt/readWriteSocketNotifier.h
  include/rockets/qt/socketProcessor.h
  include/rockets/ws/client.h
  include/rockets/ws/types.h
)
set(ROCKETS_HEADERS
  src/clientContext.h
  src/debug.h
  src/json.hpp
  src/pollDescriptors.h
  src/proxyConnectionError.h
  src/serverContext.h
  src/serviceThreadPool.h
  src/unavailablePortError.h
  src/utils.h
  src/wrappers.h
  src/http/channel.h
  src/http/connection.h
  src/http/connectionHandler.h
  src/http/cors.h
  src/http/registry.h
  src/http/requestHandler.h
  src/http/utils.h
  src/jsonrpc/asyncReceiverImpl.h
  src/jsonrpc/cancellableReceiverImpl.h
  src/jsonrpc/receiverImpl.h
  src/jsonrpc/requestProcessor.h
  src/jsonrpc/utils.h
  src/ws/channel.h
  src/ws/connection.h
  src/ws/messageHandler.h
)
set(ROCKETS_SOURCES
  src/log.cpp
  src/clientContext.cpp
  src/pollDescriptors.cpp
  src/serverContext.cpp
  src/server.cpp
  src/serviceThreadPool.cpp
  src/utils.cpp
  src/http/channel.cpp
  src/http/connection.cpp
  src/http/client.cpp
  src/http/connectionHandler.cpp
  src/http/registry.cpp
  src/http/requestHandler.cpp
  src/http/utils.cpp
  src/jsonrpc/asyncReceiver.cpp
  src/jsonrpc/cancellableReceiver.cpp
  src/jsonrpc/clientRequest.cpp
  src/jsonrpc/helpers.cpp
  src/jsonrpc/http.cpp
  src/jsonrpc/notifier.cpp
  src/jsonrpc/receiver.cpp
  src/jsonrpc/requester.cpp
  src/jsonrpc/requestProcessor.cpp
  src/ws/channel.cpp
  src/ws/connection.cpp
  src/ws/client.cpp
  src/ws/messageHandler.cpp
)

set(_all_files ${ROCKETS_PUBLIC_HEADERS} ${ROCKETS_HEADERS} ${ROCKETS_SOURCES})

add_library(Rockets SHARED ${_all_files})

include(GenerateExportHeader)
generate_export_header(Rockets EXPORT_MACRO_NAME ROCKETS_API
                               EXPORT_FILE_NAME api.h
)

target_include_directories(Rockets
    PUBLIC
        $<INSTALL_INTERFACE:include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include/rockets>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include/rockets/http>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include/rockets/jsonrpc>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include/rockets/ws>
        $<BUILD_INTERFACE:${PROJECT_BINARY_DIR}>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# without linking client code with pthread, std::promise::set_value() dies with
# std::system_error what():  Unknown error -1
# https://stackoverflow.com/questions/43928715
target_link_libraries(Rockets PUBLIC Threads::Threads PRIVATE libwebsockets)

if(COVERAGE)
  target_compile_options(Rockets PRIVATE --coverage)
  target_link_libraries(Rockets PRIVATE --coverage)
endif()

include(GNUInstallDirs)

include(CMakePackageConfigHelpers)

write_basic_package_version_file(
  ${PROJECT_BINARY_DIR}/RocketsConfigVersion.cmake
  VERSION ${PROJECT_VERSION}
  COMPATIBILITY AnyNewerVersion
)

configure_package_config_file(${PROJECT_SOURCE_DIR}/CMake/RocketsConfig.cmake
  ${PROJECT_BINARY_DIR}/RocketsConfig.cmake
  INSTALL_DESTINATION ${CMAKE_INSTALL_DATADIR}/Rockets/CMake
)

install(TARGETS Rockets
  EXPORT rockets-targets
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(FILES ${PROJECT_BINARY_DIR}/rockets/api.h
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/rockets
)
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/include
  DESTINATION .
)
install(FILES
  ${PROJECT_BINARY_DIR}/RocketsConfig.cmake
  ${PROJECT_BINARY_DIR}/RocketsConfigVersion.cmake
  DESTINATION ${CMAKE_INSTALL_DATADIR}/Rockets/CMake
)
install(EXPORT rockets-targets
  FILE RocketsTargets.cmake
  DESTINATION ${CMAKE_INSTALL_DATADIR}/Rockets/CMake
)

export(EXPORT rockets-targets
  FILE ${PROJECT_BINARY_DIR}/RocketsTargets.cmake
)
