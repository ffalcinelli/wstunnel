wstunnel 
========
[![Build Status](https://travis-ci.org/ffalcinelli/wstunnel.png)](https://travis-ci.org/ffalcinelli/wstunnel)[![Coverage Status](https://coveralls.io/repos/ffalcinelli/wstunnel/badge.png)](https://coveralls.io/r/ffalcinelli/wstunnel)[![PyPI Version](https://pypip.in/v/wstunnel/badge.png)](https://crate.io/packages/wstunnel)	

A WebSocket tunneling software written in python on top of [tornado](http://www.tornadoweb.org/) web framework for asynchronous I/O.

Currently works and tested on

* python 2.7
* python 3.3

both on unix (at least Fedora 18 and OSX) and Windows 7.


Warnings
========

On windows the server tunnel endpoint may perform not so well. There's a limit on `select()` call that impacts Tornado
loop for asynchronous I/O.

You may want to read [this conversation](https://groups.google.com/forum/?fromgroups#!topic/python-tornado/oSbxI9X28MM) for more details.

Quick start
===========

Installation
------------

You can install `wstunnel` with

```
$ python setup.py install
```

This will install the packages and two execution scripts, `wstuncltd` and `wstunsrvd` for the client and server endpoints respectively.

The scripts act like daemons on unix system and services on windows.

On the former platform you can provide configuration with the -c option

```
$ wstuncltd -c conf/client.yml start
```

while on the latter platform a regitry key is expected

```
Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\SOFTWARE\wstunneld]
"install_dir"="C:\\Users\\Fabio\\Documents\\GitHub\\wstunnel"

[HKEY_LOCAL_MACHINE\SOFTWARE\wstunneld\client]
"config"="C:\\Users\\Fabio\\Documents\\GitHub\\wstunnel\\conf\\client.yml"

[HKEY_LOCAL_MACHINE\SOFTWARE\wstunneld\server]
"config"="C:\\Users\\Fabio\\Documents\\GitHub\\wstunnel\\conf\\server.yml"
```

On windows you can get a binary distribution by running

```
$ python setup.py py2exe
```

in the `dist` folder a `wstuncltd.exe` and `wstunsrvd.exe` will be generated.


The standalone way
------------------

The command arguments are exactly the same for the client and server endpoints.
Anyway, options differs from unix and windows as you can see by invoking the `help`

```
$ wstuncltd --help
usage: wstuncltd [-h] [-c CONF_FILE] {start,stop,restart}

WebSocket tunnel client endpoint

positional arguments:
  {start,stop,restart}  Command to execute

optional arguments:
  -h, --help            show this help message and exit
  -c CONF_FILE, --config CONF_FILE
                        path to a configuration file
```

whereas on windows
```
C:\Users\Fabio\Documents\GitHub\wstunnel>wstuncltd.exe
Usage: 'wstuncltd-script.py [options] install|update|remove|start [...]|stop|restart [...]|debug [...]'
Options for 'install' and 'update' commands only:
 --username domain\username : The Username the service is to run under
 --password password : The password for the username
 --startup [manual|auto|disabled|delayed] : How the service starts, default = manual
 --interactive : Allow the service to interact with the desktop.
 --perfmonini file: .ini file to use for registering performance monitor data
 --perfmondll file: .dll file to use when querying the service for
   performance data, default = perfmondata.dll
Options for 'start' and 'stop' commands only:
 --wait seconds: Wait for the service to actually start or stop.
                 If you specify --wait with the 'stop' option, the service
                 and all dependent services will be stopped, each waiting
                 the specified period.

C:\Users\Fabio\Documents\GitHub\wstunnel>
```

The same applies on .exe binaries.

Configuration
-------------

The configuration file is in YAML syntax. The following is an example of telnet mapping

Tunnel Client side

```yaml
endpoint: client
ws_url: ws://localhost:9000/

pid_file: /tmp/wstuncltd.pid
user: null
workdir: null

proxies:
    /telnet:
      port: 50023
      filters: []
```

Tunnel Server side

```yaml
endpoint: server
listen: 9000
ssl: no
ssl_options:
  certfile: null
  keyfile: null

pid_file: /tmp/wstunsrvd.pid
user: null
workdir: null

proxies:
  /telnet:
    address: 192.168.1.2:23
    filters: [wstunnel.filters.DumpFilter]
```

As a warm up you can edit the provided `conf/client.yml` and `conf/server.yml` and run each side separately


The API way
-----------

You can use the tunneling endpoints in your code. Check the test suite for examples.
By default, a `DumpFilter` class is provided to hex dump all network traffic.
I'm planning to extend the plugin feature so this will change very soon.

### Tunnel endpoints example

The following are examples of usage of the client and server endpoints.


```python
clt_tun = WSTunnelClient(proxies={50023: "wss://localhost:9000/telnet",
                                  80: "wss://localhost:9000/http"},
                         family=socket.AF_INET)
clt_tun.install_filter(DumpFilter(handler={"filename": "/tmp/clt_log"}))
clt_tun.start()
IOLoop.instance().start()
```

```python
srv_tun = WSTunnelServer(9000,
                         proxies={"/telnet": ("192.168.1.2", 23),
                                  "/http": ("192.168.1.2", 80)},
                         ssl_options={
                                "certfile": "certs/wstunsrv.pem",
                                "keyfile":  "certs/wstunsrv.key",
                         })

srv_tun.install_filter(DumpFilter(handler={"filename": "/tmp/srv_log"}))
srv_tun.start()
IOLoop.instance().start()
```

Pay attention to the `IOLoop` instance. Until not started, the requests will not be served by the tunnel.


The developer way
-------------------

If you want to help me and contribute, start by cloning the repo

```
$ git clone https://github.com/ffalcinelli/wstunnel wstunnel
```

Create a `virtualenv`, it's a recommended practice, and install the dependencies using `pip`

```
$ pip install -r requirements.txt
```

### Windows requirements

```
$ pip install -r requirements_windows.txt
```

Anyway, `pywin32` and `py2exe` have to be installed using their installers.

For `py2exe` I've successfully got binary distribution on python 2.7 but no luck with python 3.3

Happy hacking :-)

TODOs
=====

- ~~"Daemonize" the standalone way on unix~~
- ~~A Windows Service would be nice for the Microsoft's platform~~
- ~~Create 2 different executables for client and server tunnels (maybe `wstuncltd` and `wstunsrvd`?). Explicit is better than implicit~~
- Enhance the `filter` support with custom configuration from yaml files
- Test, test, test... Expecially on Windows
- Provide an NSIS installer and a nicer way to customize on windows

License
=======

LGPLv3

Copyright (c) 2014 Fabio Falcinelli <fabio.falcinelli@gmail.com>

> This program is free software: you can redistribute it and/or modify
> it under the terms of the GNU Lesser General Public License as published by
> the Free Software Foundation, either version 3 of the License, or
> (at your option) any later version.
>
> This program is distributed in the hope that it will be useful,
> but WITHOUT ANY WARRANTY; without even the implied warranty of
> MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
> GNU Lesser General Public License for more details.
>
> You should have received a copy of the GNU Lesser General Public License
> along with this program.  If not, see <http://www.gnu.org/licenses/>.


This file was modified by PyCharm 2.7.2 for binding GitHub repository