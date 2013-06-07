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
import logging
import socket
import ssl

from tornado import escape, iostream
from tornado.tcpserver import TCPServer
from ws4py.client import WebSocketBaseClient
from ws4py.exc import HandshakeError
from wstunnel.filters import FilterException

#The urlparse module is renamed to urllib.parse in Python 3.
try:
    from urlparse import urljoin, urlparse
except ImportError:
    from urllib.parse import urljoin, urlparse

__author__ = "fabio"

logger = logging.getLogger(__name__)


#TODO: remove this class when the send issue will be fixed
class TornadoWebSocketClient(WebSocketBaseClient):
    def __init__(self, url, protocols=None, extensions=None, io_loop=None):

        WebSocketBaseClient.__init__(self, url, protocols, extensions)
        if self.scheme == "wss":
            self.sock = ssl.wrap_socket(self.sock, do_handshake_on_connect=False)
            self.io = iostream.SSLIOStream(self.sock, io_loop)
            assert self.sock is self.io.socket
        else:
            self.io = iostream.IOStream(self.sock, io_loop)
        self.io_loop = io_loop

    def connect(self):
        """
        Connects the websocket and initiate the upgrade handshake.
        """
        self.io.set_close_callback(self.__connection_refused)
        self.io.connect((self.host, int(self.port)), self.__send_handshake)

    def __connection_refused(self, *args, **kwargs):
        self.server_terminated = True
        self.closed(1005, 'Connection refused')

    def __send_handshake(self):
        self.io.set_close_callback(self.__connection_closed)
        self.io.write(escape.utf8(self.handshake_request),
                      self.__handshake_sent)

    def __connection_closed(self, *args, **kwargs):
        self.server_terminated = True
        self.closed(1006, 'Connection closed during handshake')

    def __handshake_sent(self):
        self.io.read_until(b"\r\n\r\n", self.__handshake_completed)

    def __handshake_completed(self, data):
        self.io.set_close_callback(None)
        try:
            response_line, _, headers = data.partition(b'\r\n')
            self.process_response_line(response_line)
            protocols, extensions = self.process_handshake_header(headers)
        except HandshakeError:
            self.close_connection()
            raise

        self.opened()
        self.io.set_close_callback(self.__stream_closed)
        self.io.read_bytes(self.reading_buffer_size, self.__fetch_more)

    def send(self, payload, binary=False):
        self.sock = self.io.socket
        return super(TornadoWebSocketClient, self).send(payload, binary)

    def __fetch_more(self, bytes):
        try:
            should_continue = self.process(bytes)
        except:
            should_continue = False

        if should_continue:
            self.io.read_bytes(self.reading_buffer_size, self.__fetch_more)
        else:
            self.__gracefully_terminate()

    def __gracefully_terminate(self):
        self.client_terminated = self.server_terminated = True

        try:
            if not self.stream.closing:
                self.closed(1006)
        finally:
            self.close_connection()

    def __stream_closed(self, *args, **kwargs):
        self.io.set_close_callback(None)
        code = 1006
        reason = None
        if self.stream.closing:
            code, reason = self.stream.closing.code, self.stream.closing.reason
        self.closed(code, reason)

    def close_connection(self):
        """
        Close the underlying connection
        """
        self.io.close()


class WebSocketProxy(TCPServer):
    """
    Listen on a port and delegate the accepted connection to a WebSocketLocalProxyHandler
    """

    def __init__(self, port, ws_url, **kwargs):
        super(WebSocketProxy, self).__init__(kwargs.get("io_loop"),
                                             kwargs.get("ssl_options"))
        self.bind(port,
                  kwargs.get("address", ''),
                  kwargs.get("family", socket.AF_INET),
                  kwargs.get("backlog", 128))

        self.ws_url = ws_url
        self.filters = kwargs.get("filters", [])
        self.serving = False

    @property
    def address_list(self):
        return [(s.getsockname()[0], s.getsockname()[1]) for s in self._sockets.values()]

    def handle_stream(self, stream, address):
        """
        Handle a new client connection with a proxy over websocket
        """
        logger.info("Got connection from {0}:{1}".format(*address))
        ws = WebSocketProxyConnection(self.ws_url, stream, address, filters=self.filters)
        logger.debug("Connecting to WebSocket endpoint at {}".format(self.ws_url))
        ws.connect()

    def start(self, num_processes=1):
        super(WebSocketProxy, self).start(num_processes)
        self.serving = True

    def stop(self):
        super(WebSocketProxy, self).stop()
        self.serving = False


class WebSocketProxyConnection(TornadoWebSocketClient):
    """
    Handles the client connection and works as a proxy over a websocket connection
    """

    def __init__(self, url, io_stream, address, **kwargs):
        super(WebSocketProxyConnection, self).__init__(url,
                                                       kwargs.get("protocols"),
                                                       kwargs.get("extensions"),
                                                       kwargs.get("io_loop"))
        self.io_stream, self.address = io_stream, address
        self.filters = kwargs.get("filters", [])
        self.io_stream.set_close_callback(self.handle_close)

    def opened(self):
        """
        When the websocket connection is handshaked, start reading for data over the client socket
        connection
        """
        logger.debug("Connection with websocket established")
        self.io_stream.read_until_close(self.handle_close, streaming_callback=self.handle_forward)

    def received_message(self, message):
        """
        On a message received from websocket, send back to client
        """
        try:
            data = bytes(message.data)
            for filtr in self.filters:
                data = filtr.ws_to_socket(data=data)
            if data:
                self.io_stream.write(data)
        except FilterException as e:
            logger.exception(e)
            #TODO: define better codes
            self.close(code=2022, reason=e)

    def closed(self, code, reason=None):
        """
        When WebSocket gets closed, close the client socket too
        """
        logger.debug("Connection with websocket has been closed: reason {1} [{0}]".format(code, reason))
        self.io_stream.close()

    def handle_forward(self, data):
        """
        On data received from client, forward through WebSocket
        """
        try:
            data = bytes(data)
            for filtr in self.filters:
                data = filtr.socket_to_ws(data=data)
            if data:
                self.send(data, binary=True)
        except FilterException as e:
            logger.exception(e)
            #TODO: define better codes
            self.close(code=2021, reason=e)

    def handle_close(self, data=None):
        """
        Handles the close event from the client socket
        """
        logger.debug("Closing connection with client at {0}:{1}".format(*self.address))
        if data:
            logger.debug("Additional data: {}".format(data))
        if not self.terminated:
            self.terminate()


class WSTunnelClient(object):
    """
    Manages redirects from local ports to remote websocket servers
    """

    def __init__(self, proxies=None, address='', family=socket.AF_UNSPEC, io_loop=None, ssl_options=None, **kwargs):

        self.ws_options = {
            "address": address,
            "family": family,
            "io_loop": io_loop,
            "ssl_options": ssl_options,
        }
        self.proxies = {}
        self.serving = False
        self._num_proc = 1
        if proxies:
            for port, ws_url in proxies.items():
                self.add_proxy(port, WebSocketProxy(port=port, ws_url=ws_url, **self.ws_options))

    def add_proxy(self, key, ws_proxy):
        """
        Adds a proxy to the list.
        If the tunnel is serving connection, the proxy it gets started.
        """
        logger.debug("Adding {0} as proxy for {1}".format(ws_proxy, key))
        self.proxies[key] = ws_proxy
        if self.serving:
            ws_proxy.start(self._num_proc)

    def remove_proxy(self, key):
        """
        Removes a proxy from the list.
        If the tunnel is serving connection, the proxy it gets stopped.
        """
        logger.debug("Removing proxy on {0}".format(key))
        ws_proxy = self.proxies.get(key)
        if ws_proxy:
            if self.serving:
                ws_proxy.stop()
            del self.proxies[key]

    def get_proxy(self, key):
        """
        Return the proxy associated to the given name.
        """
        return self.proxies.get(key)

    @property
    def address_list(self):
        """
        Returns the address (<host>, <port> tuple) list of all the addresses used
        """
        l = []
        for service in self.proxies.values():
            l.extend(service.address_list)
        return l

    def install_filter(self, filtr):
        """
        Install the given filter to all the current mapped services
        """
        for ws_proxy in self.proxies.values():
            ws_proxy.filters.append(filtr)

    def uninstall_filter(self, filtr):
        """
        Uninstall the given filter from all the current mapped services
        """
        for ws_proxy in self.proxies.values():
            ws_proxy.filters.remove(filtr)

    def start(self, num_processes=1):
        """
        Start the client tunnel service by starting each configured proxy
        """
        logger.info("Starting {0} {1} processes".format(num_processes, self.__class__.__name__))
        self._num_processes = num_processes
        for key, ws_proxy in self.proxies.items():
            logger.debug("Starting proxy on {}".format(key))
            ws_proxy.start(num_processes)
            self.serving = True

    def stop(self):
        """
        Stop the client tunnel service by stopping each configured proxy
        """
        logger.info("Stopping {}".format(self.__class__.__name__))
        for key, ws_proxy in self.proxies.items():
            logger.debug("Stopping proxy on {}".format(key))
            ws_proxy.stop()
        self.serving = False
