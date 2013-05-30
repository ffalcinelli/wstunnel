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
import os
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.web import Application
from tornado.websocket import WebSocketHandler
from decorators import enhance_log
from wstunnel.filters import FilterException, DumpFilter
from wstunnel.toolbox import random_free_port

__author__ = 'fabio'

logger = logging.getLogger(__name__)


class WebSocketProxyHandler(WebSocketHandler):
    """
    Proxy a websocket connection to a service listening on a given (host, port) pair
    """

    @enhance_log(logger)
    def initialize(self, **kwargs):
        self.remote_address = kwargs.get("address")
        self.io_stream = IOStream(socket.socket(kwargs.get("family", socket.AF_INET),
                                                kwargs.get("type", socket.SOCK_STREAM),
                                                0))
        self.filters = kwargs.get("filters", [])
        self.io_stream.set_close_callback(self.handle_close)

    @enhance_log(logger)
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
            data = bytes(message)
            for filtr in self.filters:
                data = filtr.ws_to_socket(data=data)
            if data:
                self.io_stream.write(data)
        except FilterException as e:
            logger.exception(e)
            self.close()

    @enhance_log(logger)
    def on_close(self):
        """
        When web socket gets closed, close the connection to the service too
        """
        logger.debug("Closing WebSocket")
        if not self.io_stream._closed:
            self.io_stream.close()

    @enhance_log(logger)
    def handle_connect(self):
        logger.debug("Connection established with peer at {0}:{1}".format(*self.remote_address))
        self.io_stream.read_until_close(self.handle_close, self.handle_reply)

    def handle_reply(self, message):
        """
        On message received from the service, send back to client through WebSocket
        """
        try:
            data = bytes(message)
            for filtr in self.filters:
                data = filtr.socket_to_ws(data=data)
            if data:
                self.write_message(data, binary=True)
        except FilterException as e:
            logger.exception(e)
            self.close()

    @enhance_log(logger)
    def handle_close(self, data=None):
        """
        Handles the close event of the service
        """
        logger.debug("Closing connection with peer at {0}:{1}".format(*self.remote_address))
        if data:
            logger("Additional data: {}".format(data))
        super(WebSocketProxyHandler, self).close()


class WSTunnelServer(object):
    """
    WebSocket tunnel remote endpoint.
    Handles several proxy services on different urls
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

    @enhance_log(logger)
    def add_proxy(self, key, ws_proxy):
        logger.debug("Adding {0} as proxy for {1}".format(ws_proxy, key))
        self.proxies[key] = ws_proxy

    @enhance_log(logger)
    def remove_proxy(self, key):
        logger.debug("Removing proxy on {1}".format(key))
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

    @enhance_log(logger)
    def start(self, num_processes=1):
        #logger.disabled = False
        logger.info("Starting {0} {1} processes".format(num_processes, self.__class__.__name__))
        self.app = Application(self.handlers, self.app_settings)
        self.server = HTTPServer(self.app, **self.tunnel_options)
        logger.info("Binding on port {}".format(self.port))
        self.server.bind(self.port)
        self.server.start(num_processes)

    def stop(self):
        pass


if __name__ == "__main__":
    cert_dir = os.path.join(os.path.dirname(__file__), "fixture")
    srv_tun = WSTunnelServer(9000,
                             proxies={"/test_svil": ("10.6.72.227", 23),
                                      "/test_home": ("192.168.1.2", 13131)})
    # ssl_options={
    # "certfile": os.path.join(cert_dir, "localhost.pem"),
    # "keyfile":  os.path.join(cert_dir, "localhost.key"),
    # }

    srv_tun.install_filter(DumpFilter(handler={"filename": "/tmp/srv_log"}))
    srv_tun.start()
    IOLoop.instance().start()