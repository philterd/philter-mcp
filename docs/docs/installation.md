# Installation

The server speaks MCP over stdio by default and is normally launched by your MCP client
rather than run by hand. It needs a reachable Philter instance.

## Requirements

- Python 3.10 or later, if running from source.
- A running Philter instance. Set `PHILTER_BASE_URL` to point at it.

## Docker

The published image is the quickest way to run the server without a Python environment:

```bash
docker run -i --rm \
  -e PHILTER_BASE_URL=https://host:8080 \
  -e PHILTER_VERIFY_SSL=false \
  philterd/philter-mcp
```

`-i` matters: the default transport is stdio, so the container reads MCP messages on
standard input. Tags `latest` and `0.1.0` are published for amd64 and arm64.

See [Docker](docker.md) for running it as a long-lived networked service instead.

## From source

```bash
pip install git+https://github.com/philterd/philter-mcp
```

This installs a `philter-mcp` console script. Verify it against your Philter instance:

```bash
PHILTER_BASE_URL=https://localhost:8080 PHILTER_VERIFY_SSL=false philter-mcp
```

The process waits for MCP messages on stdin and produces no output on its own. That is
correct behavior for a stdio server. Stop it with Ctrl+C and let your MCP client launch it
instead.

For local development:

```bash
git clone https://github.com/philterd/philter-mcp
cd philter-mcp
pip install -e ".[dev]"
pytest
```

The tests use a mocked HTTP transport, so no running Philter instance is required.

## PyPI

Not yet published. Once it is, `uvx philter-mcp` and `pipx run philter-mcp` will work. In
the meantime use the Docker image or install from git as shown above.

## Transports

`PHILTER_MCP_TRANSPORT` selects the transport:

| Value | Use |
|-------|-----|
| `stdio` (default) | Desktop and IDE clients that launch the server themselves. |
| `streamable-http` | Hosted or containerized deployments. |
| `sse` | Server-sent events, for clients that require it. |

The networked transports bind to `PHILTER_MCP_HOST` (default `127.0.0.1`) and
`PHILTER_MCP_PORT` (default `8000`). An unrecognized value falls back to `stdio`.

Next: [connect an MCP client](clients.md).
