#!/bin/env python
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
import argparse
import sys
import yaml
from wstunnel.daemon import WSTunnelServerDaemon
from wstunnel.toolbox import get_config

__author__ = "fabio"


def main():
    """
    Entry point for the WebSocket server tunnel daemon endpoint
    """
    parser = argparse.ArgumentParser(description='WebSocket tunnel server endpoint')
    parser.add_argument("-c", "--config",
                        metavar="CONF_FILE",
                        help="path to a configuration file",
                        default=get_config("wstunneld", "wstunsrvd.yml"))
    # parser.add_argument("-p", "--pid-file",
    #                     metavar="PID_FILE",
    #                     help="path to a pid file")
    parser.add_argument("command",
                        help="Command to execute", choices=["start", "stop", "restart"])
    options = parser.parse_args()

    if not options.config:
        parser.error("No configuration file found. Try using --config option.")

    with open(options.config, 'rt') as f:
        conf = yaml.load(f.read())

        if conf["endpoint"] == "server":
            wstund = WSTunnelServerDaemon(conf)
        else:
            raise ValueError("Wrong name for endpoint")

        getattr(wstund, options.command)()
        sys.exit(0)


if __name__ == "__main__":
    main()