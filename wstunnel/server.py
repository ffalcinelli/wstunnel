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
from tornado.iostream import IOStream, StreamClosedError
from tornado.web import Application
from tornado.websocket import WebSocketHandler
from wstunnel.exception import MappedServiceNotAvailableException
from wstunnel.filters import FilterException
from wstunnel.toolbox import random_free_port

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
        self.io_stream.set_close_callback(self.handle_close)

    def open(self):
        """
        Open the connection to the service when the WebSocket connection has been established
        """
        logger.debug("WebSocket connection established")
        logger.debug("Forwarding connection to server {0}:{1}".format(*self.remote_address))
        self.io_stream.connect(self.remote_address, self.handle_connect)

    def on_message(self, message):
        """
        On message received from WebSocket, forward data to the service
        """
        try:
            if not message:
                msg = "No data received through websocket to reply to remote peer"
                logger.warn(msg)
                raise EOFError(msg)

            data = bytes(message)
            for filtr in self.filters:
                data = filtr.ws_to_socket(data=data)
            if data:
                self.io_stream.write(data)
        except Exception as e:
            logger.exception(e)
            self.close()

    def on_close(self):
        """
        When web socket gets closed, close the connection to the service too
        """
        logger.debug("Closing WebSocket")
        if not self.io_stream._closed:
            self.io_stream.close()

    def handle_connect(self):
        logger.debug("Connection established with peer at {0}:{1}".format(*self.remote_address))
        self.io_stream.read_until_close(self.handle_close, self.handle_reply)

    def handle_reply(self, message):
        """
        On message received from the service, send back to client through WebSocket
        """
        try:
            if not message:
                msg = "No data received from remote peer to reply through websocket"
                logger.warn(msg)
                raise EOFError(msg)

            data = bytes(message)
            for filtr in self.filters:
                data = filtr.socket_to_ws(data=data)
            if data:
                self.write_message(data, binary=True)
        except FilterException as e:
            logger.exception(e)
            self.close()

    def handle_close(self, data=None):
        """
        Handles the close event of the service
        """
        logger.debug("Closing connection with peer at {0}:{1}".format(*self.remote_address))
        if data:
            logger("Additional data: {}".format(data))
        self.close()

    def close(self):
        """
        Handles closing the websocket
        """
        if self.ws_connection:
            super(WebSocketProxyHandler, self).close()


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
        logger.debug("Adding {0} as proxy for {1}".format(ws_proxy, key))
        self.proxies[key] = ws_proxy

    def remove_proxy(self, key):
        logger.debug("Removing proxy on {0}".format(key))
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
