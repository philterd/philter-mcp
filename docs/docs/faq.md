# FAQ

## Do I need Philter running?

Yes. This server does no detection of its own. Every tool call is forwarded to the Philter
instance at `PHILTER_BASE_URL`. Call the `status` tool to confirm the connection.

## Why do the tools not return the text that was redacted?

By design. Returning matched values would put the PII back into the model's context, which
is what you were trying to avoid. The report gives you filter types, positions, confidence,
and replacements instead. See [Privacy](privacy.md).

For local policy debugging, `explain_redactions` accepts `include_text=true`.

## Can it redact PDFs?

Not in this version. `redact_file` handles UTF-8 text only and returns an error for binary
files. Philter itself supports PDF redaction, so call its API directly for that.

## Does redact_file modify my file?

No. It reads the file and returns redacted content. Writing the result back is the calling
application's decision.

## Why is my connection failing with a certificate error?

Philter launched from a cloud marketplace serves HTTPS with a self-signed certificate. Set
`PHILTER_VERIFY_SSL=false`, and make sure `PHILTER_BASE_URL` starts with `https://`.

## How do I make the same value redact to the same replacement across documents?

Pass the same `context` on each call. Philter keeps replacements consistent within a
context, so relationships across documents survive redaction. See
[Configuration](configuration.md#context-and-consistent-pseudonymization).

## Can several clients share one server?

Yes. Run it with `PHILTER_MCP_TRANSPORT=streamable-http` and point clients at
`http://host:8000/mcp`. See [Docker](docker.md).

## Is it on PyPI?

Not yet. Use the Docker image or install from git. See [Installation](installation.md).

## Does this guarantee no PII reaches the model?

No. Detection is probabilistic and policy-driven, and it reduces rather than eliminates
what passes through. It also only covers text passed to its tools; anything the agent read
by other means is unaffected. Validate against your own data, and pair the server with a
locally hosted model so the surrounding conversation stays inside your perimeter.
