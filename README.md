# philter-mcp

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that exposes
[Philter](https://www.philterd.ai/philter/)'s PII and PHI redaction as tools any
MCP-aware client can call. Redact sensitive data from inside an agent's tool loop in
Claude Desktop, Claude Code, Cursor, Continue, Goose, and others, without writing
integration code.

**Compatible with Philter 4.0.0.** It wraps the Philter 4.0.0 REST API (`/api/explain`,
`/api/policies`, `/api/status`); you point it at a running Philter instance.

📖 **[Read the documentation](https://philterd.github.io/philter-mcp/)** for installation,
client setup, the full tool reference, and configuration.

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
> model sees the data, but the surrounding conversation (prompts, tool results, and the
> redacted output itself) still flows to whatever model the client is configured to use.
> Sending that to a third-party AI service risks leaking PII that was never meant to
> leave your perimeter, so run the model locally to keep sensitive data in your control.

Detection is probabilistic and policy-driven. It reduces how much sensitive data reaches a
model rather than eliminating it, so validate output against your own data.

## Tools

| Tool | Description | Read-only |
|------|-------------|-----------|
| `redact_text` | Redact PII/PHI from a string; returns redacted text plus a report. | no |
| `redact_file` | Redact PII/PHI from a UTF-8 text file; returns redacted content plus a report. | no |
| `explain_redactions` | Dry-run that shows what would be redacted and why (policy debugging). | yes |
| `list_policies` | List the policies available on the connected Philter instance. | yes |
| `get_policy` | Return a policy's JSON definition. | yes |
| `status` | Return the Philter instance status and health. | yes |

Full arguments and return shapes: [Tools](https://philterd.github.io/philter-mcp/tools/).

## Install

Requires a running Philter 4.0.0 instance reachable from where this server runs, and
Python 3.10 or newer if installing from source.

> **Not yet published to PyPI.** Until it is, install from source or use the Docker image:
>
> ```bash
> pip install git+https://github.com/philterd/philter-mcp
> ```

The published image runs the stdio transport by default, so an MCP client can launch it
directly:

```bash
docker run -i --rm \
  -e PHILTER_BASE_URL=https://host.docker.internal:8080 \
  -e PHILTER_VERIFY_SSL=false \
  philterd/philter-mcp
```

See [Installation](https://philterd.github.io/philter-mcp/installation/) and
[Docker](https://philterd.github.io/philter-mcp/docker/), including running it as a
networked service.

## Configure a client

Claude Code, using the image:

```bash
claude mcp add philter \
  --env PHILTER_BASE_URL=https://localhost:8080 \
  --env PHILTER_VERIFY_SSL=false \
  -- docker run -i --rm -e PHILTER_BASE_URL -e PHILTER_VERIFY_SSL philterd/philter-mcp
```

Claude Desktop, Cursor, and others are covered in
[MCP Clients](https://philterd.github.io/philter-mcp/clients/).

Configuration is entirely through environment variables, chiefly `PHILTER_BASE_URL`,
`PHILTER_API_KEY`, `PHILTER_DEFAULT_POLICY`, and `PHILTER_VERIFY_SSL`. See
[Configuration](https://philterd.github.io/philter-mcp/configuration/).

## Development

```bash
git clone https://github.com/philterd/philter-mcp
cd philter-mcp
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The tests use a mocked HTTP transport, so no running Philter instance is required.

Documentation lives in `docs/` and is published to GitHub Pages on every push to `main`.

## Related

- [Philter](https://www.philterd.ai/philter/): the self-hosted redaction API this wraps.
- [Philter AI Proxy](https://www.philterd.ai/philter-ai-proxy/): server-side PII guardrails
  for production LLM traffic. This MCP server is the client-side counterpart for agent tool loops.

## License

Apache License 2.0. See [LICENSE](LICENSE).
