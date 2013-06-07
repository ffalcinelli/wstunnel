wstunnel
========

A WebSocket tunneling software written in python on top of tornado http://www.tornadoweb.org/ web framework for asynchronous I/O.

TravisCI status: [![Build Status](https://travis-ci.org/ffalcinelli/wstunnel.png)](https://travis-ci.org/ffalcinelli/wstunnel)

Currently works on

* python 2.7
* python 3.3

The API works on windows too, but a service it's still to be implemented.

Warnings
========

On windows the server tunnel endpoint may perform not so well. There's a limit on `select()` call that impacts Tornado
loop for asynchronous I/O.

You may want to read this conversation https://groups.google.com/forum/?fromgroups#!topic/python-tornado/oSbxI9X28MM

Quick start
===========

The standalone way
------------------

You can start the client and server endpoints using the `wstuncltd.py` and `wstunsrvd.py` scripts respectively.

The command arguments are exactly the same, the two scripts are provided for simplicity. Once started, the tunnel endpoint
gets daemonized and you can stop or restart by issuing the respective commands

    $ ./wstuncltd.py --help
    usage: wstuncltd.py [-h] [-c CONF_FILE] {start,stop,restart}

    WebSocket tunnel client endpoint

    positional arguments:
      {start,stop,restart}  Command to execute

    optional arguments:
      -h, --help            show this help message and exit
      -c CONF_FILE, --config CONF_FILE
                            path to a configuration file



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

    $ ./wstuncltd.py -c conf/client.yml start
    $ ./wstunsrvd.py -c conf/server.yml start


The API way
-----------

You can use the tunneling endpoints in your code. Check the test suite for examples.

    $ python setup.py install

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

    $ git clone https://github.com/ffalcinelli/wstunnel wstunnel

Create a `virtualenv`, it's a recommended practice, and install the dependecies using `pip`

    $ pip install -r requirements.txt

Happy hacking :-)

TODOs
=====

[x] "Daemonize" the standalone way on unix.
[ ] A Windows Service would be nice for the Microsoft's platform.
[x] Create 2 different executables for client and server tunnels (maybe `wstuncltd` and `wstunsrvd`?). Explicit is better than implicit.
[ ] Enhance the `filter` support with custom configuration from yaml files.

License
=======

LGPLv3

Copyright (c) 2013 Fabio Falcinelli <fabio.falcinelli@gmail.com>

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