/* Copyright (c) 2017, EPFL/Blue Brain Project
 *                     Raphael.Dumusc@epfl.ch
 *
 * This file is part of Rockets <https://github.com/BlueBrain/Rockets>
 *
 * This library is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License version 3.0 as published
 * by the Free Software Foundation.
 *
 * This library is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
 * details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

#include "utils.h"

#include <lws_config.h>

// for NI_MAXHOST
#ifdef _WIN32
#include <Ws2tcpip.h>
#else
#include <netdb.h>
#include <unistd.h>
// For getIP
#include <arpa/inet.h>
#include <ifaddrs.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#endif

namespace rockets
{
Uri parse(std::string uri)
{
    auto in = const_cast<char*>(uri.c_str()); // uri is modified by parsing
    const char* protocol = nullptr;
    const char* address = nullptr;
    int port = 0;
    const char* path = nullptr;
    if (lws_parse_uri(in, &protocol, &address, &port, &path))
        throw std::invalid_argument("invalid uri");
    if (port < 0 || port > UINT16_MAX)
        throw std::invalid_argument("uri has invalid port range");
    return {protocol, address, (uint16_t)port, std::string("/").append(path)};
}

lws_protocols make_protocol(const char* name, lws_callback_function* callback,
                            void* user)
{
    // clang-format off
    return lws_protocols{ name, callback, 0, 0, 0, user
        #if LWS_LIBRARY_VERSION_NUMBER >= 2003000
                , 0
        #endif
    };
    // clang-format on
}

lws_protocols null_protocol()
{
    return make_protocol(nullptr, nullptr, nullptr);
}

std::string getIP(const std::string& iface)
{
#ifdef _WIN32
    return std::string();
#else
    struct ifaddrs *ifaddr, *ifa;
    int s = 0;
    char host[NI_MAXHOST] = {'\0'};

    if (getifaddrs(&ifaddr) == -1)
        return std::string();

    for (ifa = ifaddr; ifa != NULL; ifa = ifa->ifa_next)
    {
        if (ifa->ifa_addr == NULL)
            continue;

        s = getnameinfo(ifa->ifa_addr, sizeof(struct sockaddr_in), host,
                        NI_MAXHOST, NULL, 0, NI_NUMERICHOST);

        if ((strcmp(ifa->ifa_name, iface.c_str()) == 0) &&
            (ifa->ifa_addr->sa_family == AF_INET))
        {
            if (s != 0)
                return std::string();
        }
    }
    freeifaddrs(ifaddr);
    return host;
#endif
}

std::string getHostname()
{
    char host[NI_MAXHOST + 1] = {0};
    gethostname(host, NI_MAXHOST);
    host[NI_MAXHOST] = '\0';
    return host;
}
}
