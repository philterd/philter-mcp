"""philter-mcp MCP server.

Exposes Philter's redaction capabilities as MCP tools so any MCP-aware client
(Claude Desktop, Claude Code, Cursor, etc.) can redact PII/PHI from inside an
agent's tool loop.

Privacy note: the redaction tools never return the original sensitive values.
The redaction report contains filter types, character positions, confidence, and
the replacement token, but not the matched text, so nothing sensitive enters the
model's context. ``explain_redactions`` can opt in to returning matched values
for policy debugging via ``include_text=True``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import __version__
from .client import PhilterClient, PhilterError

mcp = FastMCP("philter-mcp")
client = PhilterClient()


def _report(explain_json: dict[str, Any], include_text: bool = False) -> dict[str, Any]:
    """Build a privacy-safe redaction report from a Philter explain response.

    By default the matched (original) text is omitted so it never reaches the
    model. Set ``include_text=True`` only for local policy debugging.
    """
    explanation = explain_json.get("explanation") or {}
    spans = explanation.get("appliedSpans") or []
    ignored = explanation.get("ignoredSpans") or []
    by_type: dict[str, int] = {}
    out: list[dict[str, Any]] = []
    for span in spans:
        filter_type = span.get("filterType")
        by_type[filter_type] = by_type.get(filter_type, 0) + 1
        entry: dict[str, Any] = {
            "filter_type": filter_type,
            "character_start": span.get("characterStart"),
            "character_end": span.get("characterEnd"),
            "confidence": span.get("confidence"),
            "replacement": span.get("replacement"),
            "ignored": span.get("ignored", False),
        }
        if include_text:
            entry["text"] = span.get("text")
        out.append(entry)
    return {
        "redaction_count": len(out),
        "redactions_by_type": by_type,
        "ignored_count": len(ignored),
        "spans": out,
    }


@mcp.tool(
    annotations=ToolAnnotations(
        title="Redact text",
        readOnlyHint=False,
        destructiveHint=False,
        openWorldHint=True,
    )
)
async def redact_text(
    text: str,
    policy: Optional[str] = None,
    context: Optional[str] = None,
    filename: Optional[str] = None,
) -> dict[str, Any]:
    """Redact PII and PHI from a string using Philter.

    Returns the redacted text plus a report of what was redacted (filter types,
    positions, confidence) WITHOUT the original sensitive values. Use this before
    sending text that may contain personal data to an LLM or storing it.

    Args:
        text: The text to redact.
        policy: Name of the Philter policy to apply. Falls back to PHILTER_DEFAULT_POLICY,
            then to Philter's own default policy.
        context: Logical grouping for consistent anonymization across requests.
            Use the same context across calls to anonymize consistently.
        filename: Optional document name recorded by Philter for traceability.
    """
    try:
        data = await client.explain(text, policy=policy, context=context, filename=filename)
    except PhilterError as exc:
        return {"error": str(exc)}
    return {
        "filtered_text": data.get("filteredText"),
        "document_id": data.get("documentId"),
        "context": data.get("context"),
        **_report(data),
    }


@mcp.tool(
    annotations=ToolAnnotations(
        title="Redact file",
        readOnlyHint=False,
        destructiveHint=False,
        openWorldHint=True,
    )
)
async def redact_file(
    path: str,
    policy: Optional[str] = None,
    context: Optional[str] = None,
) -> dict[str, Any]:
    """Redact PII and PHI from a UTF-8 text file (logs, CSV exports, tickets, transcripts).

    Reads the file locally, sends its contents to Philter, and returns the
    redacted content plus a redaction report (no original sensitive values). The
    file on disk is not modified. PDF and other binary files are not supported in
    this version. The file's name is passed to Philter as the document filename.

    Args:
        path: Path to a UTF-8 text file to redact.
        policy: Name of the Philter policy to apply.
        context: Logical grouping for consistent anonymization across requests.
            Use the same context across calls to anonymize consistently.
    """
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        return {"error": f"File not found: {file_path}"}
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "error": (
                f"{file_path} is not a UTF-8 text file. PDF and binary redaction is "
                "not supported in this version."
            )
        }
    try:
        data = await client.explain(text, policy=policy, context=context, filename=file_path.name)
    except PhilterError as exc:
        return {"error": str(exc)}
    return {
        "path": str(file_path),
        "filtered_text": data.get("filteredText"),
        "document_id": data.get("documentId"),
        "context": data.get("context"),
        **_report(data),
    }


@mcp.tool(
    annotations=ToolAnnotations(title="List policies", readOnlyHint=True, openWorldHint=True)
)
async def list_policies() -> Any:
    """List the names of the redaction policies available on the connected Philter instance."""
    try:
        return {"policies": await client.policies()}
    except PhilterError as exc:
        return {"error": str(exc)}


@mcp.tool(
    annotations=ToolAnnotations(title="Get policy", readOnlyHint=True, openWorldHint=True)
)
async def get_policy(name: str) -> Any:
    """Return the JSON definition of a single Philter policy.

    Args:
        name: The policy name (as returned by list_policies).
    """
    try:
        return await client.policy(name)
    except PhilterError as exc:
        return {"error": str(exc)}


@mcp.tool(
    annotations=ToolAnnotations(title="Explain redactions", readOnlyHint=True, openWorldHint=True)
)
async def explain_redactions(
    text: str,
    policy: Optional[str] = None,
    include_text: bool = False,
) -> dict[str, Any]:
    """Dry-run for debugging a policy: show what Philter would redact and why.

    Returns each detection's filter type, character position, confidence, and
    replacement token. The original matched values are omitted by default so they
    do not enter the model context.

    Args:
        text: The text to analyze.
        policy: Name of the Philter policy to apply.
        include_text: When true, also return the matched sensitive values. This
            exposes the original PII/PHI to the model, so use only for local debugging.
    """
    try:
        data = await client.explain(text, policy=policy)
    except PhilterError as exc:
        return {"error": str(exc)}
    report = _report(data, include_text=include_text)
    report["context"] = data.get("context")
    report["document_id"] = data.get("documentId")
    return report


@mcp.tool(
    annotations=ToolAnnotations(title="Philter status", readOnlyHint=True, openWorldHint=True)
)
async def status() -> Any:
    """Return the status and health of the connected Philter instance."""
    try:
        return await client.status()
    except PhilterError as exc:
        return {"error": str(exc)}


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """Health of this MCP server, shaped like Spring Boot Actuator's /health.

    Served only by the networked transports (streamable-http and sse); stdio has
    no listener. The route is unauthenticated, as health checks are meant to be.

    It reports only this server's own state and does not probe Philter, so a
    Philter outage cannot make an orchestrator restart a healthy MCP server. Use
    the ``status`` tool for the backend's health.
    """
    return JSONResponse({"status": "UP", "applicationVersion": __version__})


def main() -> None:
    """Console-script entry point.

    Transport is selected by ``PHILTER_MCP_TRANSPORT`` (default ``stdio`` for
    desktop and IDE clients). Set it to ``streamable-http`` or ``sse`` for hosted or
    containerized use; the bind address and port then come from ``FASTMCP_HOST`` and
    ``FASTMCP_PORT``.
    """
    transport = os.environ.get("PHILTER_MCP_TRANSPORT", "stdio").strip().lower()
    if transport not in ("stdio", "sse", "streamable-http"):
        transport = "stdio"
    if transport != "stdio":
        # Bind address/port for the networked transports. Containers need
        # 0.0.0.0 to be reachable from outside; default to localhost otherwise.
        mcp.settings.host = os.environ.get("PHILTER_MCP_HOST", "127.0.0.1")
        mcp.settings.port = int(os.environ.get("PHILTER_MCP_PORT", "8000"))
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
