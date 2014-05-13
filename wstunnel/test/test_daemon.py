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
import shutil
import unittest
import sys
import os


__author__ = 'fabio'

fixture = os.path.join(os.path.dirname(__file__), "fixture")

if not sys.platform.startswith("win"):
    import mock
    import yaml
    from tornado.ioloop import IOLoop
    from wstunnel.toolbox import random_free_port
    from wstunnel.daemon import WSTunnelClientDaemon, WSTunnelServerDaemon, Daemon, wstuncltd, wstunsrvd

    class DaemonTestCase(unittest.TestCase):
        """
        TestCase for the generic Daemon super class
        """

        def setup_logging(self):
            self.log_file = os.path.join(fixture, "logs", "wstun_test_{0}.log".format(os.getpid()))
            self.pid_file = os.path.join(fixture, "temp", "wstun_test_{0}.log".format(os.getpid()))

            for f in self.log_file, self.pid_file:
                if os.path.exists(f):
                    os.remove(f)

        def setUp(self):
            self.setup_logging()
            #open(self.log_file, 'w').close()

            self.daemon = Daemon(self.pid_file, workdir=fixture)
            self.daemon.hush = lambda **kwargs: 0

        def test_daemonize(self):
            """
            Tests the daemonize method by checking the pid file being written
            """
            with mock.patch("os.fork", return_value=0):
                with mock.patch("os.setsid"):
                    self.daemon.daemonize()

            self.assertTrue(os.path.exists(self.pid_file))

        def test_kill_parent(self):
            """
            Tests the daemonize method killing the parent
            """
            with mock.patch("os.fork", return_value=1):
                with self.assertRaises(SystemExit) as sysexit:
                    self.daemon.daemonize()
                self.assertEqual(sysexit.exception.code, 0)
            self.assertFalse(os.path.exists(self.pid_file))

        def test_fork_failed(self):
            """
            Tests the daemonize method failure when fork fails
            """

            def mock_fork(*args):
                raise OSError()

            with mock.patch("os.fork", return_value=1):
                self.assertRaises(SystemExit, self.daemon.daemonize)

            self.assertFalse(os.path.exists(self.pid_file))


        def test_is_not_running(self):
            """
            Test daemon is not running method by reading the pid file
            """
            self.assertFalse(self.daemon.is_running())

        def test_is_running(self):
            """
            Test is running method by passing a pid of a running process
            """
            self.assertTrue(self.daemon.is_running(pid=os.getpid()))

        def test_start_already_running(self):
            """
            Test daemon started when another instance is running
            """
            if not os.path.exists(os.path.dirname(self.pid_file)):
                os.makedirs(os.path.dirname(self.pid_file))
            with open(self.pid_file, "w") as pid:
                pid.write(str(os.getpid()) + "\n")

            with mock.patch("os.fork", return_value=0):
                with self.assertRaises(SystemExit) as sysexit:
                    self.daemon.start()
                self.assertEqual(sysexit.exception.code, -1)

        def test_start_and_stop(self):
            """
            Test daemon start and stop
            """

            def mock_shutdown(*args):
                self.daemon.is_running = lambda *args: False
                if os.path.exists(self.pid_file):
                    os.remove(self.pid_file)
                return False

            with mock.patch("os.fork", return_value=0):
                with mock.patch("os.setsid", return_value=0):
                    self.daemon.start()

                with mock.patch("os.kill", new=mock_shutdown):
                    self.daemon.stop()

            self.assertFalse(os.path.exists(self.pid_file))

        def test_restart(self):
            """
            Test daemon restart
            """

            def mock_shutdown(*args):
                self.daemon.is_running = lambda *args: False
                if os.path.exists(self.pid_file):
                    os.remove(self.pid_file)
                self.daemon._gracefully_terminate()
                return False

            with mock.patch("os.fork", return_value=0):
                with mock.patch("os.setsid", return_value=0):
                    with mock.patch("os.kill", new=mock_shutdown):
                        self.daemon.restart()

            self.assertTrue(os.path.exists(self.pid_file))

        def tearDown(self):
            self.daemon.shutdown()
            for f in [self.log_file, self.pid_file]:
                if os.path.exists(f):
                    os.remove(f)
            for d in map(os.path.dirname, [self.log_file, self.pid_file]):
                if os.path.exists(d):
                    print("Removing ", d)
                    shutil.rmtree(d)


    class WSTunnelClientDaemonTestCase(DaemonTestCase):
        """
        TestCase for the client tunnel endpoint in daemon mode
        """

        def setUp(self):
            #super(WSTunnelClientDaemonTestCase, self).setUp()
            self.setup_logging()

            with open(os.path.join(fixture, "wstuncltd.yml")) as f:
                self.tun_conf = yaml.load(f.read())
            self.tun_conf["logging"]["handlers"]["file_handler"]["filename"] = self.log_file
            self.tun_conf["pid_file"] = self.pid_file
            self.tun_conf["proxies"]["/test"]["port"] = random_free_port()

            IOLoop.instance().start = lambda: 0
            IOLoop.instance().stop = lambda: 0

            self.daemon = WSTunnelClientDaemon(self.tun_conf)
            self.daemon.hush = lambda **kwargs: 0

        def test_create_logging_directory(self):
            """
            Tests automatic creation of logging directory through monkey patch on RotatingFileHandler
            """
            self.assertTrue(os.path.exists(os.path.dirname(self.log_file)))

    class WSTunnelServerDaemonTestCase(DaemonTestCase):
        """
        TestCase for the server tunnel endpoint in daemon mode
        """

        def setUp(self):
            # super(WSTunnelServerDaemonTestCase, self).setUp()
            self.setup_logging()

            with open(os.path.join(fixture, "wstunsrvd.yml")) as f:
                self.tun_conf = yaml.load(f.read())
            self.tun_conf["logging"]["handlers"]["file_handler"]["filename"] = self.log_file
            self.tun_conf["pid_file"] = self.pid_file
            self.tun_conf["listen"] = random_free_port()

            IOLoop.instance().start = lambda: 0
            IOLoop.instance().stop = lambda: 0

            self.daemon = WSTunnelServerDaemon(self.tun_conf)
            self.daemon.hush = lambda **kwargs: 0

        def test_create_logging_directory(self):
            """
            Tests automatic creation of logging directory through monkey patch on RotatingFileHandler
            """
            self.assertTrue(os.path.exists(os.path.dirname(self.log_file)))

    class WSTunnelSSLClientDaemonTestCase(DaemonTestCase):
        """
        TestCase for the ssl client tunnel endpoint in daemon mode
        """

        def setUp(self):
            super(WSTunnelSSLClientDaemonTestCase, self).setUp()

            with open(os.path.join(fixture, "wstuncltd.yml")) as f:
                self.tun_conf = yaml.load(f.read())
            self.tun_conf["logging"]["handlers"]["file_handler"]["filename"] = self.log_file
            self.tun_conf["pid_file"] = self.pid_file
            self.tun_conf["proxies"]["/test"]["port"] = random_free_port()
            self.tun_conf["ws_url"] = "wss://localhost:9000/"

            IOLoop.instance().start = lambda: 0
            IOLoop.instance().stop = lambda: 0

            self.daemon = WSTunnelClientDaemon(self.tun_conf)
            self.daemon.hush = lambda **kwargs: 0

    class WSTunnelSSLServerDaemonTestCase(DaemonTestCase):
        """
        TestCase for the ssl server tunnel endpoint in daemon mode
        """

        def setUp(self):
            super(WSTunnelSSLServerDaemonTestCase, self).setUp()

            with open(os.path.join(fixture, "wstunsrvd.yml")) as f:
                self.tun_conf = yaml.load(f.read())
            self.tun_conf["logging"]["handlers"]["file_handler"]["filename"] = self.log_file
            self.tun_conf["pid_file"] = self.pid_file
            self.tun_conf["listen"] = random_free_port()
            self.tun_conf["ssl"] = True
            self.tun_conf["ssl_options"].update({"certfile": os.path.join(fixture, "localhost.pem"),
                                                 "keyfile": os.path.join(fixture, "localhost.key")})

            IOLoop.instance().start = lambda: 0
            IOLoop.instance().stop = lambda: 0

            self.daemon = WSTunnelServerDaemon(self.tun_conf)
            self.daemon.hush = lambda **kwargs: 0

    class MainTestCase(unittest.TestCase):
        """
        TestCase for the main method parsing command line arguments
        """

        def setUp(self):
            if not os.path.exists(os.path.join(fixture, "logs")):
                os.makedirs(os.path.join(fixture, "logs"))
            if not os.path.exists(os.path.join(fixture, "temp")):
                os.makedirs(os.path.join(fixture, "temp"))

        # TODO: these tests do not work when you have wstunnel actually installed
        # def test_wstuncltd_no_config(self):
        #     """
        #     Tests invocation without explicit config file. Since no file is in common directories
        #     it will fail
        #     """
        #     sys.argv = ["./wstuncltd.py", "stop"]
        #     with self.assertRaises(SystemExit) as sysexit:
        #         wstuncltd.main()
        #     self.assertEqual(sysexit.exception.code, 2)
        #
        # def test_wstunsrvd_no_config(self):
        #     """
        #     Tests invocation without explicit config file. Since no file is in common directories
        #     it will fail
        #     """
        #     sys.argv = ["./wstunsrvd.py", "stop"]
        #     with self.assertRaises(SystemExit) as sysexit:
        #         wstunsrvd.main()
        #     self.assertEqual(sysexit.exception.code, 2)

        def test_wstuncltd(self):
            """
            Tests invocation of daemon client method via command line
            """
            sys.argv = ["./wstuncltd.py", "-c", os.path.join(fixture, "wstuncltd.yml"), "stop"]
            with self.assertRaises(SystemExit) as sysexit:
                wstuncltd.main()
            self.assertEqual(sysexit.exception.code, 0)

        def test_wstunsrvd(self):
            """
            Tests invocation of daemon server method via command line
            """
            sys.argv = ["./wstunsrvd.py", "-c", os.path.join(fixture, "wstunsrvd.yml"), "stop"]
            with self.assertRaises(SystemExit) as sysexit:
                wstunsrvd.main()
            self.assertEqual(sysexit.exception.code, 0)
