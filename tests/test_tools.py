"""Tool-level tests: exercise the MCP tools end to end with a mocked Philter.

These complement test_philter_mcp.py (which tests the client and report builder)
by calling the actual tool functions, asserting their response shape, the
privacy guarantee (no original PII in tool output), redact_file's branches, error
handling, and main()'s transport selection.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

import philter_mcp
import philter_mcp.server as server
from philter_mcp.client import PhilterClient

# Raw PII values appear in appliedSpans.text; tool output must never contain them.
RAW_NAME = "George Washington"
RAW_SSN = "123-45-6789"

EXPLAIN_RESPONSE = {
    "filteredText": "{{{REDACTED-entity}}} was a patient and his ssn was {{{REDACTED-ssn}}}.",
    "context": "none",
    "documentId": "doc-123",
    "explanation": {
        "appliedSpans": [
            {
                "characterStart": 0,
                "characterEnd": 17,
                "filterType": "NER_ENTITY",
                "confidence": 0.91,
                "text": RAW_NAME,
                "replacement": "{{{REDACTED-entity}}}",
                "ignored": False,
            },
            {
                "characterStart": 48,
                "characterEnd": 59,
                "filterType": "SSN",
                "confidence": 1,
                "text": RAW_SSN,
                "replacement": "{{{REDACTED-ssn}}}",
                "ignored": False,
            },
        ],
        "ignoredSpans": [],
    },
}


def _ok_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/api/explain":
        return httpx.Response(200, json=EXPLAIN_RESPONSE)
    if path == "/api/policies":
        return httpx.Response(200, json=["default", "hipaa"])
    if path.startswith("/api/policies/"):
        return httpx.Response(200, json={"name": path.rsplit("/", 1)[-1], "identifiers": {}})
    if path == "/api/status":
        return httpx.Response(200, json={"status": "Healthy", "version": "3.4.1"})
    return httpx.Response(404, json={"error": "not found"})


def _error_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(503, text="unavailable")


def use_client(monkeypatch, handler):
    client = PhilterClient(base_url="http://philter.test", transport=httpx.MockTransport(handler))
    monkeypatch.setattr(server, "client", client)


def assert_no_raw_pii(result):
    blob = json.dumps(result)
    assert RAW_NAME not in blob, "tool output leaked an original name"
    assert RAW_SSN not in blob, "tool output leaked an original SSN"


# --- redact_text ---------------------------------------------------------------

def test_redact_text_returns_filtered_text_and_report(monkeypatch):
    use_client(monkeypatch, _ok_handler)
    result = asyncio.run(server.redact_text("George Washington ... 123-45-6789"))
    assert result["filtered_text"] == EXPLAIN_RESPONSE["filteredText"]
    assert result["document_id"] == "doc-123"
    assert result["redaction_count"] == 2
    assert result["redactions_by_type"] == {"NER_ENTITY": 1, "SSN": 1}


def test_redact_text_does_not_leak_pii(monkeypatch):
    use_client(monkeypatch, _ok_handler)
    result = asyncio.run(server.redact_text("George Washington ... 123-45-6789"))
    assert_no_raw_pii(result)


def test_redact_text_error_is_wrapped(monkeypatch):
    use_client(monkeypatch, _error_handler)
    result = asyncio.run(server.redact_text("hello"))
    assert "error" in result
    assert "filtered_text" not in result


# --- redact_file ---------------------------------------------------------------

def test_redact_file_happy_path(monkeypatch, tmp_path):
    use_client(monkeypatch, _ok_handler)
    f = tmp_path / "ticket.txt"
    f.write_text("George Washington ... 123-45-6789", encoding="utf-8")
    result = asyncio.run(server.redact_file(str(f)))
    assert result["filtered_text"] == EXPLAIN_RESPONSE["filteredText"]
    assert result["path"] == str(f)
    assert result["redaction_count"] == 2
    assert_no_raw_pii(result)


def test_redact_file_not_found(monkeypatch, tmp_path):
    use_client(monkeypatch, _ok_handler)
    result = asyncio.run(server.redact_file(str(tmp_path / "missing.txt")))
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_redact_file_rejects_binary(monkeypatch, tmp_path):
    use_client(monkeypatch, _ok_handler)
    f = tmp_path / "blob.bin"
    f.write_bytes(b"\xff\xfe\x00\x01not utf-8\x80")
    result = asyncio.run(server.redact_file(str(f)))
    assert "error" in result
    assert "utf-8" in result["error"].lower()


def test_redact_file_expands_home(monkeypatch, tmp_path):
    use_client(monkeypatch, _ok_handler)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows
    (tmp_path / "notes.txt").write_text("data", encoding="utf-8")
    result = asyncio.run(server.redact_file("~/notes.txt"))
    assert result.get("filtered_text") == EXPLAIN_RESPONSE["filteredText"]


# --- read-only tools -----------------------------------------------------------

def test_list_policies(monkeypatch):
    use_client(monkeypatch, _ok_handler)
    assert asyncio.run(server.list_policies()) == {"policies": ["default", "hipaa"]}


def test_list_policies_error(monkeypatch):
    use_client(monkeypatch, _error_handler)
    assert "error" in asyncio.run(server.list_policies())


def test_get_policy(monkeypatch):
    use_client(monkeypatch, _ok_handler)
    assert asyncio.run(server.get_policy("hipaa"))["name"] == "hipaa"


def test_status(monkeypatch):
    use_client(monkeypatch, _ok_handler)
    assert asyncio.run(server.status())["version"] == "3.4.1"


# --- explain_redactions --------------------------------------------------------

def test_explain_redactions_omits_text_by_default(monkeypatch):
    use_client(monkeypatch, _ok_handler)
    result = asyncio.run(server.explain_redactions("George Washington ... 123-45-6789"))
    assert result["redaction_count"] == 2
    assert result["document_id"] == "doc-123"
    assert_no_raw_pii(result)


def test_explain_redactions_can_include_text(monkeypatch):
    use_client(monkeypatch, _ok_handler)
    result = asyncio.run(server.explain_redactions("x", include_text=True))
    texts = [span.get("text") for span in result["spans"]]
    assert RAW_NAME in texts and RAW_SSN in texts


# --- main() transport selection ------------------------------------------------

def test_main_runs_selected_transport_and_binding(monkeypatch):
    captured = {}
    monkeypatch.setattr(server.mcp, "run", lambda transport="stdio": captured.update(transport=transport))
    monkeypatch.setenv("PHILTER_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("PHILTER_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("PHILTER_MCP_PORT", "9191")
    server.main()
    assert captured["transport"] == "streamable-http"
    assert server.mcp.settings.host == "0.0.0.0"
    assert server.mcp.settings.port == 9191


def test_main_defaults_to_stdio_on_invalid_transport(monkeypatch):
    captured = {}
    monkeypatch.setattr(server.mcp, "run", lambda transport="stdio": captured.update(transport=transport))
    monkeypatch.setenv("PHILTER_MCP_TRANSPORT", "bogus")
    server.main()
    assert captured["transport"] == "stdio"


def test_main_defaults_to_stdio_when_unset(monkeypatch):
    captured = {}
    monkeypatch.setattr(server.mcp, "run", lambda transport="stdio": captured.update(transport=transport))
    monkeypatch.delenv("PHILTER_MCP_TRANSPORT", raising=False)
    server.main()
    assert captured["transport"] == "stdio"


def test_health_returns_actuator_shaped_body():
    resp = asyncio.run(server.health(None))
    assert resp.status_code == 200
    assert resp.media_type == "application/json"
    body = json.loads(resp.body)
    assert body == {"status": "UP", "applicationVersion": philter_mcp.__version__}


def test_health_does_not_call_philter(monkeypatch):
    # Health is this server's own liveness, so a Philter outage must not affect it.
    def _fail():
        raise AssertionError("health must not call Philter")

    monkeypatch.setattr(server.client, "status", _fail)
    assert json.loads(asyncio.run(server.health(None)).body)["status"] == "UP"


@pytest.mark.parametrize("app_factory", ["streamable_http_app", "sse_app"])
def test_health_is_mounted_on_networked_transports(app_factory):
    app = getattr(server.mcp, app_factory)()
    assert "/health" in [getattr(route, "path", None) for route in app.routes]
