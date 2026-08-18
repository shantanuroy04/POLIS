"""Retrieved bytes → ML-ready, storage-safe text. ⟵ TRD §5.3, FR-2.1/2.2/2.11, SEC-13

Two outputs, and the difference between them is the whole point.

``cleaned_text`` is what the model reads and what a human sees. Casing and
diacritics are **preserved** ⟵ FR-2.2. Lowercasing is a reflex left over from
bag-of-words pipelines and it destroys signal XLM-RoBERTa's tokenizer relies on;
"US" and "us" are not the same token, and Arabic diacritics are not noise.

``normalized_text`` is aggressively folded and exists **only** for hashing and
duplicate detection. It never reaches the model.

POLIS never stores or renders HTML ⟵ SEC-13. Tags are stripped here, once, and
what is stored is text. The frontend renders it as React text nodes, and
``dangerouslySetInnerHTML`` is lint-banned, so there is no second line of
defence to rely on — this one has to hold.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from bs4 import BeautifulSoup

# Items longer than this are truncated at ingest with a visible flag ⟵ FR-2.11.
# Generous on purpose: the model truncates at its own token limit anyway, and the
# stored text is also what an analyst reads.
MAX_CHARS = 20_000

# Bidirectional overrides can make stored text render as something other than
# what it says ⟵ TRD §14.6. Removed rather than escaped: no legitimate news item
# needs them, and an escaped control character is still a control character to
# whatever reads the database next.
_BIDI_CONTROLS = dict.fromkeys(
    [0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)]
)

_ZERO_WIDTH = dict.fromkeys([0x200B, 0x200C, 0x200D, 0xFEFF])

_WHITESPACE = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


@dataclass(frozen=True, slots=True)
class CleanResult:
    cleaned_text: str
    normalized_text: str
    truncated: bool = False
    degraded: bool = False  # decoding fell back; text may contain replacements


def _decode(raw: bytes, content_type: str) -> tuple[str, bool]:
    """Decode using the declared charset, falling back rather than failing.

    A source with a lying or missing charset is common and is not a reason to
    drop an item. The fallback is flagged so the degradation is visible in the
    UI instead of silently becoming part of the corpus ⟵ TRD §5.10.
    """
    charset = "utf-8"
    if "charset=" in content_type.lower():
        charset = content_type.lower().split("charset=", 1)[1].split(";")[0].strip() or "utf-8"
    try:
        return raw.decode(charset), False
    except (LookupError, UnicodeDecodeError):
        return raw.decode("utf-8", errors="replace"), True


def strip_html(text: str) -> str:
    """All tags to text, with script and style *contents* removed.

    BeautifulSoup rather than a bleach strip: bleach removes the ``<script>``
    tags but keeps the JavaScript between them as text, which then reads as
    article body and gets scored as if it were prose.
    """
    soup = BeautifulSoup(text, "lxml")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    return soup.get_text(separator=" ")


def normalize_for_hashing(text: str) -> str:
    """Aggressively folded form for dedupe only ⟵ TRD §5.3, §5.4.

    Casefolded, punctuation removed, whitespace collapsed. Two versions of the
    same wire story that differ by a headline comma must hash identically, or
    exact-match dedupe never fires and every near-duplicate falls through to the
    more expensive SimHash path.
    """
    folded = unicodedata.normalize("NFKC", text).casefold()
    folded = _PUNCT.sub(" ", folded)
    return _WHITESPACE.sub(" ", folded).strip()


def clean_text(text: str, *, degraded: bool = False) -> CleanResult:
    """The core path. `clean` wraps this for callers holding bytes."""
    stripped = strip_html(text)
    stripped = stripped.translate(_BIDI_CONTROLS).translate(_ZERO_WIDTH)

    # NFKC before whitespace collapsing, because NFKC turns some exotic space
    # characters into ordinary ones that the collapse should then absorb.
    cleaned = unicodedata.normalize("NFKC", stripped)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()

    truncated = len(cleaned) > MAX_CHARS
    if truncated:
        cleaned = cleaned[:MAX_CHARS].rstrip()

    return CleanResult(
        cleaned_text=cleaned,
        normalized_text=normalize_for_hashing(cleaned),
        truncated=truncated,
        degraded=degraded,
    )


def clean(raw: bytes, content_type: str = "text/html; charset=utf-8") -> CleanResult:
    """⟵ TRD §5.3 interface."""
    text, degraded = _decode(raw, content_type)
    return clean_text(text, degraded=degraded)
