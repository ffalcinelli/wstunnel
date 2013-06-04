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
import os
from binascii import hexlify
import sys

__author__ = 'fabio'

PY2 = sys.version_info[0] == 2
if not PY2:
    unichr = chr


def printable(x):
    if isinstance(x, bytes):
        return x if x in string.printable[:-6].encode("utf-8") else b'.'
    elif isinstance(x, int):
        return printable(unichr(x))
    else:
        return x if x in string.printable[:-6] else u'.'

hex_value = lambda x: hex(x if isinstance(x, int) else ord(x))[2:]


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
    half = int(size / 2)
    if buff:
        for i in range(0, len(buff), size):
            hexed, plain = zip(*[(hex_value(c), printable(c)) for c in buff[i:i + size]])
            hexed = "{:04x}  {}  {}".format(i,
                                            " ".join(hexed[:half]),
                                            " ".join(hexed[half:size]))
            plain = "{} {}".format("".join(plain[: half]),
                                   "".join(plain[half:size]))
            out.append("{0}   {1:>{2}}".format(hexed,
                                               plain,
                                               55 - (len(hexed) - len(plain))))
    return "\n".join(out)


def random_free_port(family=socket.AF_INET, type=socket.SOCK_STREAM):
    """
    Pick a free port in the given range
    """
    s = socket.socket(family, type)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("", 0))
        port = s.getsockname()[1]
        return port
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


def hex_and_printable(c):
    h = hexlify(c.encode("utf-8"))
    p = c if c in string.printable[:-6] else '.'
    return h, p
