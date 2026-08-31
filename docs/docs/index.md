# Philter MCP

Philter MCP is a [Model Context Protocol](https://modelcontextprotocol.io) server that
exposes [Philter](https://www.philterd.ai/philter/)'s PII and PHI redaction as tools any
MCP-aware client can call. It lets an agent redact sensitive data from inside its own tool
loop, in Claude Desktop, Claude Code, Cursor, Continue, Goose, and other MCP clients,
without writing integration code.

It is a thin client in front of a running Philter instance. Philter does the detection and
redaction; this server makes it callable as MCP tools. Philter runs entirely within your
own environment, so the data being redacted stays inside your perimeter.

## What it is for

- A developer about to paste a production record into a chat can redact it first.
- An agent reading logs, CSV exports, or support tickets can redact inline rather than
  pulling PII into the model's context.
- "Redact PII before it reaches the model" becomes a configuration line rather than a
  project.

## What it does not do

It does not detect PII itself. Every tool call is forwarded to Philter, so you need a
Philter instance the server can reach. See [Installation](installation.md).

Detection is probabilistic and policy-driven. These tools are designed to reduce how much
sensitive data reaches a model, and you should validate their output against your own data
rather than assume everything is caught.

## Compatibility

Wraps the Philter 4.0.0 REST API (`/api/explain`, `/api/policies`, `/api/status`).
Requires Python 3.10 or later.

## Next steps

- [Install and run the server](installation.md)
- [Connect it to Claude Desktop or Claude Code](clients.md)
- [Read what each tool does](tools.md)
- [Understand what does and does not reach the model](privacy.md)
