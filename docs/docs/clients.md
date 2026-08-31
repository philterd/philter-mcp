# MCP Clients

The server is launched by your MCP client over stdio. Configuration is passed as
environment variables. See [Configuration](configuration.md) for the full list.

The examples below use the Docker image, which requires no Python environment. If you
installed from source, replace the command with `philter-mcp` and drop the `args`.

## Claude Desktop

Edit `claude_desktop_config.json` through Settings, Developer, Edit Config:

```json
{
  "mcpServers": {
    "philter": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "PHILTER_BASE_URL",
        "-e", "PHILTER_VERIFY_SSL",
        "philterd/philter-mcp"
      ],
      "env": {
        "PHILTER_BASE_URL": "https://localhost:8080",
        "PHILTER_VERIFY_SSL": "false"
      }
    }
  }
}
```

Restart Claude Desktop. The Philter tools appear in the tools menu.

## Claude Code

```bash
claude mcp add philter \
  --env PHILTER_BASE_URL=https://localhost:8080 \
  --env PHILTER_VERIFY_SSL=false \
  -- docker run -i --rm -e PHILTER_BASE_URL -e PHILTER_VERIFY_SSL philterd/philter-mcp
```

`claude mcp list` should then show `philter` connected.

## Other clients

Cursor, Continue, Goose, and other MCP clients use the same shape: a command to launch,
optional arguments, and an environment block. Point the command at `docker` or at the
`philter-mcp` console script and set at least `PHILTER_BASE_URL`.

For a client that connects to an already-running server rather than launching one, run the
server with `PHILTER_MCP_TRANSPORT=streamable-http` and point the client at
`http://host:8000/mcp`. See [Docker](docker.md).

## Checking the connection

Ask the client to call the `status` tool. It returns the state of the Philter instance the
server is talking to, which confirms both that the client can launch the server and that
the server can reach Philter.

If `status` returns an error, the server started but could not reach Philter. Check
`PHILTER_BASE_URL`, and set `PHILTER_VERIFY_SSL=false` if Philter is serving its default
self-signed certificate.
