"""Language detection. ⟵ TRD §5.3, FR-2.3, FR-2.4

Two decisions here, both deliberate.

**The detector is not restricted to the three demo languages.** Restricting it
would force every Spanish or Portuguese item into `ar`, `en` or `fr` with high
confidence, because the detector can only answer from the set it is given. The
candidate set is deliberately wider than the supported set, so "this is Spanish"
is a possible answer — and Spanish then lands in `other` rather than being
mislabelled French and poisoning the French baseline.

**Low confidence is flagged, never guessed away.** Below 0.60 the item keeps its
best guess but carries `uncertain=True` ⟵ FR-2.4, and the UI shows a badge. An
item POLIS is unsure about must look unsure.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from lingua import Language, LanguageDetectorBuilder

# What POLIS supports end to end ⟵ TBD-1, DOC-007 §4.1.
SUPPORTED: frozenset[str] = frozenset({"ar", "en", "fr"})

# What the detector is allowed to *consider*. Wider than SUPPORTED on purpose —
# these are the languages plausibly present in UN News and ReliefWeb output, so
# the detector can say "not one of yours" instead of being forced to pick.
_CANDIDATES = (
    Language.ARABIC,
    Language.ENGLISH,
    Language.FRENCH,
    Language.SPANISH,
    Language.PORTUGUESE,
    Language.RUSSIAN,
    Language.CHINESE,
    Language.SWAHILI,
    Language.GERMAN,
    Language.TURKISH,
)

CONFIDENCE_FLOOR = 0.60  # ⟵ FR-2.4, TRD §5.10

# Below this there is not enough text for any detector to be meaningful. A
# three-word headline with no body is common in feeds and must not be assigned a
# language with false confidence.
MIN_CHARS = 20


@dataclass(frozen=True, slots=True)
class LanguageResult:
    code: str  # ISO 639-1, or "other", or "und" when undetectable
    confidence: float
    uncertain: bool
    supported: bool


@lru_cache(maxsize=1)
def _detector():
    """Built once. Construction loads language models and is expensive; the
    scheduler calls this thousands of times per cycle."""
    return LanguageDetectorBuilder.from_languages(*_CANDIDATES).build()


def detect(text: str) -> LanguageResult:
    """Best-effort language of `text`, with its confidence exposed."""
    stripped = (text or "").strip()
    if len(stripped) < MIN_CHARS:
        return LanguageResult(code="und", confidence=0.0, uncertain=True, supported=False)

    values = _detector().compute_language_confidence_values(stripped)
    if not values:
        return LanguageResult(code="und", confidence=0.0, uncertain=True, supported=False)

    best = values[0]
    code = best.language.iso_code_639_1.name.lower()
    supported = code in SUPPORTED

    return LanguageResult(
        code=code if supported else "other",
        confidence=round(best.value, 3),
        uncertain=best.value < CONFIDENCE_FLOOR,
        # An unsupported language is still detected and still stored; it is
        # excluded from per-language indicators, not from the corpus.
        supported=supported,
    )
