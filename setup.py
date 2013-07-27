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
import sys
from setuptools import setup, find_packages
import wstunnel

__author__ = 'fabio'

kwargs = dict(name='wstunnel',
              version='0.0.1',
              description='A Python WebSocket Tunnel',
              author='Fabio Falcinelli',
              author_email='fabio.falcinelli@gmail.com',
              url='https://github.com/ffalcinelli/wstunnel',
              download_url='https://github.com/ffalcinelli/wstunnel/tarball/0.0.1',
              keywords=['tunneling', 'websocket', 'ssl'],
              packages=find_packages(),
              classifiers=[
                  'Development Status :: 2 - Pre-Alpha',
                  'Intended Audience :: Developers',
                  'Intended Audience :: System Administrators',
                  'Intended Audience :: Telecommunications Industry',
                  'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
                  'Programming Language :: Python',
                  'Topic :: Software Development :: Libraries :: Python Modules',
                  'Topic :: Utilities',
              ],
              setup_requires=['nose'],
              test_suite='nose.collector')

if not sys.platform.startswith("win"):
    install_requires = []
    with open(os.path.join(os.path.dirname(__file__), "requirements.txt")) as reqs:
        for req in reqs:
            install_requires.append(req)

    kwargs["install_requires"] = install_requires
    kwargs["entry_points"] = {
        "console_scripts": [
            "wstuncltd = wstunnel.daemon.wstuncltd:main",
            "wstunsrvd = wstunnel.daemon.wstunsrvd:main",
        ]
    }
else:

    install_requires = []
    with open(os.path.join(os.path.dirname(__file__), "requirements_windows.txt")) as reqs:
        for req in reqs:
            install_requires.append(req)

    if "py2exe" in sys.argv:
        if wstunnel.PY2:
            from wstunnel.svc import wstunsrvd, wstuncltd
            import py2exe

            class Target:
                def __init__(self, **kw):
                    self.__dict__.update(kw)
                    # for the versioninfo resources
                    self.version = kwargs["version"]
                    self.company_name = "N.A."
                    self.copyright = "Copyright (c) 2013 Fabio Falcinelli"
                    self.name = kwargs["name"]

            tunclt_svc = Target(
                # used for the versioninfo resource
                description=wstuncltd.wstuncltd._svc_description_,
                # what to build. For a service, the module name (not the
                # filename) must be specified!
                modules=["wstunnel.svc.wstuncltd"],
                cmdline_style='pywin32',
            )

            tunsrv_svc = Target(
                # used for the versioninfo resource
                description=wstunsrvd.wstunsrvd._svc_description_,
                # what to build. For a service, the module name (not the
                # filename) must be specified!
                modules=["wstunnel.svc.wstunsrvd"],
                cmdline_style='pywin32',
            )

            kwargs["service"] = [tunclt_svc, tunsrv_svc]
            kwargs["options"] = {
                "py2exe": {
                    "compressed": 1,
                    "optimize": 2,
                }
            }
        else:
            sys.stderr.write("Warning: you're using python {0}.{1}.{2} "
                             "which is not supported yet by py2exe.\n".format(sys.version_info[0],
                                                                              sys.version_info[1],
                                                                              sys.version_info[2]))
            sys.exit(-1)
    else:
        kwargs["entry_points"] = {
            "console_scripts": [
                "wstuncltd = wstunnel.svc.wstuncltd:main",
                "wstunsrvd = wstunnel.svc.wstunsrvd:main",
            ]
        }

setup(**kwargs)