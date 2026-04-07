wstunnel 
========
[![Build Status](https://github.com/ffalcinelli/wstunnel/actions/workflows/ci.yml/badge.svg)](https://github.com/ffalcinelli/wstunnel/actions/workflows/ci.yml)

A WebSocket tunneling software written in python on top of [tornado](http://www.tornadoweb.org/) web framework for asynchronous I/O.

Currently works and tested on modern Python 3.8+ both on Unix and Windows.

Quick start
===========

Installation
------------

The project has been modernized and uses `uv` for fast package management.

To install dependencies and create the environment:
```bash
$ uv sync
```

To run the endpoints:
```bash
# Run the client
$ uv run wstuncltd -c conf/client.yml start

# Run the server
$ uv run wstunsrvd -c conf/server.yml start
```

The scripts act like daemons on unix system and services on windows.

On Windows, the service variants can be accessed via `wstuncltd-svc` and `wstunsrvd-svc`.

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

As a warm up you can edit the provided `conf/client.yml` and `conf/server.yml` and run each side separately.


The API way
-----------

You can use the tunneling endpoints in your code. Check the test suite for examples.
By default, a `DumpFilter` class is provided to hex dump all network traffic.

### Tunnel endpoints example

The following are examples of usage of the client and server endpoints.


```python
clt_tun = WSTunnelClient(proxies={50023: "wss://localhost:9000/telnet",
                                  80: "wss://localhost:9000/http"},
                         family=socket.AF_INET)
clt_tun.install_filter(DumpFilter(handler={"filename": "/tmp/clt_log"}))
clt_tun.start()
tornado.ioloop.IOLoop.current().start()
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
tornado.ioloop.IOLoop.current().start()
```

Pay attention to the `IOLoop` instance. Until not started, the requests will not be served by the tunnel.


The developer way
-------------------

If you want to help me and contribute, start by cloning the repo

```
$ git clone https://github.com/ffalcinelli/wstunnel wstunnel
```

Make sure you have `uv` installed, then run:

```bash
$ uv sync
```

To run the test suite:

```bash
$ uv run pytest wstunnel/test
```

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
