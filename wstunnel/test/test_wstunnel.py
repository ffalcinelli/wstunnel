# -*- coding: utf-8 -*-
# Copyright (C) 2013  Fabio Falcinelli
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import socket
from tempfile import NamedTemporaryFile
import os
from tornado.testing import AsyncTestCase, LogTrapTestCase
from wstunnel.filters import DumpFilter, FilterException
from wstunnel.test import EchoServer, EchoClient, RaiseFromWSFilter, RaiseToWSFilter, setup_logging, clean_logging, \
    fixture, DELETE_TMPFILE
from wstunnel.client import WSTunnelClient, WebSocketProxy
from wstunnel.server import WSTunnelServer
from wstunnel.toolbox import hex_dump, random_free_port


__author__ = 'fabio'
ASYNC_TIMEOUT = 2


class WSEndpointsTestCase(AsyncTestCase, LogTrapTestCase):
    """
    TestCase for endpoints behaviour on various conditions
    """

    def setUp(self):
        super(WSEndpointsTestCase, self).setUp()
        self.log_file, self.pid_file = setup_logging()

    def no_response(self, response):
        self.stop()
        self.fail("Connection should be dropped without a response if an error happens")


    def test_no_ws_endpoint(self):
        """
        Tests the client tunnel endpoint behaviour when there's no server counterpart
        """
        clt_tun = WSTunnelClient(family=socket.AF_INET)
        clt_tun.add_proxy("test", WebSocketProxy(port=0, ws_url="ws://localhost:{0}/test".format(random_free_port())))
        clt_tun.start()
        message = "Hello World!"
        client = EchoClient(clt_tun.address_list[0])
        client.send_message(message, self.no_response)
        #self.wait(timeout=ASYNC_TIMEOUT)
        with self.assertRaises(Exception):
            try:
                self.wait(timeout=ASYNC_TIMEOUT)
            except Exception as e:
                self.assertEqual(str(e),
                                 "The server endpoint is not available, caused by HTTPError('HTTP 599: [Errno 61] Connection refused',))")
                raise e

    def test_no_server_service(self):
        """
        Tests the server tunnel endpoint behaviour when there's no service to connect
        """
        srv_tun = WSTunnelServer(0, proxies={"/test": ("127.0.0.1", random_free_port())})
        srv_tun.start()
        clt_tun = WSTunnelClient()
        clt_tun.add_proxy("test", WebSocketProxy(port=0,
                                                 ws_url="ws://localhost:{0}/test".format(srv_tun.port)))

        clt_tun.start()

        message = "Hello World!"
        client = EchoClient(clt_tun.address_list[0])
        client.send_message(message, self.no_response)
        with self.assertRaises(Exception):
            try:
                self.wait(timeout=ASYNC_TIMEOUT)
            except Exception as e:
                #print(e)
                #self.assertEqual(str(e),)
                raise e

    def test_no_client_ws_options(self):
        """
        Tests the client tunnel endpoint behaviour when there's no server counterpart
        """
        clt_tun = WSTunnelClient(family=socket.AF_INET)
        clt_tun.add_proxy("test", WebSocketProxy(port=0, ws_url="ws://localhost:{0}/test".format(random_free_port())))
        clt_tun.start()
        self.assertEqual(clt_tun.ws_options, {})

    def tearDown(self):
        super(WSEndpointsTestCase, self).tearDown()
        clean_logging([self.log_file, self.pid_file])


class WSTunnelTestCase(AsyncTestCase, LogTrapTestCase):
    """
    Tunneling thorugh WebSocket tests
    """

    def setUp(self):
        super(WSTunnelTestCase, self).setUp()
        self.log_file, self.pid_file = setup_logging()
        self.srv = EchoServer(port=0,
                              address="127.0.0.1")
        self.srv.start(1)
        self.srv_tun = WSTunnelServer(port=0,
                                      address=self.srv.address_list[0][0],
                                      proxies={"/test": self.srv.address_list[0]})
        self.srv_tun.start()
        self.clt_tun = WSTunnelClient(proxies={0: "ws://localhost:{0}/test".format(self.srv_tun.port)},
                                      address=self.srv_tun.address,
                                      family=socket.AF_INET,
                                      ws_options={"validate_cert": False})
        self.clt_tun.start()

        self.message = "Hello World!".encode("utf-8")
        self.client = EchoClient(self.clt_tun.address_list[0])

    def tearDown(self):

        for srv in self.srv, self.srv_tun, self.clt_tun:
            srv.stop()

        super(WSTunnelTestCase, self).tearDown()
        clean_logging([self.log_file, self.pid_file])

    def on_response_received(self, response):
        """
        Callback invoked when response is received
        """
        self.assertEqual(self.message.upper(), response)
        self.stop()

    def on_response_resend(self, response):
        """
        Callback invoked when response is received. It resends the message, so that there will be an infinite loop.
        """
        self.assertEqual(self.message.upper(), response)
        self.client.write(self.message)

    def test_request_response(self):
        """
        Test a simple request/response chat through the websocket tunnel
        """
        self.client.send_message(self.message, self.on_response_received)
        self.wait(timeout=ASYNC_TIMEOUT)

    def test_request_response_binary(self):
        """
        Test a simple request/response chat through the websocket tunnel. Message contains
        non utf-8 characters
        """
        self.message = bytes(b"\xff\xfd\x18\xff\xfd\x1f\xff\xfd#\xff\xfd'\xff\xfd$")
        self.client.send_message(self.message, self.on_response_received)
        self.wait(timeout=ASYNC_TIMEOUT)

    def test_client_dump_filter(self):
        """
        Test the installing of a dump filter into client endpoint
        """
        setup_logging()
        with NamedTemporaryFile(delete=DELETE_TMPFILE) as logf:
            client_filter = DumpFilter(handler={"filename": logf.name})
            self.clt_tun.install_filter(client_filter)

            self.client.send_message(self.message, self.on_response_received)
            self.wait(timeout=ASYNC_TIMEOUT)

            content = logf.read()
            for line in hex_dump(self.message).splitlines():
                self.assertIn(line, content.decode("utf-8"))

            self.clt_tun.uninstall_filter(client_filter)

    def test_server_dump_filter(self):
        """
        Test the installing of a dump filter into server endpoint
        """
        with NamedTemporaryFile(delete=DELETE_TMPFILE) as logf:
            server_filter = DumpFilter(handler={"filename": logf.name})
            self.srv_tun.install_filter(server_filter)

            self.client.send_message(self.message, self.on_response_received)
            self.wait(timeout=ASYNC_TIMEOUT)

            content = logf.read()
            for line in hex_dump(self.message).splitlines():
                self.assertIn(line, content.decode("utf-8"))

            self.srv_tun.uninstall_filter(server_filter)

    def test_raise_filter_exception_from_ws(self):
        """
        Tests the behaviour when a filter raises exception reading from websocket
        """
        server_filter = RaiseFromWSFilter()
        self.srv_tun.install_filter(server_filter)

        self.client.send_message(self.message, self.on_response_received)
        #TODO: this generically catch assertion errors... We should get the inner FilterException in some way
        self.assertRaises(AssertionError, self.wait, timeout=1)

    def test_raise_filter_exception_to_ws(self):
        """
        Tests the behaviour when a filter raises exception writing to websocket
        """
        server_filter = RaiseToWSFilter()
        self.srv_tun.install_filter(server_filter)

        self.client.send_message(self.message, self.on_response_received)
        #TODO: this generically catch assertion errors... We should get the inner FilterException in some way
        self.assertRaises(AssertionError, self.wait, timeout=1)

    def test_add_get_remove_client_proxy(self):
        """
        Tests adding/remove/get operations on client proxies
        """
        ws_proxy = WebSocketProxy(port=0, ws_url="ws://localhost:9000/test_add_remove")
        self.assertFalse(ws_proxy.serving)
        self.clt_tun.add_proxy("test_add_remove", ws_proxy)
        self.assertEqual(ws_proxy, self.clt_tun.get_proxy("test_add_remove"))
        self.assertTrue(ws_proxy.serving)
        self.clt_tun.remove_proxy("test_add_remove")
        self.assertFalse(ws_proxy.serving)

    def test_add_get_remove_server_proxy(self):
        """
        Tests adding/remove/get operations on server proxies
        """
        ws_proxies = {"/test": ("127.0.0.1", random_free_port())}
        for key, address in ws_proxies.items():
            self.srv_tun.add_proxy(key, address)
            self.assertEqual(address, self.srv_tun.get_proxy(key))
            self.assertEqual(1, len(self.srv_tun.proxies))
            self.srv_tun.remove_proxy(key)
            self.assertEqual(0, len(self.srv_tun.proxies))

    def test_server_peer_connection_drop_issue_6(self):
        """
        Tests dropping peer connection server side. This test addresses issue #6
        """

        def on_close(*args):
            raise Exception("CLOSED")

        self.client.handle_close = on_close
        self.client.send_message(self.message, handle_response=self.on_response_resend)
        self.srv.stop()
        try:
            self.wait(timeout=ASYNC_TIMEOUT)
        except Exception as e:
            self.assertEqual("CLOSED", str(e))

    def test_server_tunnel_connection_drop(self):
        """
        Tests dropping connection server side by shutting down the WebSocket tunnel server
        """
        def on_close(*args):
            raise Exception("CLOSED")

        self.client.handle_close = on_close
        self.client.send_message(self.message, handle_response=self.on_response_resend)
        self.srv_tun.stop()
        try:
            self.wait(timeout=ASYNC_TIMEOUT)
        except Exception as e:
            # Possibile cases (timing matters here):
            # 1. Connection is lost when the client already sent next message --> CLOSED since the
            # endpoint notified the client just in time.
            # 2. Connection is lost when the client did not send the next message --> ASYNC_TIMEOUT since no endpoint
            # responding
            self.assertTrue(str(e).lower() in ("closed", "async operation timed out after %d seconds" % ASYNC_TIMEOUT))


class WSTunnelSSLTestCase(WSTunnelTestCase):
    """
    Tests for SSL WebSocket tunnel
    """

    def setUp(self):
        super(WSTunnelSSLTestCase, self).setUp()
        self.log_file, self.pid_file = setup_logging()
        self.srv = EchoServer(port=0, address="127.0.0.1")
        self.srv.start()
        self.srv_tun = WSTunnelServer(port=0,
                                      address=self.srv.address_list[0][0],
                                      proxies={"/test": self.srv.address_list[0]},
                                      ssl_options={
                                          "certfile": os.path.join(fixture, "localhost.pem"),
                                          "keyfile": os.path.join(fixture, "localhost.key"),
                                      })
        self.srv_tun.start()
        self.clt_tun = WSTunnelClient(proxies={0: "wss://localhost:{0}/test".format(self.srv_tun.port)},
                                      address=self.srv_tun.address,
                                      family=socket.AF_INET,
                                      ws_options={"validate_cert": False})
        self.clt_tun.start()

        self.message = "Hello World!".encode("utf-8")
        self.client = EchoClient(self.clt_tun.address_list[0])
