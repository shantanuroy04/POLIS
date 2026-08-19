"""Schema constraint tests. ⟵ DOC-005, SEC-20, FR-5.2

These assert the constraints that carry a requirement, not that SQLAlchemy can
insert a row. Each one below is a rule the application could get wrong and the
database refuses anyway.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.db import ADVISORY_LOCK_NAMESPACE
from backend.models import (
    Alert,
    AuditLog,
    IndicatorScore,
    NlpResult,
    ProcessedContent,
    RawContent,
    Source,
    User,
)
from tests.db.conftest import requires_db

pytestmark = requires_db

NOW = datetime.now(tz=timezone.utc)


def _content(session: Session, source: Source, *, hash_suffix: str = "") -> ProcessedContent:
    raw = RawContent(
        source_id=source.id,
        external_id=f"urn:{uuid.uuid4()}",
        url="https://news.example.com/a",
        title="Ceasefire holds",
        body="Reports indicate the ceasefire is holding.",
        published_at=NOW,
        content_hash=(uuid.uuid4().hex + uuid.uuid4().hex)[: 64 - len(hash_suffix)] + hash_suffix,
    )
    session.add(raw)
    session.flush()
    pc = ProcessedContent(
        raw_content_id=raw.id,
        cleaned_text="Reports indicate the ceasefire is holding.",
        normalized_text="reports indicate the ceasefire is holding",
        language_code="en",
        language_confidence=0.97,
        cluster_id=uuid.uuid4(),
    )
    session.add(pc)
    session.flush()
    return pc


# --- the eight tables exist and round-trip ----------------------------------


def test_content_chain_round_trips(session: Session, source: Source):
    pc = _content(session, source)
    assert pc.status == "pending_analysis"
    assert pc.is_canonical is True
    assert session.get(ProcessedContent, pc.id) is pc


def test_raw_content_hash_is_unique(session: Session, source: Source):
    """Exact-duplicate defence lives in the database, not only in the deduper.
    Two workers racing on the same item must not both insert ⟵ FR-2.5."""
    shared = uuid.uuid4().hex + uuid.uuid4().hex
    for _ in range(2):
        session.add(
            RawContent(
                source_id=source.id,
                body="same story",
                content_hash=shared[:64],
            )
        )
    with pytest.raises(IntegrityError):
        session.flush()


def test_processed_content_is_one_per_raw(session: Session, source: Source):
    pc = _content(session, source)
    session.add(
        ProcessedContent(
            raw_content_id=pc.raw_content_id,
            cleaned_text="again",
            normalized_text="again",
            cluster_id=uuid.uuid4(),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# --- score integrity ⟵ PRD §10 ----------------------------------------------


def _score(session: Session, **kw) -> IndicatorScore:
    defaults = {
        "indicator_code": "IND-01",
        "subject_topic": "T-01",
        "subject_region": "northern-africa",
        "subject_language": "en",
        "window_start": NOW - timedelta(days=1),
        "window_end": NOW,
        "computed": True,
        "severity": "medium",
        "raw_value": 1.5,
        "z_score": 2.4,
    }
    defaults.update(kw)
    score = IndicatorScore(**defaults)
    session.add(score)
    session.flush()
    return score


def test_an_uncomputed_score_must_say_why(session: Session):
    """Silence without a stated reason is indistinguishable from a bug. PRD §10
    requires "not computed" to name its cause, and this is what enforces it."""
    session.add(
        IndicatorScore(
            indicator_code="IND-01",
            subject_topic="T-01",
            subject_region="northern-africa",
            subject_language="en",
            window_start=NOW - timedelta(days=1),
            window_end=NOW,
            computed=False,
            not_computed_reason=None,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_below_n_min_is_a_valid_uncomputed_score(session: Session):
    score = _score(session, computed=False, not_computed_reason="below_n_min", severity=None)
    assert score.computed is False


def test_window_end_must_follow_window_start(session: Session):
    with pytest.raises(IntegrityError):
        _score(session, window_start=NOW, window_end=NOW - timedelta(hours=1))


def test_one_score_per_indicator_subject_window(session: Session):
    _score(session)
    with pytest.raises(IntegrityError):
        _score(session)


def test_evidence_is_capped_at_fifty(session: Session):
    """FR-5.4. An alert that cites 4,000 items is not evidence, it is a dump."""
    with pytest.raises(IntegrityError):
        _score(session, evidence_content_ids=[str(uuid.uuid4()) for _ in range(51)])


# --- alert dedup ⟵ FR-5.2 ---------------------------------------------------


def _alert(session: Session, score: IndicatorScore, **kw) -> Alert:
    defaults = {
        "indicator_code": score.indicator_code,
        "subject_topic": score.subject_topic,
        "subject_region": score.subject_region,
        "subject_language": score.subject_language,
        "triggering_score_id": score.id,
        "severity": "medium",
        "explanation": "Sentiment shifted. POLIS does not predict events; a human must assess.",
        "raw_value": 1.5,
        "baseline_mean": 0.5,
        "baseline_stddev": 0.3,
        "z_score": 2.4,
        "threshold_applied": 2.0,
        "confidence": 0.8,
        "n_items": 25,
        "n_sources": 3,
    }
    defaults.update(kw)
    alert = Alert(**defaults)
    session.add(alert)
    session.flush()
    return alert


def test_only_one_open_alert_per_indicator_and_subject(session: Session):
    """FR-5.2's dedup is race-proof because the database refuses the second
    insert — not because the application wins a check-then-act race."""
    score = _score(session)
    _alert(session, score)
    with pytest.raises(IntegrityError):
        _alert(session, score)


def test_a_resolved_alert_frees_the_slot(session: Session):
    score = _score(session)
    first = _alert(session, score)
    user = User(
        full_name="Analyst",
        email=f"a{uuid.uuid4().hex[:8]}@example.com",
        password_hash="argon2-hash",
    )
    session.add(user)
    session.flush()

    first.status = "resolved_confirmed"
    first.reviewed_by = user.id
    first.reviewed_at = NOW
    session.flush()

    second = _alert(session, score)  # must not raise
    assert second.status == "new"


def test_resolution_requires_a_reviewer_and_a_timestamp(session: Session):
    """A resolution with nobody attached is not a resolution — it is an audit
    gap wearing a status field."""
    score = _score(session)
    alert = _alert(session, score)
    alert.status = "resolved_confirmed"
    with pytest.raises(IntegrityError):
        session.flush()


# --- audit ⟵ SEC-20 ---------------------------------------------------------


def test_audit_detail_rejects_secret_shaped_keys(session: Session):
    """Defence in depth. The application is supposed to never put a secret in
    `detail`; this makes the database refuse it when it does."""
    session.add(
        AuditLog(
            actor_type="system",
            action="auth.login",
            resource_type="user",
            result="success",
            detail={"password": "hunter2"},
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_audit_detail_accepts_ordinary_context(session: Session):
    log = AuditLog(
        actor_type="system",
        action="alert.raised",
        resource_type="alert",
        resource_id=str(uuid.uuid4()),
        result="success",
        detail={"severity": "medium", "n_items": 25},
    )
    session.add(log)
    session.flush()
    assert log.id > 0


# --- users ------------------------------------------------------------------


def test_email_must_look_like_an_email(session: Session):
    session.add(User(full_name="X", email="not-an-email", password_hash="h"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_email_is_unique(session: Session):
    email = f"dup{uuid.uuid4().hex[:8]}@example.com"
    session.add(User(full_name="A", email=email, password_hash="h"))
    session.flush()
    session.add(User(full_name="B", email=email, password_hash="h"))
    with pytest.raises(IntegrityError):
        session.flush()


# --- nlp ---------------------------------------------------------------------


def test_nlp_result_stores_the_frozen_contract_shape(session: Session, source: Source):
    """The columns mirror ml/schema.py. If the contract ever changes, this test
    and the schema test in tests/ml both have to change — which is the point."""
    pc = _content(session, source)
    result = NlpResult(
        processed_content_id=pc.id,
        model_version="polis-stub-v0.0.1",
        sentiment_label="negative",
        sentiment_confidence=0.81,
        sentiment_scores={"negative": 0.81, "neutral": 0.12, "positive": 0.07},
        hostility_label="none",
        hostility_confidence=0.9,
        hostility_scores={"none": 0.9},
        disinfo_label="not_applicable",
        disinfo_confidence=0.0,
        disinfo_scores={},
        entities=[{"text": "Mali", "type": "GPE"}],
        topics=[{"code": "T-01", "score": 0.7}],
    )
    session.add(result)
    session.flush()
    assert result.stance_label == "not_applicable"


def test_nlp_label_values_are_constrained(session: Session, source: Source):
    pc = _content(session, source)
    session.add(
        NlpResult(
            processed_content_id=pc.id,
            model_version="v1",
            sentiment_label="furious",  # not in the frozen enum
            sentiment_confidence=0.5,
            sentiment_scores={},
            hostility_label="none",
            hostility_confidence=0.5,
            hostility_scores={},
            disinfo_label="not_applicable",
            disinfo_confidence=0.0,
            disinfo_scores={},
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# --- advisory lock ⟵ TRD §6.2 ------------------------------------------------


def test_advisory_lock_is_exclusive_across_connections(session: Session, engine):
    """`pipeline_cycle` runs every 10 minutes with max_instances=1. If a run
    overruns, the next must skip rather than run concurrently and double-process."""
    held = session.execute(
        text("SELECT pg_try_advisory_xact_lock(:ns, 1)"), {"ns": ADVISORY_LOCK_NAMESPACE}
    ).scalar_one()
    assert held is True

    with engine.connect() as other:
        second = other.execute(
            text("SELECT pg_try_advisory_xact_lock(:ns, 1)"), {"ns": ADVISORY_LOCK_NAMESPACE}
        ).scalar_one()
        assert second is False, "a second run acquired the pipeline lock"
