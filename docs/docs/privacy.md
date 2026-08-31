# Privacy

This server sits between an agent and your data, so what it returns matters as much as what
it redacts.

## Matched values do not reach the model

The redaction tools never return the original sensitive values. The report contains filter
types, character positions, confidence, and the replacement token, but not the matched
text. An agent can see that an SSN was found at characters 43 to 54 and replaced, without
the SSN entering its context.

The one exception is `explain_redactions` with `include_text=true`, which returns the
matched values deliberately. It exists for debugging a policy against your own data
locally. Do not enable it in a client connected to a hosted model.

## Data stays in your infrastructure

Philter runs inside your own environment and this server is a thin client in front of it.
Text sent to a tool goes to your Philter instance and nowhere else. Neither component sends
data to Philterd.

## Pair it with a local model

Redaction happens inside the agent's tool loop, before the model sees the redacted output.
But the surrounding conversation, the prompts, the tool results, and the redacted text
itself still flow to whatever model the client is configured to use.

If that model is a third-party API, anything the agent read before calling a redaction tool
has already left your perimeter. Running the model locally keeps the whole loop inside your
control. This is the difference between redacting data on the way to a model and redacting
it after the model has already seen it.

## Files are not modified

`redact_file` reads a file and returns redacted content. It never writes to disk. Anything
that overwrites the original is a decision for the calling application, made explicitly.

## Detection is probabilistic

Philter's detection is policy-driven and probabilistic. It reduces how much sensitive data
passes through; it does not catch everything. Validate output against your own data, and
treat the redaction report as evidence for review rather than proof of completeness.

Use [`explain_redactions`](tools.md#explain_redactions) and
[Philter Scope](https://www.philterd.ai/philter-scope/) to measure a policy against
representative data before relying on it.
