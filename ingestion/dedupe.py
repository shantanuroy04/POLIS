"""Exact and near-duplicate detection. ⟵ TRD §5.4, FR-2.5/2.6/2.7

**Duplicates are linked, never deleted.** The naive instinct is that dedupe
means discard, and here it would silently break a downstream requirement:
IND-03 (Narrative Amplification) measures how widely the *same* story spreads,
so cluster size is the signal. Throwing away the second copy throws away the
measurement ⟵ FR-2.7.

Two stages, cheap first:

1. **Exact** — SHA-256 of ``normalized_text``. Catches the same wire story
   republished verbatim, which is most of what UN News feeds do to each other.
2. **Near** — 64-bit SimHash as a *candidate filter*, then token Jaccard
   ≥ 0.85 as the *decision*.

## Why the Hamming threshold is 12 and not TRD §5.4's 3

TRD §5.4 specifies "Hamming distance ≤ 3 (≈ 0.95 similarity)". That is the
standard SimHash rule for **large documents**, and it does not survive contact
with news items. Measured on real POLIS-shaped text:

    punctuation-only difference        Hamming  0    Jaccard 1.00
    one word appended, 25 tokens       Hamming  8    Jaccard 0.958
    one word changed, 35 tokens        Hamming  7    Jaccard 0.833
    unrelated story                    Hamming 29    Jaccard 0.14

A 3-bit gate rejects every one of those true near-duplicates. The cause is
structural: SimHash bits are a majority vote over shingles, and a 30-token item
has ~28 shingles, so changing one shingle moves a large fraction of the vote.
The textbook threshold assumes thousands.

Left at 3, this stage would find almost nothing beyond what exact hashing
already finds, **IND-03 (Narrative Amplification) would report near-zero, and
that reads as "no amplification" when it means "the detector is blind."** Same
class of defect as the original ADR-001 latency claim: a number borrowed from
another context and never checked against POLIS's own data.

So the roles are corrected to what the two-stage design always intended.
SimHash is a **cheap filter** with a deliberately loose threshold; Jaccard is
the **decision**. The measured gap between 8 and 29 is wide, so 12 separates the
two populations with room on both sides.

**These thresholds are provisional until measured on real ingested volume**
(Week 8, alongside TBD-11). The measurements are recorded here rather than the
number alone, because the next person to touch them needs the evidence.
"""

from __future__ import annotations

import hashlib

SIMHASH_BITS = 64
SHINGLE_SIZE = 3
# Candidate filter, not a decision. TRD §5.4 says 3; measured true near-duplicates
# land at 7-8 and unrelated stories at ~29, so 3 rejects real duplicates while 12
# separates the two populations. See the module docstring for the measurements.
MAX_HAMMING = 12
MIN_JACCARD = 0.85  # ⟵ PRD FR-2.6. This is what actually decides.

_MASK = (1 << SIMHASH_BITS) - 1


def hash_exact(normalized_text: str) -> str:
    """⟵ TRD §5.4. Takes `normalized_text`, never `cleaned_text` — the whole
    point of the folded form is that trivial punctuation differences collide."""
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


def shingles(normalized_text: str, size: int = SHINGLE_SIZE) -> set[str]:
    """Overlapping n-gram token shingles.

    Short texts shorter than one shingle fall back to their own tokens, so a
    headline-only item still produces a usable fingerprint rather than nothing.
    """
    tokens = normalized_text.split()
    if not tokens:
        return set()
    if len(tokens) < size:
        return set(tokens)
    return {" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1)}


def simhash(normalized_text: str) -> int:
    """64-bit SimHash over shingles ⟵ TRD §5.4.

    Unweighted: every shingle counts once. Term-frequency weighting is the usual
    refinement and is skipped deliberately — news items are short, repeated
    shingles are rare, and the Jaccard confirmation below is what actually
    decides. ponytail: revisit only if measured precision is poor.
    """
    grams = shingles(normalized_text)
    if not grams:
        return 0

    vector = [0] * SIMHASH_BITS
    for gram in grams:
        h = int.from_bytes(hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest(), "big")
        for bit in range(SIMHASH_BITS):
            vector[bit] += 1 if (h >> bit) & 1 else -1

    out = 0
    for bit in range(SIMHASH_BITS):
        if vector[bit] > 0:
            out |= 1 << bit
    return out & _MASK


def to_signed64(value: int) -> int:
    """Reinterpret an unsigned 64-bit SimHash as PostgreSQL's signed `bigint`.

    SimHash fills all 64 bits, and roughly half of all values are >= 2**63, which
    `bigint` cannot hold — the insert fails with "bigint out of range" on those
    and succeeds on the rest, so the bug looks intermittent. The bit pattern is
    what matters and is preserved; only its interpretation changes.

    `hamming` masks to 64 bits, so signed and unsigned forms compare correctly
    against each other. Converting on the way in anyway, because a column whose
    values mean two different things depending on who wrote them is a trap.
    """
    return value - (1 << 64) if value >= (1 << 63) else value


def to_unsigned64(value: int) -> int:
    """Inverse of :func:`to_signed64`, for values read back from the database."""
    return value + (1 << 64) if value < 0 else value


def hamming(a: int, b: int) -> int:
    return ((a ^ b) & _MASK).bit_count()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def bands(value: int, width: int = 16) -> tuple[int, ...]:
    """Split a simhash into fixed-width chunks for a banded index ⟵ TRD §5.4.

    **Unused at current scale, and kept deliberately.** The pigeonhole guarantee
    banding depends on — two values within Hamming distance ≤ 3 must share an
    identical 16-bit band — no longer holds now that the threshold is 12.
    Banding would silently miss the duplicates it was added to find.

    At POLIS's actual volume the index is unnecessary anyway: a 7-day window
    holds roughly 700 items, and comparing 700 integers takes microseconds. The
    scan is both correct and simpler.

    Retained because Week 5's schema references it and volume may grow. If it
    ever does, re-derive banding for the threshold in force then rather than
    copying TRD §5.4.
    """
    return tuple((value >> (i * width)) & ((1 << width) - 1) for i in range(SIMHASH_BITS // width))


def is_near_duplicate(a_norm: str, b_norm: str) -> bool:
    """Full two-stage check for a single pair.

    Week 5's database path scans the 7-day window for candidates and then calls
    this same comparison, so the thresholds live in exactly one place and cannot
    drift between the in-memory and the stored path.
    """
    if hamming(simhash(a_norm), simhash(b_norm)) > MAX_HAMMING:
        return False
    return jaccard(shingles(a_norm), shingles(b_norm)) >= MIN_JACCARD
