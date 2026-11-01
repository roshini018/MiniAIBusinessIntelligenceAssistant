import json
import pytest
from google.genai import errors
from app import llm_classifier


class MockResponse:
    def __init__(self, text):
        self.text = text


def test_gemini_server_error_retries_and_falls_back(monkeypatch):
    """5xx ServerError must retry and eventually fall back to keyword classifier."""
    attempts = 0

    def fail_with_server_error(model, question, default_year):
        nonlocal attempts
        attempts += 1
        raise errors.ServerError(500, {"error": {"message": "Internal server error"}})

    monkeypatch.setattr(llm_classifier, "_request", fail_with_server_error)
    # Monkeypatch time.sleep to avoid slow tests
    monkeypatch.setattr(llm_classifier.time, "sleep", lambda s: None)

    res = llm_classifier.classify_question("What is our total revenue?", 2026)
    assert res["source"] == "keywords"
    assert res["intent"] == "total_revenue"
    # 2 models in candidates * 2 attempts each = 4 attempts
    assert attempts >= 2


def test_gemini_client_error_fails_fast_without_retry(monkeypatch):
    """4xx ClientError must fail fast without retry loops and fall back immediately."""
    attempts = 0

    def fail_with_client_error(model, question, default_year):
        nonlocal attempts
        attempts += 1
        raise errors.ClientError(400, {"error": {"message": "Invalid API key"}})

    monkeypatch.setattr(llm_classifier, "_request", fail_with_client_error)

    res = llm_classifier.classify_question("What is the highest revenue?", 2026)
    assert res["source"] == "keywords"
    assert res["intent"] == "monthly_trend"
    # Breaks out of attempt loop on client error
    assert attempts == 2  # 1 per candidate model


def test_gemini_timeout_falls_back(monkeypatch):
    """Timeout during Gemini call must fall back cleanly to keywords."""
    def fail_timeout(model, question, default_year):
        raise TimeoutError("Gemini request timed out")

    monkeypatch.setattr(llm_classifier, "_request", fail_timeout)
    res = llm_classifier.classify_question("Rank products by revenue", 2026)
    assert res["source"] == "keywords"
    assert res["intent"] == "top_product"
    assert res["params"]["target"] == "ranking"


def test_gemini_connection_error_falls_back(monkeypatch):
    """Connection/network failure must fall back cleanly to keywords."""
    def fail_conn(model, question, default_year):
        raise ConnectionError("Failed to establish SSL connection")

    monkeypatch.setattr(llm_classifier, "_request", fail_conn)
    res = llm_classifier.classify_question("How much did we earn?", 2026)
    assert res["source"] == "keywords"
    assert res["intent"] == "total_revenue"


def test_gemini_malformed_json_falls_back(monkeypatch):
    """When Gemini returns gibberish or unparseable JSON, falls back to keywords."""
    monkeypatch.setattr(
        llm_classifier,
        "_request",
        lambda m, q, y: MockResponse("{broken json: [1, 2,"),
    )
    res = llm_classifier.classify_question("Which product earned the most revenue?", 2026)
    assert res["source"] == "keywords"
    assert res["intent"] == "top_product"


def test_gemini_missing_required_fields_falls_back(monkeypatch):
    """When Gemini JSON misses the required 'intent' field, validation fails and falls back."""
    monkeypatch.setattr(
        llm_classifier,
        "_request",
        lambda m, q, y: MockResponse(json.dumps({"months": ["2026-01"]})),
    )
    res = llm_classifier.classify_question("What was the revenue in January?", 2026)
    assert res["source"] == "keywords"
    assert res["intent"] == "monthly_trend"


def test_gemini_unknown_intent_value_falls_back(monkeypatch):
    """When Gemini returns an unallowed intent like 'stock_forecast', falls back."""
    monkeypatch.setattr(
        llm_classifier,
        "_request",
        lambda m, q, y: MockResponse(json.dumps({"intent": "stock_forecast", "months": []})),
    )
    res = llm_classifier.classify_question("What is our total sales?", 2026)
    assert res["source"] == "keywords"
    assert res["intent"] == "total_revenue"


def test_gemini_invalid_comparison_months_falls_back(monkeypatch):
    """When month_comparison from Gemini has only 1 month or invalid dates, falls back to keywords."""
    # 1 month only
    monkeypatch.setattr(
        llm_classifier,
        "_request",
        lambda m, q, y: MockResponse(json.dumps({"intent": "month_comparison", "months": ["2026-01"]})),
    )
    res1 = llm_classifier.classify_question("Compare January and February 2026", 2026)
    assert res1["source"] == "keywords"
    assert res1["intent"] == "month_comparison"
    assert len(res1["params"]["months"]) == 2

    # Invalid month syntax '2026-99'
    monkeypatch.setattr(
        llm_classifier,
        "_request",
        lambda m, q, y: MockResponse(json.dumps({"intent": "month_comparison", "months": ["2026-01", "2026-99"]})),
    )
    res2 = llm_classifier.classify_question("Compare January and February 2026", 2026)
    assert res2["source"] == "keywords"
    assert res2["params"]["months"] == ["2026-01", "2026-02"]


def test_gemini_successful_parameter_mapping(monkeypatch):
    """When Gemini returns valid classifications, parameters are cleanly mapped."""
    # Product target
    monkeypatch.setattr(
        llm_classifier,
        "_request",
        lambda m, q, y: MockResponse(json.dumps({"intent": "top_product", "target": "lowest", "months": []})),
    )
    r1 = llm_classifier.classify_question("Which product generated least revenue?", 2026)
    assert r1["source"] == "gemini"
    assert r1["params"]["target"] == "lowest"

    # Specific region lookup
    monkeypatch.setattr(
        llm_classifier,
        "_request",
        lambda m, q, y: MockResponse(json.dumps({"intent": "top_region", "target": "specific", "region": "South", "months": []})),
    )
    r2 = llm_classifier.classify_question("How much came from South?", 2026)
    assert r2["source"] == "gemini"
    assert r2["params"]["region"] == "South"

    # Ambiguous clarification
    monkeypatch.setattr(
        llm_classifier,
        "_request",
        lambda m, q, y: MockResponse(
            json.dumps({
                "intent": "ambiguous",
                "clarification_message": "Did you mean month or region?",
                "months": [],
            })
        ),
    )
    r3 = llm_classifier.classify_question("Which was highest?", 2026)
    assert r3["source"] == "gemini"
    assert r3["intent"] == "ambiguous"
    assert r3["params"]["message"] == "Did you mean month or region?"
