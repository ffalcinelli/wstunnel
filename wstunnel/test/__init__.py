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
import os
import shutil
import socket
import sys
from time import sleep
from tornado.iostream import IOStream
from tornado.tcpserver import TCPServer
from wstunnel.filters import BaseFilter, FilterException


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

    def __init__(self, port, address='127.0.0.1', family=socket.AF_UNSPEC, backlog=128, io_loop=None, ssl_options=None):
        super(EchoServer, self).__init__(io_loop, ssl_options)
        self.bind(port, address, family, backlog)

    @property
    def address_list(self):
        return [(s.getsockname()[0], s.getsockname()[1]) for s in self._sockets.values()]

    def handle_stream(self, stream, address):
        handler = EchoHandler(stream)


class EchoClient(object):
    """
    An asynchronous client for EchoServer
    """

    def __init__(self, address, family=socket.AF_INET, socktype=socket.SOCK_STREAM):
        self.io_stream = IOStream(socket.socket(family, socktype, 0))
        self.address = address
        self.is_closed = False

    def handle_close(self, data):
        self.is_closed = True

    def send_message(self, message, handle_response):
        def handle_connect():
            self.io_stream.read_until_close(self.handle_close, handle_response)
            m = message
            if not isinstance(m, bytes):
                m = m.encode("UTF-8")
            self.io_stream.write(m)
        self.io_stream.connect(self.address, handle_connect)

        # def send_message_forever(self, message, handle_response, delay=0.5):
        #     def handle_connect():
        #         self.io_stream.read_until_close(self.handle_close, handle_response)
        #         while True:
        #             m = message
        #             if not isinstance(m, bytes):
        #                 m = m.encode("UTF-8")
        #             self.io_stream.write(m)
        #             sleep(delay)
        #     self.io_stream.connect(self.address, handle_connect)


class RaiseFromWSFilter(BaseFilter):
    """
    A fake filter raising an exception when receiving data from websocket
    """

    def ws_to_socket(self, data):
        raise FilterException(data)

    def socket_to_ws(self, data):
        return data


class RaiseToWSFilter(BaseFilter):
    """
    A fake filter raising an exception when sending data to websocket
    """

    def ws_to_socket(self, data):
        return data

    def socket_to_ws(self, data):
        raise FilterException(data)

#TODO: on windows, temporary files are not working so well...
DELETE_TMPFILE = not sys.platform.startswith("win")
fixture = os.path.join(os.path.dirname(__file__), "fixture")


def setup_logging():
    """
    Sets up the logging and PID files
    """
    log_file = os.path.join(fixture, "logs", "wstun_test_{0}.log".format(os.getpid()))
    pid_file = os.path.join(fixture, "temp", "wstun_test_{0}.pid".format(os.getpid()))

    for f in log_file, pid_file:
        if os.path.exists(f):
            os.remove(f)
    return log_file, pid_file


def clean_logging(files):
    """
    Cleans up logging and PID files
    """
    for f in files:
        if os.path.exists(f):
            os.remove(f)
    for d in map(os.path.dirname, files):
        if os.path.exists(d):
            shutil.rmtree(d)
