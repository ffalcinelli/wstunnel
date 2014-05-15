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
from wstunnel import join_url
from wstunnel.client import WSTunnelClient, WebSocketProxy
from wstunnel.server import WSTunnelServer
from wstunnel.toolbox import address_to_tuple

__author__ = 'fabio'


def load_filter(clazz, args=None):
    """
    Load a filter by its fully qualified class name
    """
    import importlib

    path = clazz.split(".")
    mod = importlib.import_module(".".join(path[:-1]))
    Filter = getattr(mod, path[-1])
    return Filter(*args) if args else Filter()


def create_ws_client_endpoint(config):
    """
    Create a client endpoint parsing the configuration file options
    """
    ws_url = config["ws_url"]
    srv = WSTunnelClient(ws_options=config.get("ws_options", {}))
    proxies = config["proxies"]
    for resource, settings in proxies.items():
        filters = [load_filter(clazz) for clazz in config.get("filters", [])]

        srv.add_proxy(key=settings["port"],
                      ws_proxy=WebSocketProxy(  #address=settings.get("address", ''),
                                                port=int(settings.get("port", 0)),
                                                ws_url=join_url(ws_url, resource),
                                              filters=filters,
                                              ws_options=config.get("ws_options", {})))
    return srv


def create_ws_server_endpoint(config):
    """
    Create a server endpoint parsing the configuration file options
    """
    address, port = address_to_tuple(config["listen"])

    ssl_options = None
    if config["ssl"]:
        ssl_options = config["ssl_options"]

    srv = WSTunnelServer(port=port,
                         address=address,
                         ssl_options=ssl_options)
    proxies = config["proxies"]
    for resource, settings in proxies.items():
        filters = [load_filter(clazz) for clazz in settings.get("filters", [])]

        srv.add_proxy(key=resource,
                      ws_proxy={"address": address_to_tuple(settings["address"]),
                                "filters": filters})
    return srv


