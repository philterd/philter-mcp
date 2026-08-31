# Tools

Six tools. The four read-only ones are marked as such so clients can allow them without
prompting.

| Tool | Read-only | Purpose |
|------|-----------|---------|
| `redact_text` | no | Redact PII and PHI from a string. |
| `redact_file` | no | Redact a UTF-8 text file. |
| `explain_redactions` | yes | Dry run showing what a policy would redact. |
| `list_policies` | yes | Policy names available on the Philter instance. |
| `get_policy` | yes | A policy's JSON definition. |
| `status` | yes | Health of the connected Philter instance. |

Every tool returns `{"error": "..."}` rather than raising when Philter cannot be reached.

## redact_text

Redacts a string and returns the redacted text plus a report of what changed.

| Argument | Required | Description |
|----------|----------|-------------|
| `text` | yes | The text to redact. |
| `policy` | no | Policy name. Falls back to `PHILTER_DEFAULT_POLICY`, then Philter's own default. |
| `context` | no | Groups related documents so the same value maps to the same replacement. |
| `filename` | no | Document name recorded by Philter for traceability. |

Returns `filtered_text`, `document_id`, `context`, and the redaction report described
below. The original matched values are not included.

## redact_file

Reads a UTF-8 text file from disk, redacts its contents, and returns the result. Useful for
logs, CSV exports, tickets, and transcripts.

| Argument | Required | Description |
|----------|----------|-------------|
| `path` | yes | Path to a UTF-8 text file. |
| `policy` | no | Policy name. |
| `context` | no | Groups related documents for consistent replacement. |

**The file on disk is not modified.** The redacted content is returned to the caller.

PDF and other binary formats are not supported in this version; a non-UTF-8 file returns an
error. The file's name is passed to Philter as the document filename.

## explain_redactions

A dry run for policy debugging. Shows what would be redacted and why.

| Argument | Required | Description |
|----------|----------|-------------|
| `text` | yes | The text to analyze. |
| `policy` | no | Policy name. |
| `include_text` | no | Return the matched sensitive values as well. Default false. |

`include_text=true` puts the original PII and PHI into the model's context. Use it only
when debugging a policy locally against data you are willing to expose. See
[Privacy](privacy.md).

## list_policies

No arguments. Returns `{"policies": [...]}`, the policy names available on the connected
Philter instance.

## get_policy

| Argument | Required | Description |
|----------|----------|-------------|
| `name` | yes | Policy name, as returned by `list_policies`. |

Returns the policy's JSON definition.

## status

No arguments. Returns the status and health of the connected Philter instance. This is the
quickest way to confirm the server can reach Philter.

## The redaction report

`redact_text`, `redact_file`, and `explain_redactions` all return the same report shape:

| Field | Description |
|-------|-------------|
| `redaction_count` | Number of spans redacted. |
| `redactions_by_type` | Count per filter type, for example `{"NER_ENTITY": 1, "SSN": 1}`. |
| `ignored_count` | Spans the policy matched but deliberately ignored. |
| `spans` | One entry per redaction. |

Each span carries `filter_type`, `character_start`, `character_end`, `confidence`,
`replacement`, and `ignored`. It carries `text` only when `include_text=true` was passed to
`explain_redactions`.
