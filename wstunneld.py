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
import logging
import sys
from tornado.log import app_log, gen_log, access_log
import yaml
from tornado.ioloop import IOLoop
from wstunnel.client import WSTunnelClient, WebSocketProxy
from wstunnel.server import WSTunnelServer
from wstunnel.toolbox import get_config, address_to_tuple


#The urlparse module is renamed to urllib.parse in Python 3.
try:
    from urlparse import urljoin, urlparse
except ImportError:
    from urllib.parse import urljoin, urlparse

__author__ = "fabio"


def create_ws_client_endpoint(config):
    """
    Create a client endpoint parsing the configuration file options
    """
    ws_url = config["ws_url"]
    srv = WSTunnelClient()
    proxies = config["proxies"]
    for resource, settings in proxies.items():
        filters = [load_filter(clazz) for clazz in config.get("filters", [])]

        srv.add_proxy(key=settings["port"],
                      ws_proxy=WebSocketProxy(port=int(settings["port"]),
                                              ws_url=urljoin(ws_url, resource),
                                              filters=filters))
    return srv


def create_ws_server_endpoint(config):
    """
    Create a server endpoint parsing the configuration file options
    """
    address, port = address_to_tuple(config["listen"])

    ssl_options = None
    if config["ssl"]:
        ssl_options = config["ssl_options"]

    srv = WSTunnelServer(port=port, address=address, ssl_options=ssl_options)
    proxies = config["proxies"]
    for resource, settings in proxies.items():
        filters = [load_filter(clazz) for clazz in settings.get("filters", [])]

        srv.add_proxy(key=resource, ws_proxy={"address": address_to_tuple(settings["address"]),
                                              "filters": filters})
    return srv


def load_filter(clazz, args=None):
    """
    Load a filter by its fully qualified class name
    """
    import importlib

    path = clazz.split(".")
    mod = importlib.import_module(".".join(path[:-1]))
    Filter = getattr(mod, path[-1])
    return Filter(*args) if args else Filter()


def main(options):
    parser = argparse.ArgumentParser(description='WebSocket tunnel endpoint')
    parser.add_argument("-c", "--config",
                        metavar="CONF_FILE",
                        help="path to a configuration file",
                        default=get_config("wstunneld", "wstunneld.yml"))
    # subparsers = parser.add_subparsers(title="Tunnel proxy modes")
    # parser_local = subparsers.add_parser('local', help="tunnelize client connections over websocket")
    # parser_local.add_argument("-b", "--bind", metavar="ADDRESS", help="bind on the given address")
    # parser_local.add_argument("-u", "--ws-url", metavar="WS_URL", help="websocket tunnel remote url")
    #
    # parser_remote = subparsers.add_parser('remote', help="proxy connections from websocket to server")
    # parser_remote.add_argument("-b", "--bind", metavar="ADDRESS", help="bind on the given address")
    # parser_remote.add_argument("-p", "--port", metavar="PORT", help="listen for connections over this port")
    options = parser.parse_args()

    if not options.config:
        parser.error("No configuration file found. Try using --config option.")

    with open(options.config, 'rt') as f:
        wstun_conf = yaml.load(f.read())

    logging.config.dictConfig(wstun_conf["logging"])

    if wstun_conf["endpoint"] == "client":
        srv = create_ws_client_endpoint(wstun_conf)
    else:
        srv = create_ws_server_endpoint(wstun_conf)
    srv.start()
    for log in (gen_log, app_log, access_log, logging.getLogger("wstunnel.server")):
        log.disabled = False


if __name__ == "__main__":
    main(sys.argv)

    IOLoop.instance().start()




