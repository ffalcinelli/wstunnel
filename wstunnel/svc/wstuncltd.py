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
import os
import servicemanager
import win32event
import win32service

from tornado.ioloop import IOLoop
import win32serviceutil
import yaml

from wstunnel import winreg
from wstunnel.factory import create_ws_client_endpoint
from wstunnel.registry import get_reg_values

__author__ = 'fabio'
WSTUNNELD_KEY = r"SOFTWARE\wstunneld"


class wstuncltd(win32serviceutil.ServiceFramework):
    """
    The client service class
    """
    _svc_name_ = "WSTunnelClientSvc"
    _svc_display_name_ = "WebSocket tunnel client service"
    _svc_description_ = "This is the client endpoint of the WebSocket tunnel"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        #Read configuration from registry
        os.chdir(get_reg_values(key=WSTUNNELD_KEY, root_key=winreg.HKEY_LOCAL_MACHINE)["install_dir"])
        self.reg_conf = get_reg_values(key=os.path.join(WSTUNNELD_KEY, "client"))
        self.srv = None

    def SvcStop(self):
        """
        Stops the Windows service
        """
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.srv:
            self.srv.stop()
        IOLoop.instance().stop()

    def SvcDoRun(self):
        """
        Starts the Windows service
        """
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        with open(self.reg_conf["config"]) as yaml_conf:
            self.srv = create_ws_client_endpoint(yaml.load(yaml_conf.read()))
        self.srv.start()
        IOLoop.instance().start()


def main():
    """
    Entry point for the WebSocket client tunnel service endpoint
    """
    win32serviceutil.HandleCommandLine(wstuncltd)


if __name__ == "__main__":
    main()
