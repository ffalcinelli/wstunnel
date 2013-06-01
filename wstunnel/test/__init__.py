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
from tornado.iostream import IOStream
from tornado.tcpserver import TCPServer


class EchoHandler(object):
    """
    Echo handler. Data is echoed back to uppercase
    """

    def __init__(self, io_stream):
        self.io_stream = io_stream

        def closing_cb(data):
            pass

        def sending_cb(data):
            self.io_stream.write(data.upper())

        self.io_stream.read_until_close(closing_cb, streaming_callback=sending_cb)


class EchoServer(TCPServer):
    """
    Asynchronous TCP Server echoing data back to uppercase
    """

    def __init__(self, port, address='', family=socket.AF_UNSPEC, backlog=128, io_loop=None, ssl_options=None):
        super(EchoServer, self).__init__(io_loop, ssl_options)
        self.bind(port, address, family, backlog)

    @property
    def address_list(self):
        return [(s.getsockname()[0], s.getsockname()[1]) for s in self._sockets.values()]

    def handle_stream(self, stream, address):
        handler = EchoHandler(stream)


class EchoClient():
    """
    An asynchronous client for EchoServer
    """

    def __init__(self, address, family=socket.AF_INET, socktype=socket.SOCK_STREAM):
        self.io_stream = IOStream(socket.socket(family, socktype, 0))
        self.address = address

    def handle_close(self, data):
        pass

    def send_message(self, message, handle_response):
        def handle_connect():
            self.io_stream.read_until_close(self.handle_close, handle_response)
            self.io_stream.write(message.encode("utf-8"))

        self.io_stream.connect(self.address, handle_connect)



