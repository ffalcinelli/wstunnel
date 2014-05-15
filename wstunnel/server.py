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
from tornado.httpserver import HTTPServer
from tornado.iostream import IOStream
from tornado.web import Application
from tornado.websocket import WebSocketHandler
from wstunnel.filters import FilterException
from wstunnel.toolbox import random_free_port, tuple_to_address

__author__ = 'fabio'

logger = logging.getLogger(__name__)


class WebSocketProxyHandler(WebSocketHandler):
    """
    Proxy a websocket connection to a service listening on a given (host, port) pair
    """

    def initialize(self, **kwargs):
        self.remote_address = kwargs.get("address")
        self.io_stream = IOStream(socket.socket(kwargs.get("family", socket.AF_INET),
                                                kwargs.get("type", socket.SOCK_STREAM),
                                                0))
        self.filters = kwargs.get("filters", [])
        self.io_stream.set_close_callback(self.on_close)

    def open(self):
        """
        Open the connection to the service when the WebSocket connection has been established
        """
        logger.info("Forwarding connection to server %s" % tuple_to_address(self.remote_address))
        self.io_stream.connect(self.remote_address, self.on_connect)

    def on_message(self, message):
        """
        On message received from WebSocket, forward data to the service
        """
        try:
            data = None if message is None else bytes(message)
            for filtr in self.filters:
                data = filtr.ws_to_socket(data=data)
            if data:
                self.io_stream.write(data)
        except Exception as e:
            logger.exception(e)
            self.close()

    def on_close(self, *args, **kwargs):
        """
        When web socket gets closed, close the connection to the service too
        """
        logger.info("Closing connection with peer at %s" % tuple_to_address(self.remote_address))
        logger.debug("Received args %s and %s", args, kwargs)
        #if not self.io_stream._closed:
        for message in args:
            self.on_peer_message(message)
        if not self.io_stream.closed():
            self.io_stream.close()
        self.close()

    def on_connect(self):
        """
        Callback invoked on connection with mapped service
        """
        logger.info("Connection established with peer at %s" % tuple_to_address(self.remote_address))
        self.io_stream.read_until_close(self.on_close, self.on_peer_message)

    def on_peer_message(self, message):
        """
        On message received from peer service, send back to client through WebSocket
        """
        try:
            data = None if message is None else bytes(message)
            for filtr in self.filters:
                data = filtr.socket_to_ws(data=data)
            if data:
                self.write_message(data, binary=True)
        except FilterException as e:
            logger.exception(e)
            self.on_close()


class WSTunnelServer(object):
    """
    WebSocket tunnel remote endpoint.
    Handles several proxy services on different paths
    """

    def __init__(self, port=0, address='', proxies=None, io_loop=None, ssl_options=None, **kwargs):
        self.port = port
        self.address = address
        self.proxies = {}

        self.tunnel_options = {
            "io_loop": io_loop,
            "ssl_options": ssl_options
        }
        self.app_settings = kwargs

        if proxies:
            for resource, addr in proxies.items():
                self.add_proxy(resource, {"address": addr})

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value if value else random_free_port()

    def add_proxy(self, key, ws_proxy):
        logger.info("Adding {0} as proxy for {1}".format(ws_proxy, key))
        self.proxies[key] = ws_proxy

    def remove_proxy(self, key):
        logger.info("Removing proxy on {0}".format(key))
        del self.proxies[key]

    def get_proxy(self, key):
        return self.proxies.get(key)

    def install_filter(self, filtr):
        """
        Install a filter into each WebSocket proxy
        """
        for ws_proxy in self.proxies.values():
            if ws_proxy.get("filters") is not None:
                ws_proxy.get("filters").append(filtr)
            else:
                ws_proxy["filters"] = [filtr]

    def uninstall_filter(self, filtr):
        """
        Uninstall a filter from each WebSocket proxy
        """
        for ws_proxy in self.proxies.values():
            if filtr in ws_proxy.get("filters"):
                ws_proxy.get("filters").remove(filtr)

    @property
    def handlers(self):
        return [(key, WebSocketProxyHandler, ws_proxy) for key, ws_proxy in self.proxies.items()]

    def start(self, num_processes=1):
        logger.info("Starting {0} {1} processes".format(num_processes, self.__class__.__name__))
        self.app = Application(self.handlers, self.app_settings)
        self.server = HTTPServer(self.app, **self.tunnel_options)
        logger.info("Binding on port {}".format(self.port))
        self.server.bind(self.port)
        self.server.start(num_processes)

    def stop(self):
        pass
