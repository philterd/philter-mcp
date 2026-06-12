"""Unit tests for the Philter client and the redaction-report builder.

Uses httpx.MockTransport so no running Philter instance is required.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from philter_mcp.client import PhilterClient, PhilterError
from philter_mcp.server import _report

# A representative /api/explain response (from the Philter API docs). The
# appliedSpans deliberately include the original `text` values so we can assert
# they are stripped from tool output.
EXPLAIN_RESPONSE = {
    "filteredText": "{{{REDACTED-entity}}} was a patient and his ssn was {{{REDACTED-ssn}}}.",
    "context": "none",
    "documentId": "7a906866-4fc9-44d6-9bc3-22728b93a602",
    "explanation": {
        "appliedSpans": [
            {
                "id": "c78fb69c",
                "characterStart": 0,
                "characterEnd": 17,
                "filterType": "NER_ENTITY",
                "confidence": 0.91,
                "text": "George Washington",
                "replacement": "{{{REDACTED-entity}}}",
                "ignored": False,
            },
            {
                "id": "f4556f62",
                "characterStart": 48,
                "characterEnd": 59,
                "filterType": "SSN",
                "confidence": 1,
                "text": "123-45-6789",
                "replacement": "{{{REDACTED-ssn}}}",
                "ignored": False,
            },
        ],
        "ignoredSpans": [],
    },
}


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/api/explain":
        return httpx.Response(200, json=EXPLAIN_RESPONSE)
    if path == "/api/policies":
        return httpx.Response(200, json=["default", "just-phone-numbers"])
    if path == "/api/policies/just-phone-numbers":
        return httpx.Response(200, json={"name": "just-phone-numbers", "identifiers": {}})
    if path == "/api/status":
        return httpx.Response(200, json={"status": "Healthy"})
    return httpx.Response(404, json={"error": "not found"})


def make_client(**kwargs) -> PhilterClient:
    return PhilterClient(
        base_url="http://philter.test",
        transport=httpx.MockTransport(_handler),
        **kwargs,
    )


def test_explain_returns_filtered_text():
    data = asyncio.run(make_client().explain("George Washington ... 123-45-6789"))
    assert data["filteredText"].startswith("{{{REDACTED")
    assert data["documentId"]


def test_explain_passes_policy_context_filename():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(200, json=EXPLAIN_RESPONSE)

    client = PhilterClient(base_url="http://philter.test", transport=httpx.MockTransport(handler))
    asyncio.run(client.explain("hello", policy="hipaa", context="ctx1", filename="notes.txt"))
    # Philter 4.0.0 /api/explain takes c, p, and filename (no document-id input).
    assert captured["params"] == {"p": "hipaa", "c": "ctx1", "filename": "notes.txt"}
    assert captured["body"] == "hello"


def test_default_policy_applied():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json=EXPLAIN_RESPONSE)

    client = PhilterClient(
        base_url="http://philter.test",
        default_policy="my-default",
        transport=httpx.MockTransport(handler),
    )
    asyncio.run(client.explain("hello"))
    assert captured["params"]["p"] == "my-default"


def test_api_key_sets_authorization_header():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json=["default"])

    client = PhilterClient(
        base_url="http://philter.test",
        api_key="secret-key",
        transport=httpx.MockTransport(handler),
    )
    asyncio.run(client.policies())
    # Philter 4.0.0 receives the key verbatim as the Authorization value; the
    # client does not prepend a "Bearer " scheme (the caller adds one if needed).
    assert captured["auth"] == "secret-key"


def test_policies_and_policy_and_status():
    client = make_client()
    assert asyncio.run(client.policies()) == ["default", "just-phone-numbers"]
    assert asyncio.run(client.policy("just-phone-numbers"))["name"] == "just-phone-numbers"
    assert asyncio.run(client.status()) == {"status": "Healthy"}


def test_http_error_raises_philter_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = PhilterClient(base_url="http://philter.test", transport=httpx.MockTransport(handler))
    with pytest.raises(PhilterError):
        asyncio.run(client.explain("hello"))


def test_report_strips_original_text_by_default():
    report = _report(EXPLAIN_RESPONSE)
    assert report["redaction_count"] == 2
    assert report["redactions_by_type"] == {"NER_ENTITY": 1, "SSN": 1}
    assert report["ignored_count"] == 0
    for span in report["spans"]:
        assert "text" not in span, "original PII value must not be returned"
        assert span["filter_type"]
        assert span["replacement"]


def test_report_can_include_text_for_debugging():
    report = _report(EXPLAIN_RESPONSE, include_text=True)
    assert report["spans"][0]["text"] == "George Washington"


def test_status_falls_back_to_text():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="HEALTHY")

    client = PhilterClient(base_url="http://philter.test", transport=httpx.MockTransport(handler))
    assert asyncio.run(client.status()) == {"status": "HEALTHY"}
