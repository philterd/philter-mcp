# philter-mcp

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that exposes
[Philter](https://www.philterd.ai/philter/)'s PII and PHI redaction as tools any
MCP-aware client can call. Redact sensitive data from inside an agent's tool loop in
Claude Desktop, Claude Code, Cursor, Continue, Goose, and others, without writing
integration code.

**Compatible with Philter 3.x.** It wraps the Philter 3.x REST API (`/api/explain`,
`/api/policies`, `/api/status`); you point it at a running Philter instance.

## Why

- A developer about to paste a production record into a chat can redact it first.
- An agent reading logs, CSV exports, or support tickets can redact inline instead of
  leaking PII into the model's context.
- "I want my agent to redact PII before sending it to the LLM" has a one-config-line answer.

Philter runs entirely within your own environment, so your data never leaves your
perimeter. This server is a thin client in front of it.

## Privacy by design

The redaction tools never return the original sensitive values. The redaction report
contains filter types, character positions, confidence, and the replacement token, but
not the matched text, so nothing sensitive enters the model's context.
`explain_redactions` can opt in to returning matched values for local policy debugging
with `include_text=true`.

> **Use with local LLMs.** Because this server redacts text inside the agent's tool
> loop, it should be paired with a locally hosted LLM. Redaction happens before the
> model sees the data, but the surrounding conversation — prompts, tool results, and the
> redacted output itself — still flows to whatever model the client is configured to use.
> Sending that to a third-party AI service risks leaking PII that was never meant to
> leave your perimeter, so run the model locally to keep sensitive data in your control.

## Tools

| Tool | Description | Read-only |
|------|-------------|-----------|
| `redact_text` | Redact PII/PHI from a string; returns redacted text plus a report. | no |
| `redact_file` | Redact PII/PHI from a UTF-8 text file; returns redacted content plus a report. | no |
| `explain_redactions` | Dry-run that shows what would be redacted and why (policy debugging). | yes |
| `list_policies` | List the policies available on the connected Philter instance. | yes |
| `get_policy` | Return a policy's JSON definition. | yes |
| `status` | Return the Philter instance status and health. | yes |

`redact_text` and `redact_file` accept optional `policy`, `context`, and `document_id`
arguments. `context` and `document_id` are passed through to Philter so its consistent
anonymization and format-preserving behavior hold across requests.

## Requirements

- A running Philter 3.x instance reachable from where this server runs.
- Python 3.10 or newer (only if installing from source; `uvx`/`pipx` manage this for you).

## Install and run

The server speaks MCP over stdio and is meant to be launched by your MCP client. The
easiest way is with [`uv`](https://docs.astral.sh/uv/):

```bash
uvx philter-mcp
```

or with pipx:

```bash
pipx run philter-mcp
```

## Configuration

All configuration is via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PHILTER_BASE_URL` | `http://localhost:8080` | Base URL of your Philter instance. |
| `PHILTER_API_KEY` | (unset) | Sent as `Authorization: Bearer <key>` when set. |
| `PHILTER_DEFAULT_POLICY` | (unset) | Policy name used when a call omits `policy`. |
| `PHILTER_VERIFY_SSL` | `true` | Set to `false` for Philter's default self-signed certificate. |

> Philter launched from a cloud marketplace serves HTTPS with a self-signed certificate.
> In that case set `PHILTER_BASE_URL=https://...` and `PHILTER_VERIFY_SSL=false`.

### Claude Desktop

Add to `claude_desktop_config.json` (Settings, Developer, Edit Config):

```json
{
  "mcpServers": {
    "philter": {
      "command": "uvx",
      "args": ["philter-mcp"],
      "env": {
        "PHILTER_BASE_URL": "https://localhost:8080",
        "PHILTER_VERIFY_SSL": "false"
      }
    }
  }
}
```

Restart Claude Desktop. The Philter tools appear in the tools menu.

### Claude Code

```bash
claude mcp add philter \
  --env PHILTER_BASE_URL=https://localhost:8080 \
  --env PHILTER_VERIFY_SSL=false \
  -- uvx philter-mcp
```

Then `claude mcp list` should show `philter` connected.

## Docker

A container image is provided. By default it runs the stdio transport, so an MCP
client can launch it directly:

```bash
docker run -i --rm \
  -e PHILTER_BASE_URL=https://host.docker.internal:8080 \
  -e PHILTER_VERIFY_SSL=false \
  philterd/philter-mcp
```

Claude Desktop config using the image:

```json
{
  "mcpServers": {
    "philter": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "PHILTER_BASE_URL=https://host.docker.internal:8080",
        "-e", "PHILTER_VERIFY_SSL=false",
        "philterd/philter-mcp"
      ]
    }
  }
}
```

To run it as a long-running networked MCP service instead (streamable-http), use the
included compose file:

```bash
docker compose up --build
```

That serves the MCP endpoint at `http://localhost:8000/mcp`, talking to the Philter
instance at `PHILTER_BASE_URL` (`host.docker.internal:8080` by default). Override
`PHILTER_BASE_URL`, `PHILTER_API_KEY`, `PHILTER_DEFAULT_POLICY`, `PHILTER_VERIFY_SSL`,
and `PHILTER_MCP_PORT` as needed.

Build the image yourself with `docker build -t philterd/philter-mcp .`.

## Example prompts

- "Redact the PII from `./tickets.csv` and show me the result."
- "Before I share this log, redact any personal data: `<paste>`"
- "Which redaction policies are available on my Philter instance?"
- "Using the `hipaa` policy, explain what would be redacted in this note and why."

## Development

```bash
git clone https://github.com/philterd/philter-mcp
cd philter-mcp
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The tests use a mocked HTTP transport, so no running Philter instance is required.

## Related

- [Philter](https://www.philterd.ai/philter/): the self-hosted redaction API this wraps.
- [Philter AI Proxy](https://www.philterd.ai/philter-ai-proxy/): server-side PII guardrails
  for production LLM traffic. This MCP server is the client-side counterpart for agent tool loops.

## License

Apache License 2.0. See [LICENSE](LICENSE).
