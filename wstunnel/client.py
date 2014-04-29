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
from tornado import httpclient
from tornado.ioloop import IOLoop

from tornado.tcpserver import TCPServer
from tornado.websocket import WebSocketClientConnection
from wstunnel.filters import FilterException

__author__ = "fabio"
logger = logging.getLogger(__name__)


def websocket_connect(url, io_loop=None, callback=None, connect_timeout=None, **kwargs):
    """Client-side websocket support.

    Takes a url and returns a Future whose result is a
    `WebSocketClientConnection`.
    """
    options = httpclient.HTTPRequest._DEFAULTS.copy()
    options.update(kwargs)

    if io_loop is None:
        io_loop = IOLoop.current()
    request = httpclient.HTTPRequest(url, connect_timeout=connect_timeout)
    request = httpclient._RequestProxy(
        request, options)
    conn = WebSocketClientConnection(io_loop, request)
    if callback is not None:
        io_loop.add_future(conn.connect_future, callback)
    return conn.connect_future


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
        self.ws_options = kwargs.get("ws_options", {})
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
        ws = WebSocketProxyConnection(self.ws_url, stream, address, filters=self.filters, ws_options=self.ws_options)
        logger.debug("Connecting to WebSocket endpoint at {}".format(self.ws_url))
        ws.connect()

    def start(self, num_processes=1):
        super(WebSocketProxy, self).start(num_processes)
        self.serving = True

    def stop(self):
        super(WebSocketProxy, self).stop()
        self.serving = False


class WebSocketProxyConnection(object):
    """
    Handles the client connection and works as a proxy over a websocket connection
    """

    def __init__(self, url, io_stream, address, ws_options=None, **kwargs):
        self.url = url
        self.io_loop = kwargs.get("io_loop")
        self.connect_timeout = kwargs.get("connect_timeout", None)
        self.keep_alive = kwargs.get("keep_alive", None)
        self.ws_options = ws_options
        self.io_stream, self.address = io_stream, address
        self.filters = kwargs.get("filters", [])
        self.io_stream.set_close_callback(self.handle_close)
        self.ws_conn = None

    def connect(self):
        websocket_connect(self.url,
                          self.io_loop,
                          callback=self.opened,
                          connect_timeout=self.connect_timeout,
                          **self.ws_options)


    def opened(self, ws_conn):
        """
        When the websocket connection is handshaked, start reading for data over the client socket
        connection
        """
        logger.debug("Connection with websocket established")
        self.ws_conn = ws_conn.result()
        self.ws_conn.on_message = self.handle_receive
        self.io_stream.read_until_close(self.handle_close, streaming_callback=self.handle_forward)

    def handle_receive(self, message):
        """
        On a message received from websocket, send back to client
        """
        try:
            data = bytes(message)
            for filtr in self.filters:
                data = filtr.ws_to_socket(data=data)
            if data:
                self.io_stream.write(data)
        except FilterException as e:
            logger.exception(e)
            #TODO: define better codes
            self.close(code=2022, reason=e)

    def close(self, code, reason=None):
        """
        When WebSocket gets closed, close the client socket too
        """
        logger.debug("Connection with websocket has been closed: reason {1} [{0}]".format(code, reason))
        if not self.io_stream.closed():
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
                self.ws_conn.write_message(data, binary=True)
        except FilterException as e:
            logger.exception(e)
            #TODO: define better codes
            self.close(code=2021, reason=e)

    def handle_close(self):
        """
        Handles the close event from the client socket
        """
        logger.debug("Closing connection with client at {0}:{1}".format(*self.address))
        self.close(code=2020, reason="Client disconnected")


class WSTunnelClient(object):
    """
    Manages redirects from local ports to remote websocket servers
    """

    def __init__(self, proxies=None, address='', family=socket.AF_UNSPEC, io_loop=None, ssl_options=None,
                 ws_options=None, **kwargs):

        self.stream_options = {
            "address": address,
            "family": family,
            "io_loop": io_loop,
            "ssl_options": ssl_options,
        }
        self.ws_options = ws_options or {}
        self.proxies = {}
        self.serving = False
        self._num_proc = 1
        if proxies:
            for port, ws_url in proxies.items():
                self.add_proxy(port, WebSocketProxy(port=port, ws_url=ws_url, ws_options=self.ws_options,
                                                    **self.stream_options))

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
