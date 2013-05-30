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
import string
from binascii import hexlify

import os

__author__ = 'fabio'

PORT_RANGE = (1025, 65535)


def address_to_tuple(addr):
    """
    Convert an host:port string into (host, port) tuple.
    """
    addr = str(addr)
    address, port = None, None
    if ":" in addr:
        address, port = addr.split(":")[0], int(addr.split(":")[1])
    elif addr.isdigit():
        port = int(addr)
    else:
        address = addr
    return address, port


def tuple_to_address(addr):
    """
    Convert an (host, port) tuple into a host:port string.
    If one of the member is missing, the other is returned.
    """
    host, port = addr
    if host and port:
        return "{}:{}".format(*addr)
    elif host and not port:
        return host
    elif port and not host:
        return port
    else:
        return None


def hex_dump(buff, size=16):
    """
    Dump the buffer in wireshark style
    """
    out = []
    if buff:
        char_conv = lambda x: c if c in string.printable[:-6] else '.'
        for i in range(0, len(buff), size):
            hexed, plain = zip(*[(hexlify(c), char_conv(c)) for c in buff[i:i + size]])
            hexed = "{:04x}  {}  {}".format(i,
                                            " ".join(hexed[:size / 2]),
                                            " ".join(hexed[size / 2:size]))
            plain = "{} {}".format("".join(plain[:size / 2]),
                                   "".join(plain[size / 2:size]))
            out.append("{0}   {1:>{2}}".format(hexed,
                                               plain,
                                               55 - (len(hexed) - len(plain))))
    return "\n".join(out)


def random_free_port(family=socket.AF_INET, type=socket.SOCK_STREAM, port_range=PORT_RANGE):
    """
    Pick a free port in the given range
    """
    s = socket.socket(family, type)
    try:
        for p in range(*port_range):
            if s.connect_ex(('127.0.0.1' if family == socket.AF_INET else '::1', p)) != 0:
                return p
        else:
            raise Exception("No free ports in range {0}".format(port_range))
    finally:
        s.close()


def get_config(appname="wstunneld", filename="wstunneld.conf"):
    """
    Search for a configuration file in current, user home or /etc (not suitable for windows...) folders
    """
    path_list = [os.getcwd(),
                 os.path.join(os.path.expanduser("~"), "." + appname),
                 os.path.join("/etc", appname)]

    for conf_dir in path_list:
        if conf_dir:
            conf_file = os.path.join(conf_dir, filename)
            if os.path.exists(conf_file):
                return conf_file
    return None