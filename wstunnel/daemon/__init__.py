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
import sys
import atexit
import signal
import logging
import time
import os
from tornado.ioloop import IOLoop
from wstunnel.factory import create_ws_client_endpoint, create_ws_server_endpoint

__author__ = 'fabio'
SIG_NAMES = dict((k, v) for v, k in signal.__dict__.items() if v.startswith('SIG'))
SHUTDOWN_POLL = 0.2


class Daemon(object):
    """
    Handles common daemon operations: pid file, start/stop/restart commands
    """

    def __init__(self, pid_file, user=None, workdir="/", umask=0):
        self.pid_file = pid_file
        self.user = user
        self.workdir = workdir
        self.umask = umask
        self.name = type(self).__name__
        self.dev_null = None

    def switch_user(self):
        """
        Change the user running the daemon
        """
        if self.user:
            self.uid = self.user

    @property
    def uid(self):
        return os.getuid()

    @uid.setter
    def uid(self, value):
        import pwd

        if isinstance(value, int):
            self.user = pwd.getpwuid(value).pw_name
        else:
            value = pwd.getpwnam(self.user).pw_uid
        os.setuid(value)

    def hush(self, **kwargs):
        """
        Redirect standard fd to the /dev/null if no one is provided
        """
        sys.stdout.flush()
        sys.stderr.flush()

        for name in "stdin", "stdout", "stderr":
            if not kwargs.get(name):
                if not self.dev_null:
                    self.dev_null = open(os.devnull, "r+b")
                kwargs[name] = self.dev_null

        os.dup2(kwargs["stdin"].fileno(), sys.stdin.fileno())
        os.dup2(kwargs["stdout"].fileno(), sys.stdout.fileno())
        os.dup2(kwargs["stderr"].fileno(), sys.stderr.fileno())

    def delete_pid_file(self):
        """
        If no daemon running, delete the pid file
        """
        if os.path.exists(self.pid_file) and not self.is_running():
            os.remove(self.pid_file)

    def register_shutdown(self):
        """
        Register the shutdown hook when trapping SIGTERM
        """
        signal.signal(signal.SIGTERM, self._gracefully_terminate)

    def daemonize(self):
        """
        Daemonize the process with the double fork hack
        """
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)

            os.chdir(self.workdir)
            os.setsid()
            os.umask(self.umask)

            pid = os.fork()
            if pid > 0:
                sys.exit(0)

            self.hush()

            atexit.register(self.delete_pid_file)

            self.register_shutdown()

            with open(self.pid_file, 'w+') as f:
                f.write(str(os.getpid()) + '\n')

        except OSError as oserr:
            sys.stderr.write("Daemonize {0} failed: {1}\n".format(self.name, oserr))
            sys.exit(oserr.errno)

    def read_pid_file(self):
        """
        Read the pid from the pid file, if available
        """
        try:
            with open(self.pid_file, 'r') as pf:
                pid = int(pf.read().strip())
                return pid
        except IOError:
            return None

    def is_running(self, pid=None):
        """
        Check if the given pid corresponds to an alive process. If no pid is given, try to read from pid file
        """
        pid = pid if pid else self.read_pid_file()
        try:
            if pid:
                os.kill(pid, 0)
            else:
                return False
        except OSError:
            return False
        else:
            return True

    def start(self):
        """
        Starts the daemon. If a user have been setup, demote to that user
        """
        pid = self.read_pid_file()
        if not pid:
            self.daemonize()
            self.run()
        else:
            sys.stderr.write("{0} is already running [pid: {1}]\n".format(self.name, pid))
            sys.exit(-1)

    def stop(self):
        """
        Stops the daemon. Invokes the shutdown hook to gracefully terminate the service
        """
        try:
            pid = self.read_pid_file()
            if pid:
                while self.is_running(pid):
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(SHUTDOWN_POLL)
        except OSError as oserr:
            msg = "Could not stop {0} daemon: {1}\n"
            sys.stderr.write(msg.format(self.name, oserr))
            sys.exit(oserr.errno)
        else:
            self.delete_pid_file()

    def restart(self):
        """
        Restarts the daemon by simply stopping and starting again.
        """
        self.stop()
        time.sleep(SHUTDOWN_POLL)
        self.start()

    def run(self, *args):
        """
        Hook to call the business service. Override to launch your service
        """
        pass

    def _gracefully_terminate(self, *args):
        self.shutdown(*args)
        if self.dev_null:
            self.dev_null.close()

    def shutdown(self, *args):
        """
        Hook called when a shutdown is requested. Override to add your graceful service termination
        """
        pass


class WSTunnelDaemon(Daemon):
    """
    WebSocket Tunnel Daemon
    """

    def __init__(self, config):
        super(WSTunnelDaemon, self).__init__(pid_file=config["pid_file"],
                                             user=config["user"],
                                             workdir=config.get("workdir", os.getcwd()))
        self.config = config
        logging.config.dictConfig(self.config["logging"])
        self._srv = None

    def run(self):
        """
        Called when daemon starts
        """
        for logger_name in self.config["logging"]["loggers"].keys():
            logging.getLogger(logger_name).disabled = False
        self._srv.start()
        self.switch_user()
        IOLoop.instance().start()

    def shutdown(self, *args):
        """
        This will be called when daemon will be stopped
        """
        if self._srv:
            self._srv.stop()
        for logger_name in self.config["logging"]["loggers"].keys():
            logger = logging.getLogger(logger_name)
            for h in list(logger.handlers):
                logger.removeHandler(h)
                h.flush()
                h.close()
        IOLoop.instance().stop()


class WSTunnelClientDaemon(WSTunnelDaemon):
    """
    Shortcut to have a wstunnel client endpoint
    """

    def run(self):
        self._srv = create_ws_client_endpoint(self.config)
        super(WSTunnelClientDaemon, self).run()


class WSTunnelServerDaemon(WSTunnelDaemon):
    """
    Shortcut to have a wstunnel server endpoint
    """

    def run(self):
        self._srv = create_ws_server_endpoint(self.config)
        super(WSTunnelServerDaemon, self).run()

