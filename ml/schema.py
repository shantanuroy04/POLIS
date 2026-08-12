"""POLIS ML output contract.

THIS FILE IS THE FROZEN INTERFACE between Team B (ML) and Team C (backend).
Authoritative definition: PRD §9.1, restated in TRD §5.5 and DOC-007 §3.1.

Any change here after Week 4 requires sign-off from BOTH the Team B lead and the
Team C lead, plus a matching update to PRD §9.1, TRD §5.5, and DOC-007 §3.1 in
the same pull request. See ADR-008.

Both the Week-1 stub and the real model pass their output through ScoreResult.
That is deliberate: if the stub could drift from the schema, Teams C and D would
build against a shape the real model will never produce.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"

# Label vocabularies. These MUST match the CHECK constraints on `nlp_results`
# in DB §6 — a test asserts the two sets are identical.
SentimentLabel = Literal["negative", "neutral", "positive", "not_applicable"]
HostilityLabel = Literal["none", "hostile_rhetoric", "threatening_language", "not_applicable"]
DisinfoLabel = Literal["likely_reliable", "uncertain", "likely_unreliable", "not_applicable"]
StanceLabel = Literal["supportive", "neutral", "opposed", "not_applicable"]
EntityType = Literal["PERSON", "ORG", "GPE", "LOC", "EVENT"]


class PolisSchema(BaseModel):
    """Reject-by-default base. Unknown fields are an error, not something to ignore.

    `protected_namespaces=()` is required, not cosmetic: `model_version` is part of
    the frozen PRD §9.1 contract, and pydantic reserves the `model_` prefix by
    default. Renaming the field to silence the warning would break the contract.
    """

    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class LanguageBlock(PolisSchema):
    code: str = Field(pattern=r"^[a-z]{2}$", description="ISO 639-1")
    confidence: float = Field(ge=0.0, le=1.0)


class ClassificationBlock(PolisSchema):
    """One classification head's output.

    `scores` carries the full per-class distribution (FR-3.9) — the arg-max label
    alone is not enough for the UI, which shows confidence per class.
    """

    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    scores: dict[str, float]


class SentimentBlock(ClassificationBlock):
    label: SentimentLabel


class HostilityBlock(ClassificationBlock):
    label: HostilityLabel


class DisinfoBlock(ClassificationBlock):
    label: DisinfoLabel


class StanceBlock(ClassificationBlock):
    label: StanceLabel


class EntityMention(PolisSchema):
    text: str
    type: EntityType
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    confidence: float = Field(ge=0.0, le=1.0)


class TopicAssignment(PolisSchema):
    topic: str
    confidence: float = Field(ge=0.0, le=1.0)


class MetaBlock(PolisSchema):
    inference_ms: int = Field(ge=0)
    device: str
    chars_in: int = Field(ge=0)


class ScoreResult(PolisSchema):
    """The complete return value of `score_text()`.

    EVERY key is always present. A descoped or disabled task returns
    label="not_applicable" with confidence=0.0 — never a missing key, never None.
    Backend code may therefore index every field without defensive checks.
    """

    schema_version: str
    model_version: str
    language: LanguageBlock
    truncated: bool
    sentiment: SentimentBlock
    hostility: HostilityBlock
    disinfo: DisinfoBlock
    stance: StanceBlock
    entities: list[EntityMention]
    topics: list[TopicAssignment]
    meta: MetaBlock
