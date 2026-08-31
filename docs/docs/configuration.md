# Configuration

All configuration is through environment variables. There is no config file.

## Philter connection

| Variable | Default | Description |
|----------|---------|-------------|
| `PHILTER_BASE_URL` | `http://localhost:8080` | Base URL of your Philter instance. |
| `PHILTER_API_KEY` | unset | Sent verbatim as the `Authorization` header value. |
| `PHILTER_DEFAULT_POLICY` | unset | Policy used when a tool call omits `policy`. |
| `PHILTER_VERIFY_SSL` | `true` | TLS certificate verification. |

`PHILTER_API_KEY` is sent exactly as given, with no scheme added. Philter 4.0.0 compares
the `Authorization` header against its configured key, so include a prefix such as
`Bearer ` yourself only if your deployment expects one.

`PHILTER_VERIFY_SSL` treats `false`, `0`, `no`, and `off` as false. Anything else, including
an empty value, is true.

Philter launched from a cloud marketplace serves HTTPS with a self-signed certificate. Set
`PHILTER_BASE_URL=https://...` and `PHILTER_VERIFY_SSL=false` in that case. Turning
verification off means the connection is encrypted but the server's identity is not
checked, so keep it to networks you control and prefer a trusted certificate in production.

## Server transport

| Variable | Default | Description |
|----------|---------|-------------|
| `PHILTER_MCP_TRANSPORT` | `stdio` | `stdio`, `streamable-http`, or `sse`. |
| `PHILTER_MCP_HOST` | `127.0.0.1` | Bind address. Networked transports only. |
| `PHILTER_MCP_PORT` | `8000` | Bind port. Networked transports only. |

An unrecognized transport value falls back to `stdio` rather than failing. Host and port are
ignored under `stdio`, which has no listener. In a container set
`PHILTER_MCP_HOST=0.0.0.0` so the server is reachable from outside it.

## Policy resolution

A tool call's `policy` argument wins. If omitted, `PHILTER_DEFAULT_POLICY` is used. If that
is unset too, Philter applies its own default policy.

Setting `PHILTER_DEFAULT_POLICY` is worth doing when a client should always use one policy,
because it removes the chance of the model choosing or omitting a policy name.

## Context and consistent pseudonymization

The `context` argument is accepted by `redact_text` and `redact_file`. It groups documents
that belong together. Philter uses it to keep
replacements consistent, so the same source value maps to the same replacement everywhere
within that context. That preserves referential integrity across a set of documents, which
matters when relationships in the data need to survive redaction.

Pass the same `context` across related calls. Pass different values when documents should
not share replacements.
