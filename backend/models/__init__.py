"""SQLAlchemy models — the eight tables POLIS actually builds. ⟵ DOC-005, DOC-016 §5

DOC-005 specifies 23 tables for the six-person design. This is the solo subset,
and every reduction is a decision rather than an omission:

* **No `roles` / `permissions` / `role_permissions`.** Separation of duties needs
  two people to separate. `users.role` is a plain column. Argon2id hashing and
  the audit log stay — SEC-5 does not scale with team size.
* **No `model_versions`.** One model, so `nlp_results.model_version` is the text
  the model reports. A registry table for a single row is a join with no reader.
* **No `entities` / `content_entities` / `topics` / `content_topics`.** Entities
  and topics live in JSONB on `nlp_results` with GIN indexes. Normalising buys
  joins and "every item mentioning X" — which is the Search page, and Search is
  on the restore ladder, not in scope. At ~100 items a day a GIN containment
  query is fast. Promote them if Search is ever restored.
* **No `subjects` / `indicator_definitions`.** A subject is a (topic, region,
  language) tuple, so it is three columns rather than a table and a join. Two
  indicator definitions live in code, where their formulas already are.
* **No `ingestion_runs`.** Run history is a descoped page. Source health is four
  columns on `sources`.
* **No `analyst_reviews`.** Folded into `alerts`, which is where a single
  reviewer's decision belongs.
* **No `translations`.** The translation layer is descoped; language is detected
  and stored, never translated.

Alert evidence is a **JSONB snapshot, not a foreign key**, and that is
deliberate. Raw content is purged at 180 days (PRIV-4) while alerts are kept for
365, so a foreign key would either block the purge or cascade away the very
basis of the alert. The snapshot keeps the alert readable after its sources are
gone.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


TIMESTAMPTZ = DateTime(timezone=True)

# Kept in one place so a label can never drift between the database constraint
# and ml/schema.py's frozen contract.
SENTIMENT_LABELS = ("negative", "neutral", "positive", "not_applicable")
HOSTILITY_LABELS = ("none", "hostile_rhetoric", "threatening_language", "not_applicable")
DISINFO_LABELS = ("likely_reliable", "uncertain", "likely_unreliable", "not_applicable")
STANCE_LABELS = ("supportive", "neutral", "opposed", "not_applicable")
SEVERITIES = ("normal", "informational", "low", "medium", "high", "critical")
ALERT_SEVERITIES = ("low", "medium", "high", "critical")


def _in(column: str, values: tuple[str, ...]) -> str:
    joined = ",".join(f"'{v}'" for v in values)
    return f"{column} IN ({joined})"


# --------------------------------------------------------------------------- identity


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    # A column, not a roles table. One account, and the audit log is what
    # actually carries accountability ⟵ DOC-016 §5.
    role: Mapped[str] = mapped_column(Text, nullable=False, default="admin")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, server_default=func.now(), onupdate=_now
    )

    __table_args__ = (
        CheckConstraint("length(full_name) BETWEEN 1 AND 200", name="ck_users_name_len"),
        CheckConstraint(r"email ~ '^[^@]+@[^@]+\.[^@]+$'", name="ck_users_email_shape"),
        CheckConstraint(_in("status", ("active", "disabled")), name="ck_users_status"),
        CheckConstraint(_in("role", ("analyst", "supervisor", "admin")), name="ck_users_role"),
        CheckConstraint("failed_login_count >= 0", name="ck_users_failed_count"),
    )


# --------------------------------------------------------------------------- ingestion


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = _uuid_pk()
    key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(Text, nullable=False, default="rss")
    url: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(2))
    region: Mapped[str | None] = mapped_column(Text)
    poll_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="enabled")

    # Replaces the ingestion_runs table: run history is a descoped page, and the
    # scheduler and the UI badge only ever read the latest outcome.
    health_status: Mapped[str] = mapped_column(Text, nullable=False, default="healthy")
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    last_run_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    last_success_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)

    reliability_band: Mapped[str] = mapped_column(Text, nullable=False, default="limited")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_cursor: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, server_default=func.now(), onupdate=_now
    )

    __table_args__ = (
        CheckConstraint(
            _in("source_type", ("rss", "telegram", "reddit", "html_page")),
            name="ck_sources_type",
        ),
        CheckConstraint("language ~ '^[a-z]{2}$'", name="ck_sources_language"),
        CheckConstraint("poll_minutes BETWEEN 5 AND 1440", name="ck_sources_poll"),
        CheckConstraint(_in("status", ("enabled", "disabled")), name="ck_sources_status"),
        CheckConstraint(
            _in("health_status", ("healthy", "degraded", "unhealthy", "config_error")),
            name="ck_sources_health",
        ),
        CheckConstraint(
            _in("reliability_band", ("established", "mixed", "limited")),
            name="ck_sources_band",
        ),
        CheckConstraint("consecutive_failures >= 0", name="ck_sources_failures"),
        # The scheduler's hot path: which enabled sources are due?
        Index(
            "ix_sources_due",
            "status",
            "health_status",
            "last_success_at",
            postgresql_where=("status = 'enabled'"),
        ),
    )


class RawContent(Base):
    __tablename__ = "raw_content"

    id: Mapped[uuid.UUID] = _uuid_pk()
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_handle: Mapped[str | None] = mapped_column(Text)  # public handle only ⟵ PRIV-2
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    collected_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    source: Mapped[Source] = relationship()

    __table_args__ = (
        CheckConstraint("length(body) > 0", name="ck_raw_body_nonempty"),
        Index(
            "ux_raw_source_external",
            "source_id",
            "external_id",
            unique=True,
            postgresql_where=("external_id IS NOT NULL"),
        ),
        Index("ix_raw_source_pub", "source_id", "published_at"),
        # Indicator windows read by effective time, not by whichever of the two
        # happens to be set.
        Index("ix_raw_effective_time", func.coalesce("published_at", "collected_at")),
    )


class ProcessedContent(Base):
    __tablename__ = "processed_content"

    id: Mapped[uuid.UUID] = _uuid_pk()
    raw_content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_content.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    cleaned_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    language_code: Mapped[str | None] = mapped_column(Text)
    language_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    language_uncertain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    simhash: Mapped[int | None] = mapped_column(BigInteger)
    cluster_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_canonical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending_analysis")
    processed_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())

    raw: Mapped[RawContent] = relationship()

    __table_args__ = (
        CheckConstraint(
            "language_code IS NULL OR language_code ~ '^[a-z]{2,5}$'", name="ck_pc_language"
        ),
        CheckConstraint(
            "language_confidence IS NULL OR language_confidence BETWEEN 0 AND 1",
            name="ck_pc_lang_conf",
        ),
        CheckConstraint(
            _in(
                "status",
                ("pending_analysis", "analyzed", "scoring_failed", "clean_degraded"),
            ),
            name="ck_pc_status",
        ),
        # The scoring job's queue.
        Index(
            "ix_pc_pending",
            "processed_at",
            postgresql_where=("status = 'pending_analysis'"),
        ),
        Index("ix_pc_cluster", "cluster_id"),
        Index("ix_pc_lang", "language_code", "processed_at"),
        # Dedupe scans the 7-day window by simhash ⟵ ingestion/dedupe.py.
        Index("ix_pc_simhash", "simhash", postgresql_where=("simhash IS NOT NULL")),
    )


# --------------------------------------------------------------------------- ML


class NlpResult(Base):
    __tablename__ = "nlp_results"

    id: Mapped[uuid.UUID] = _uuid_pk()
    processed_content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processed_content.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Text, not a FK to model_versions. One model in scope, and the value is
    # exactly what score_text reports, so the row is self-describing.
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False, default="1.0")

    sentiment_label: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment_confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    sentiment_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    hostility_label: Mapped[str] = mapped_column(Text, nullable=False)
    hostility_confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    hostility_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    disinfo_label: Mapped[str] = mapped_column(Text, nullable=False)
    disinfo_confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    disinfo_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    stance_label: Mapped[str] = mapped_column(Text, nullable=False, default="not_applicable")
    stance_confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0)
    stance_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # JSONB rather than four tables ⟵ module docstring. GIN-indexed, because the
    # indicator aggregates filter on topic containment.
    entities: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    topics: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    inference_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())

    content: Mapped[ProcessedContent] = relationship()

    __table_args__ = (
        UniqueConstraint("processed_content_id", "model_version", name="ux_nlp_content_model"),
        CheckConstraint(_in("sentiment_label", SENTIMENT_LABELS), name="ck_nlp_sentiment"),
        CheckConstraint(_in("hostility_label", HOSTILITY_LABELS), name="ck_nlp_hostility"),
        CheckConstraint(_in("disinfo_label", DISINFO_LABELS), name="ck_nlp_disinfo"),
        CheckConstraint(_in("stance_label", STANCE_LABELS), name="ck_nlp_stance"),
        CheckConstraint(
            "sentiment_confidence BETWEEN 0 AND 1 AND hostility_confidence BETWEEN 0 AND 1 "
            "AND disinfo_confidence BETWEEN 0 AND 1 AND stance_confidence BETWEEN 0 AND 1",
            name="ck_nlp_confidences",
        ),
        Index("ix_nlp_content", "processed_content_id"),
        Index(
            "ix_nlp_hostility",
            "hostility_label",
            "created_at",
            postgresql_where=("hostility_label <> 'none'"),
        ),
        Index("ix_nlp_topics", "topics", postgresql_using="gin"),
        Index("ix_nlp_entities", "entities", postgresql_using="gin"),
    )


# --------------------------------------------------------------------------- signal


class IndicatorScore(Base):
    """One indicator, one subject, one window.

    `subject` is three denormalised columns rather than a foreign key to a
    `subjects` table: the tuple is (topic, region, language), it is small, and a
    lookup table for it would be a join on every aggregate read for no gain.
    """

    __tablename__ = "indicator_scores"

    id: Mapped[uuid.UUID] = _uuid_pk()
    indicator_code: Mapped[str] = mapped_column(Text, nullable=False)  # 'IND-01'

    subject_topic: Mapped[str] = mapped_column(Text, nullable=False)
    subject_region: Mapped[str] = mapped_column(Text, nullable=False)
    subject_language: Mapped[str] = mapped_column(Text, nullable=False)

    window_start: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    window_end: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)

    computed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    not_computed_reason: Mapped[str | None] = mapped_column(Text)

    raw_value: Mapped[float | None] = mapped_column(Numeric(10, 5))
    baseline_mean: Mapped[float | None] = mapped_column(Numeric(10, 5))
    baseline_stddev: Mapped[float | None] = mapped_column(Numeric(10, 5))
    z_score: Mapped[float | None] = mapped_column(Numeric(8, 3))
    threshold_applied: Mapped[float | None] = mapped_column(Numeric(6, 3))
    severity: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))

    n_current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_sources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_content_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    alert_evaluated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "indicator_code",
            "subject_topic",
            "subject_region",
            "subject_language",
            "window_end",
            name="ux_score_window",
        ),
        CheckConstraint("window_end > window_start", name="ck_score_window"),
        # An uncomputed score must say why. Silence without a reason is
        # indistinguishable from a bug ⟵ PRD §10.
        CheckConstraint(
            "computed = true OR not_computed_reason IS NOT NULL", name="ck_score_reason"
        ),
        CheckConstraint(
            "not_computed_reason IS NULL OR "
            + _in(
                "not_computed_reason",
                ("below_n_min", "insufficient_baseline", "no_data", "gate_not_met"),
            ),
            name="ck_score_reason_values",
        ),
        CheckConstraint(
            "severity IS NULL OR " + _in("severity", SEVERITIES), name="ck_score_severity"
        ),
        CheckConstraint(
            "jsonb_array_length(evidence_content_ids) <= 50", name="ck_score_evidence_cap"
        ),
        # The alert job's queue.
        Index(
            "ix_scores_pending_alert",
            "created_at",
            postgresql_where=(
                "computed AND NOT alert_evaluated "
                "AND severity IN ('low','medium','high','critical')"
            ),
        ),
        Index(
            "ix_scores_trend",
            "subject_topic",
            "subject_region",
            "subject_language",
            "indicator_code",
            "window_end",
        ),
    )


class Alert(Base):
    """A raised alert, and the single reviewer's decision on it.

    DOC-005's `analyst_reviews` is folded in: with one account there is no
    review queue to model, only a decision to record.
    """

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    indicator_code: Mapped[str] = mapped_column(Text, nullable=False)
    subject_topic: Mapped[str] = mapped_column(Text, nullable=False)
    subject_region: Mapped[str] = mapped_column(Text, nullable=False)
    subject_language: Mapped[str] = mapped_column(Text, nullable=False)

    triggering_score_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("indicator_scores.id", ondelete="RESTRICT"),
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="new")
    # Carries the mandatory non-prediction clause ⟵ PRD §10.6.
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    raw_value: Mapped[float] = mapped_column(Numeric(10, 5), nullable=False)
    baseline_mean: Mapped[float] = mapped_column(Numeric(10, 5), nullable=False)
    baseline_stddev: Mapped[float] = mapped_column(Numeric(10, 5), nullable=False)
    z_score: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    threshold_applied: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    n_items: Mapped[int] = mapped_column(Integer, nullable=False)
    n_sources: Mapped[int] = mapped_column(Integer, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # A snapshot, not a foreign key. Raw content is purged at 180 days while
    # alerts are kept for 365, so a FK would either block the purge or cascade
    # away the alert's own basis ⟵ module docstring, PRIV-4.
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ)
    review_note: Mapped[str | None] = mapped_column(Text)

    first_seen_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())

    __table_args__ = (
        CheckConstraint(_in("severity", ALERT_SEVERITIES), name="ck_alerts_severity"),
        CheckConstraint(
            _in(
                "status",
                (
                    "new",
                    "acknowledged",
                    "under_review",
                    "resolved_confirmed",
                    "resolved_rejected",
                    "resolved_inconclusive",
                ),
            ),
            name="ck_alerts_status",
        ),
        CheckConstraint("occurrence_count >= 1", name="ck_alerts_occurrences"),
        # A resolution without a reviewer and a timestamp is not a resolution.
        CheckConstraint(
            "status NOT LIKE 'resolved%' OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL)",
            name="ck_alerts_resolution_complete",
        ),
        # At most ONE open alert per (indicator, subject). This is what makes
        # FR-5.2's dedup race-proof — the database refuses the second insert
        # rather than the application trying to win a check-then-act race.
        Index(
            "ux_alert_open",
            "indicator_code",
            "subject_topic",
            "subject_region",
            "subject_language",
            unique=True,
            postgresql_where=("status IN ('new','acknowledged','under_review')"),
        ),
        Index("ix_alerts_queue", "status", "severity", "created_at"),
    )


# --------------------------------------------------------------------------- audit


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    actor_type: Mapped[str] = mapped_column(Text, nullable=False, default="user")
    action: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, server_default=func.now())

    __table_args__ = (
        CheckConstraint(_in("actor_type", ("user", "system")), name="ck_audit_actor_type"),
        CheckConstraint(_in("result", ("success", "denied", "failure")), name="ck_audit_result"),
        # Defence in depth ⟵ SEC-20. The application is supposed to never put a
        # secret in `detail`; this makes the database refuse it if it ever does.
        CheckConstraint(
            "NOT (detail::text ~* '\"(password|secret|token|api_key|password_hash)\"')",
            name="ck_audit_no_secrets",
        ),
        Index("ix_audit_actor", "actor_id", "created_at"),
        Index("ix_audit_action", "action", "created_at"),
        Index("ix_audit_resource", "resource_type", "resource_id", "created_at"),
        Index("ix_audit_denied", "created_at", postgresql_where=("result = 'denied'")),
    )


__all__ = [
    "Alert",
    "AuditLog",
    "Base",
    "IndicatorScore",
    "NlpResult",
    "ProcessedContent",
    "RawContent",
    "Source",
    "User",
]
