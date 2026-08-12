"""POLIS ML inference entry point.

    score_text(text, lang=None) -> dict

This is the ONLY symbol the backend imports from `ml`. The backend never imports
torch, transformers, or any training code. See ADR-008.

WEEK 1 STATUS: this is a STUB. It returns deterministic pseudo-scores derived
from a hash of the input, so that Teams C and D can build the backend and
frontend against a stable, schema-valid shape during the ~7 weeks before a real
model exists (Implementation Plan task 1.12, PRD risk R-9).

Replacing the stub in Week 8 changes the BODY of `score_text` only. Its
signature, its return schema, and `tests/ml/test_score_text_contract.py` stay
exactly as they are — that is the whole point of the frozen contract.
"""

from __future__ import annotations

import hashlib
import time

from ml.schema import SCHEMA_VERSION, ScoreResult

# The stub advertises itself as a stub. Any nlp_results row carrying this
# version tag was NOT produced by a trained model, and the UI/reporting must
# never present it as though it were.
STUB_MODEL_VERSION = "polis-stub-v0.0.1"

# Mirrors MODEL_MAX_TOKENS in .env.example. The stub has no tokenizer, so it
# approximates the 512-token limit by character count purely to exercise the
# `truncated` flag end to end. The real implementation counts actual tokens.
_STUB_TRUNCATE_CHARS = 4000


def _pseudo_scores(digest: int, shift: int, labels: tuple[str, ...]) -> dict[str, float]:
    """Deterministic pseudo-distribution over `labels`, summing to 1.0.

    Deterministic so tests are stable and the same fixture always renders the
    same way; varied across inputs so the UI is not a wall of identical numbers.
    """
    raw = [((digest >> (shift + 7 * i)) % 1000) + 1 for i in range(len(labels))]
    total = sum(raw)
    scores = {label: round(value / total, 3) for label, value in zip(labels, raw, strict=True)}
    # Rounding can leave the sum off by a thousandth; absorb it into the largest
    # class so the distribution still sums to exactly 1.0.
    drift = round(1.0 - sum(scores.values()), 3)
    if drift:
        top = max(scores, key=lambda k: scores[k])
        scores[top] = round(scores[top] + drift, 3)
    return scores


def _block(scores: dict[str, float]) -> dict:
    label = max(scores, key=lambda k: scores[k])
    return {"label": label, "confidence": scores[label], "scores": scores}


def score_text(text: str, lang: str | None = None) -> dict:
    """Classify one piece of text.

    Pure function: no database access, no HTTP, no file writes at call time.

    Args:
        text: cleaned, normalised text (NOT raw HTML). Truncated internally.
        lang: ISO 639-1 code if already known; None triggers internal detection.

    Returns:
        dict conforming exactly to `ml.schema.ScoreResult` (PRD §9.1).

    Raises:
        ValueError: on empty or whitespace-only text. Never returns a partial dict.
    """
    if not text or not text.strip():
        raise ValueError("score_text requires non-empty text")

    started = time.perf_counter()
    digest = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)

    result = {
        "schema_version": SCHEMA_VERSION,
        "model_version": STUB_MODEL_VERSION,
        "language": {"code": lang or "en", "confidence": 0.99},
        "truncated": len(text) > _STUB_TRUNCATE_CHARS,
        "sentiment": _block(_pseudo_scores(digest, 0, ("negative", "neutral", "positive"))),
        "hostility": _block(
            _pseudo_scores(digest, 3, ("none", "hostile_rhetoric", "threatening_language"))
        ),
        "disinfo": _block(
            _pseudo_scores(digest, 5, ("likely_reliable", "uncertain", "likely_unreliable"))
        ),
        # Stance is [PROPOSED] and may be descoped entirely (PRD FR-3.4, TBD-4).
        # The stub returns the descoped shape so the backend and UI handle the
        # not_applicable path from day one rather than discovering it in Week 7.
        "stance": {"label": "not_applicable", "confidence": 0.0, "scores": {}},
        "entities": [],
        "topics": [],
        "meta": {
            "inference_ms": int((time.perf_counter() - started) * 1000),
            "device": "stub",
            "chars_in": len(text),
        },
    }

    # The contract is enforced on the stub too — not just on the real model.
    return ScoreResult.model_validate(result).model_dump()
