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
from logging import config

import copy
import sys
import yaml
from wstunnel import EnhancedRotatingFileHandler
from wstunnel.toolbox import hex_dump

logging.handlers.RotatingFileHandler = EnhancedRotatingFileHandler

__author__ = 'fabio'

WS_TO_SOCK = 0
SOCK_TO_WS = 1
BOTH = 2


class FilterException(Exception):
    pass


class BaseFilter(object):
    def __init__(self, *args, **kwargs):
        pass

    def ws_to_socket(self, data):
        """
        Override this method to perform filtering on WebSocket to Socket dataflow
        """
        return data

    def socket_to_ws(self, data):
        """
        Override this method to perform filtering on Socket to WebSocket dataflow
        """
        return data


class DumpFilter(BaseFilter):
    """
    Dump data on the given filepath or stdout
    """
    default_conf = {
        "version": 1,
        "formatters": {
            "dump_formatter": {
                "format": "[%(asctime)s] %(name)-15s - %(message)s",
            }
        },
        "handlers": {
            "dump_file_handler": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "dump_formatter",
                "filename": "logs/dump.log",
                "maxBytes": 536870912,
                "backupCount": 10,
                "encoding": "utf8",
            }
        },
        "loggers": {
            __name__: {
                "level": "INFO",
                "handlers": ["dump_file_handler"],
                "propagate": "no",
            }
        }
    }

    def __init__(self, handler=None, fmt=None, conf_file=None, **kwargs):
        super(DumpFilter, self).__init__()

        if conf_file:
            with open(conf_file, "rt") as yml:
                conf = yaml.load(yml)
        else:
            conf = copy.copy(self.default_conf)
            if handler:
                conf["handlers"]["dump_file_handler"].update(handler)
            if fmt:
                conf["formatters"]["dump_formatter"].update(fmt)

        logging.config.dictConfig(conf)
        self.logger = logging.getLogger(__name__)

    def ws_to_socket(self, data, **kwargs):
        try:
            self.logger.info("[-->] From WebSocket endpoint\n{}".format(hex_dump(data)))
        except Exception as e:
            #Ignore errors... DumpFilter should not interpose the protocol flow
            sys.stderr.write("Unable to log filter dump: %s" % str(e))
        return data

    def socket_to_ws(self, data, **kwargs):
        try:
            self.logger.info("[<--] To WebSocket endpoint\n{}".format(hex_dump(data)))
        except Exception as e:
            #Ignore errors... DumpFilter should not interpose the protocol flow
            sys.stderr.write("Unable to log filter dump: %s" % str(e))
        return data
