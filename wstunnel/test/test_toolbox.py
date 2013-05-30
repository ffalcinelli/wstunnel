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
import unittest
from toolbox import address_to_tuple, tuple_to_address, hex_dump, random_free_port

__author__ = 'fabio'


class ToolBoxTestCase(unittest.TestCase):
    def test_address_to_tuple(self):
        """
        Tests the address to tuple conversions
        """
        addr = "127.0.0.1:443"
        t = address_to_tuple(addr)
        self.assertEqual(t, ("127.0.0.1", 443))
        self.assertEqual(addr, tuple_to_address(t))

    def test_address_to_tuple_missing_port(self):
        """
        Tests the address to tuple conversions when port is missing
        """
        addr = "127.0.0.1"
        t = address_to_tuple(addr)
        self.assertEqual(t, ("127.0.0.1", None))
        self.assertEqual(addr, tuple_to_address(t))

    def test_address_to_tuple_missing_host(self):
        """
        Tests the address to tuple conversions when host is missing
        """
        addr = 443
        t = address_to_tuple(addr)
        self.assertEqual(t, (None, 443))
        self.assertEqual(addr, tuple_to_address(t))

    def test_hex_dump(self):
        """
        Tests the hex dump function
        """
        size = 16
        data = "Hello World"
        result = "0000  48 65 6c 6c 6f 20 57 6f  72 6c 64                   Hello.Wo rld"
        self.assertEqual(hex_dump(data, size), result)

    def _test_random_free_port(self, address, family, type):
        port = random_free_port(family=family, type=type)
        sock = socket.socket(family=family, type=type)
        self.assertRaises(socket.error, sock.connect, (address, port))

    def test_random_free_port_ipv4(self):
        """
        Tests getting a random free port on ipv4 interface
        """
        self._test_random_free_port("127.0.0.1", socket.AF_INET, socket.SOCK_STREAM)

    def test_random_free_port_ipv6(self):
        """
        Tests getting a random free port on ipv6 interface
        """
        self._test_random_free_port("::1", socket.AF_INET6, socket.SOCK_STREAM)
