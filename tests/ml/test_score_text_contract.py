"""Contract tests for `ml.predict.score_text` — Implementation Plan task 1.13.

These tests must pass UNCHANGED when the Week-8 real model replaces the Week-1
stub. If a change to the real implementation requires editing this file, the
frozen contract (ADR-008) has been broken and the change needs both team leads'
sign-off plus matching PRD/TRD/DOC-007 updates.
"""

from __future__ import annotations

import pytest

from ml.predict import score_text
from ml.schema import SCHEMA_VERSION, ScoreResult

SAMPLE = "Ministry officials issued a statement about the border incident today."


def test_returns_schema_valid_dict():
    """PRD §9.1 — output validates against the frozen schema."""
    result = score_text(SAMPLE)
    ScoreResult.model_validate(result)  # raises if the shape drifted


def test_every_key_always_present():
    """No optional keys. Backend indexes these without defensive checks."""
    result = score_text(SAMPLE)
    for key in (
        "schema_version",
        "model_version",
        "language",
        "truncated",
        "sentiment",
        "hostility",
        "disinfo",
        "stance",
        "entities",
        "topics",
        "meta",
    ):
        assert key in result, f"missing required key: {key}"


def test_schema_version_matches_module_constant():
    assert score_text(SAMPLE)["schema_version"] == SCHEMA_VERSION


def test_model_version_is_non_empty():
    """FR-3.8 — every inference is attributable to an exact model version."""
    assert score_text(SAMPLE)["model_version"].strip()


def test_deterministic_for_same_input():
    """TRD §5.5 — same input + same model_version => same output."""
    assert score_text(SAMPLE) == score_text(SAMPLE)


def test_varies_across_inputs():
    """A stub that returned constants would hide integration bugs downstream."""
    a = score_text("Peaceful negotiations concluded successfully this morning.")
    b = score_text("Armed groups exchanged threats across the disputed border.")
    assert a["sentiment"]["scores"] != b["sentiment"]["scores"]


@pytest.mark.parametrize("bad", ["", "   ", "\n\t  "])
def test_empty_input_raises_value_error(bad):
    """TRD §5.5 — raises, never returns a partial dict."""
    with pytest.raises(ValueError):
        score_text(bad)


@pytest.mark.parametrize("task", ["sentiment", "hostility", "disinfo", "stance"])
def test_confidence_within_bounds(task):
    block = score_text(SAMPLE)[task]
    assert 0.0 <= block["confidence"] <= 1.0


@pytest.mark.parametrize("task", ["sentiment", "hostility", "disinfo"])
def test_scores_sum_to_one(task):
    """FR-3.9 — full per-class distribution, not just the arg-max."""
    scores = score_text(SAMPLE)[task]["scores"]
    assert scores, f"{task} returned an empty distribution"
    assert sum(scores.values()) == pytest.approx(1.0, abs=0.005)


@pytest.mark.parametrize("task", ["sentiment", "hostility", "disinfo"])
def test_label_is_argmax_of_scores(task):
    block = score_text(SAMPLE)[task]
    assert block["label"] == max(block["scores"], key=lambda k: block["scores"][k])
    assert block["confidence"] == pytest.approx(block["scores"][block["label"]])


def test_descoped_task_uses_not_applicable_shape():
    """PRD §9.1 — a descoped task returns not_applicable / 0.0, never a missing key.

    Stance is [PROPOSED] (FR-3.4, TBD-4). Whether it survives Week 7 or not, the
    key exists and this shape is what the backend and UI must handle.
    """
    stance = score_text(SAMPLE)["stance"]
    if stance["label"] == "not_applicable":
        assert stance["confidence"] == 0.0
        assert stance["scores"] == {}


def test_truncation_flag_reports_honestly():
    """FR-2.10 — truncation is recorded, not silent."""
    assert score_text(SAMPLE)["truncated"] is False
    assert score_text("word " * 5000)["truncated"] is True


def test_language_passthrough_and_default():
    assert score_text(SAMPLE, lang="ar")["language"]["code"] == "ar"
    assert score_text(SAMPLE)["language"]["code"] == "en"


def test_meta_reports_input_size():
    meta = score_text(SAMPLE)["meta"]
    assert meta["chars_in"] == len(SAMPLE)
    assert meta["inference_ms"] >= 0


def test_no_extra_keys_accepted():
    """Schema is reject-by-default (SEC-10) — an unknown field is an error."""
    from pydantic import ValidationError

    payload = score_text(SAMPLE)
    payload["unexpected_field"] = "should be rejected"
    with pytest.raises(ValidationError):
        ScoreResult.model_validate(payload)
