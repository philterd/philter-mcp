# Docker

The image is published as `philterd/philter-mcp`, with `latest` and `0.1.0` tags for amd64
and arm64.

## As a stdio server

The image's default transport is stdio, so an MCP client can launch a container per
session:

```bash
docker run -i --rm \
  -e PHILTER_BASE_URL=https://host:8080 \
  -e PHILTER_VERIFY_SSL=false \
  philterd/philter-mcp
```

`-i` is required. Without it the container has no stdin and the server cannot receive MCP
messages. See [MCP Clients](clients.md) for wiring this into Claude Desktop or Claude Code.

## As a networked service

Set `PHILTER_MCP_TRANSPORT=streamable-http` to run one long-lived server that multiple
clients connect to. The repository includes a compose file:

```bash
docker compose up --build
```

That serves the MCP endpoint at `http://localhost:8000/mcp` and a health endpoint at
`http://localhost:8000/health`.

The compose file points at `host.docker.internal:8080` by default, which reaches a Philter
running on the host. Override it for your environment:

```bash
PHILTER_BASE_URL=https://philter.internal:8080 docker compose up
```

To run Philter alongside the MCP server, uncomment the `philter` service in
`docker-compose.yaml` and set `PHILTER_BASE_URL=http://philter:8080`.

## Health endpoint

The networked transports serve `GET /health`:

```json
{"status": "UP", "applicationVersion": "0.1.0"}
```

It is unauthenticated, as health checks are meant to be, and reports only this server's own
state. It deliberately does not probe Philter, so a Philter outage cannot cause an
orchestrator to restart a healthy MCP server. Use the `status` tool to check the backend.

There is no health endpoint under `stdio`, which has no listener.

## Notes

The container runs as an unprivileged user (uid 1000). Port 8000 is exposed but used only
by the networked transports.

Images are built by CI on every push and pull request, but pushed to the registry by a
human. A broken Dockerfile fails a pull request without any workflow holding a registry
credential.
