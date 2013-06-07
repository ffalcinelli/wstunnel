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
import sys
import unittest

from tempfile import NamedTemporaryFile

from wstunnel.factory import load_filter
from wstunnel.filters import DumpFilter
from wstunnel.toolbox import address_to_tuple, tuple_to_address, hex_dump, random_free_port


__author__ = 'fabio'

DELETE_TMP = not sys.platform.startswith("win")


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

    def test_hex_dump_unicode(self):
        """
        Tests the hex dump function with unicode strings
        """
        size = 16
        data = u"Hello World"
        result = "0000  48 65 6c 6c 6f 20 57 6f  72 6c 64                   Hello.Wo rld"
        self.assertEqual(hex_dump(data, size), result)

    def test_hex_dump_binary_data(self):
        """
        Tests the hex dump function passing binary data
        """
        size = 16
        data = b"\xff\xfd\x18\xff\xfd\x1f\xff\xfd#\xff\xfd'\xff\xfd$"
        result = "0000  ff fd 18 ff fd 1f ff fd  23 ff fd 27 ff fd 24       ........ #..'..$"
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

    def test_load_filter(self):
        """
        Test loading a filter given the fully qualified class name
        """
        with NamedTemporaryFile(delete=DELETE_TMP) as dumpf:
            filter_name = "wstunnel.filters.DumpFilter"
            DumpFilter.default_conf["handlers"]["dump_file_handler"]["filename"] = dumpf.name
            f = load_filter(filter_name)
            self.assertIsInstance(f, DumpFilter)