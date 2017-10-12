/*********************************************************************/
/* Copyright (c) 2017, EPFL/Blue Brain Project                       */
/*                     Raphael Dumusc <raphael.dumusc@epfl.ch>       */
/* All rights reserved.                                              */
/*                                                                   */
/* Redistribution and use in source and binary forms, with or        */
/* without modification, are permitted provided that the following   */
/* conditions are met:                                               */
/*                                                                   */
/*   1. Redistributions of source code must retain the above         */
/*      copyright notice, this list of conditions and the following  */
/*      disclaimer.                                                  */
/*                                                                   */
/*   2. Redistributions in binary form must reproduce the above      */
/*      copyright notice, this list of conditions and the following  */
/*      disclaimer in the documentation and/or other materials       */
/*      provided with the distribution.                              */
/*                                                                   */
/*    THIS  SOFTWARE IS PROVIDED  BY THE  UNIVERSITY OF  TEXAS AT    */
/*    AUSTIN  ``AS IS''  AND ANY  EXPRESS OR  IMPLIED WARRANTIES,    */
/*    INCLUDING, BUT  NOT LIMITED  TO, THE IMPLIED  WARRANTIES OF    */
/*    MERCHANTABILITY  AND FITNESS FOR  A PARTICULAR  PURPOSE ARE    */
/*    DISCLAIMED.  IN  NO EVENT SHALL THE UNIVERSITY  OF TEXAS AT    */
/*    AUSTIN OR CONTRIBUTORS BE  LIABLE FOR ANY DIRECT, INDIRECT,    */
/*    INCIDENTAL,  SPECIAL, EXEMPLARY,  OR  CONSEQUENTIAL DAMAGES    */
/*    (INCLUDING, BUT  NOT LIMITED TO,  PROCUREMENT OF SUBSTITUTE    */
/*    GOODS  OR  SERVICES; LOSS  OF  USE,  DATA,  OR PROFITS;  OR    */
/*    BUSINESS INTERRUPTION) HOWEVER CAUSED  AND ON ANY THEORY OF    */
/*    LIABILITY, WHETHER  IN CONTRACT, STRICT  LIABILITY, OR TORT    */
/*    (INCLUDING NEGLIGENCE OR OTHERWISE)  ARISING IN ANY WAY OUT    */
/*    OF  THE  USE OF  THIS  SOFTWARE,  EVEN  IF ADVISED  OF  THE    */
/*    POSSIBILITY OF SUCH DAMAGE.                                    */
/*                                                                   */
/* The views and conclusions contained in the software and           */
/* documentation are those of the authors and should not be          */
/* interpreted as representing official policies, either expressed   */
/* or implied, of Ecole polytechnique federale de Lausanne.          */
/*********************************************************************/

#define BOOST_TEST_MODULE rockets_jsonrpc_client_server

#include <boost/test/unit_test.hpp>

#include "rockets/jsonrpc/client.h"
#include "rockets/jsonrpc/server.h"
#include "rockets/ws/client.h"
#include "rockets/server.h"
#include "rockets/json.hpp"

using namespace rockets;

namespace
{
const std::string simpleMessage(R"({
    "value": true
})");
}

struct MockNetworkCommunicator
{
    void handleText(ws::MessageCallback callback)
    {
        handleMessage = callback;
    }

    void handleText(ws::MessageCallbackAsync callback)
    {
        handleMessageAsync = callback;
    }

    void sendText(std::string message)
    {
        if (blockRecursion)
            return;
        blockRecursion = true;

        // Handle return message from Receiver without infinite loop.
        // The ws::MessageHandler normally does this in the rockets::Server.
        auto ret = sendToRemoteEndpoint(message);
        if (!ret.empty())
            handleMessage(std::move(ret));

        blockRecursion = false;
    }

    void broadcastText(const std::string& message)
    {
        sendToRemoteEndpoint(message);
    }

    void connectWith(MockNetworkCommunicator& other)
    {
        sendToRemoteEndpoint = other.handleMessage;
        other.sendToRemoteEndpoint = handleMessage;
    }

    ws::MessageCallback handleMessage;
    ws::MessageCallbackAsync handleMessageAsync;
    ws::MessageCallback sendToRemoteEndpoint;
    bool blockRecursion = false;
};

BOOST_AUTO_TEST_CASE(client_constructor)
{
    ws::Client wsClient;
    jsonrpc::Client<ws::Client> client{wsClient};
}

BOOST_AUTO_TEST_CASE(server_constructor)
{
    Server wsServer;
    jsonrpc::Server<Server> server{wsServer};
}

struct Fixture
{
    MockNetworkCommunicator serverCommunicator;
    MockNetworkCommunicator clientCommunicator;
    jsonrpc::Server<MockNetworkCommunicator> server{serverCommunicator};
    jsonrpc::Client<MockNetworkCommunicator> client{clientCommunicator};
    Fixture()
    {
        serverCommunicator.connectWith(clientCommunicator);
    }
};

BOOST_FIXTURE_TEST_CASE(client_notification_received_by_server, Fixture)
{
    bool received = false;
    server.connect("test", [&](const std::string& request) {
        received = (request == simpleMessage);
    });
    client.emit("test", simpleMessage);
    BOOST_CHECK(received);
}

BOOST_FIXTURE_TEST_CASE(client_request_answered_by_server, Fixture)
{
    bool receivedRequest = false;
    bool receivedReply = false;
    std::string receivedValue;
    server.bind("test", [&](const std::string& request) {
        receivedRequest = (request == simpleMessage);
        return jsonrpc::Response{"42"};
    });
    client.request("test", simpleMessage, [&](jsonrpc::Response response) {
        receivedReply = !response.error;
        receivedValue = response.result;
    });
    BOOST_CHECK(receivedRequest);
    BOOST_CHECK(receivedReply);
    BOOST_CHECK_EQUAL(receivedValue, "\"42\"");
}

BOOST_FIXTURE_TEST_CASE(server_notification_received_by_client, Fixture)
{
    bool received = false;
    client.connect("test", [&](const std::string& request) {
        received = (request == simpleMessage);
    });
    server.emit("test", simpleMessage);
    BOOST_CHECK(received);
}
