# wstunnel Project Overview

`wstunnel` is a WebSocket tunneling software written in Python, built on top of the [Tornado](http://www.tornadoweb.org/) web framework for asynchronous I/O. It allows tunneling TCP traffic over WebSocket connections, which can be useful for bypassing firewalls or proxies that only allow HTTP(S) traffic.

## Architecture

The project consists of two main components:

- **Client (`WSTunnelClient`):** Listens on a local TCP port and forwards incoming data to a remote WebSocket server.
- **Server (`WSTunnelServer`):** Listens for WebSocket connections and forwards the data to a target TCP service (e.g., a telnet server, a database, etc.).

### Key Components

- `wstunnel/client.py`: Implementation of the client-side tunnel.
- `wstunnel/server.py`: Implementation of the server-side tunnel.
- `wstunnel/filters.py`: Base class and implementations for data filters (e.g., `DumpFilter` for hex dumping traffic).
- `wstunnel/daemon/`: Unix-specific daemon implementation for running the tunnel in the background.
- `wstunnel/svc/`: Windows-specific service implementation using `pywin32`.
- `wstunnel/factory.py`: Factory methods to create tunnel endpoints from configuration files.

## Building and Running

### Requirements

- Python 2.7, 3.3+
- Dependencies: `PyYAML`, `tornado`, `nose`, `mock`
- Windows specific: `pywin32`, `py2exe`

### Installation

```bash
python setup.py install
```

### Running Standalone

The project provides two scripts: `wstuncltd` (client) and `wstunsrvd` (server).

#### Unix (Daemon mode)

```bash
# Start the client tunnel
wstuncltd -c conf/client.yml start

# Start the server tunnel
wstunsrvd -c conf/server.yml start
```

#### Windows (Service mode)

On Windows, the scripts act as services. You might need to configure the registry as described in the `README.md`.

### Building Windows Binaries

To create a standalone `.exe` using `py2exe`:

```bash
python setup.py py2exe
```

## Testing

The project uses `nose` for testing.

```bash
python setup.py test
```

Or directly using `nosetests`:

```bash
nosetests wstunnel/test
```

## Development Conventions

- **Asynchronous I/O:** The project heavily uses Tornado's `IOLoop` and asynchronous streams (`IOStream`, `WebSocketClientConnection`).
- **Configuration:** Configuration is handled via YAML files. Key sections include `proxies`, `logging`, and `ssl_options`.
- **Filtering:** You can intercept and modify traffic by implementing a `BaseFilter` and adding it to the `proxies` configuration or via the API.
- **Cross-platform:** The codebase maintains compatibility between Unix and Windows, particularly in how background processes (daemons vs. services) are handled.
- **Python Compatibility:** Supports both Python 2 and Python 3.

## Key Files

- `README.md`: High-level overview and quick start guide.
- `setup.py`: Package configuration, dependencies, and entry points.
- `wstunnel/factory.py`: Central point for creating endpoints from config.
- `wstunnel/client.py` & `wstunnel/server.py`: Core logic for tunneling.
- `wstunnel/test/`: Comprehensive test suite.
