"""Dedupe tests. ⟵ TRD §5.4, FR-2.5/2.6/2.7

The fixtures below are the variants that actually occur in syndication: the same
wire story republished verbatim, with punctuation changed, with a tagline
appended, or with a masthead prefixed. Measured on this text:

    identical                 Hamming  0    Jaccard 1.000   duplicate
    punctuation only          Hamming  0    Jaccard 1.000   duplicate
    trailing word added       Hamming  6    Jaccard 0.960   duplicate
    headline prefix added     Hamming 10    Jaccard 0.960   duplicate
    one word substituted      Hamming 11    Jaccard 0.778   NOT a duplicate
    two words substituted     Hamming 12    Jaccard 0.655   NOT a duplicate
    unrelated story           Hamming 27    Jaccard 0.000   NOT a duplicate

The line falls between "additions" and "substitutions", which is the right place
for IND-03: syndication republishes, it does not paraphrase. A rewritten story is
a different story, and merging the two would inflate an amplification score that
is supposed to mean something.
"""

from __future__ import annotations

from ingestion.clean import normalize_for_hashing as norm
from ingestion.dedupe import (
    MAX_HAMMING,
    bands,
    hamming,
    hash_exact,
    is_near_duplicate,
    jaccard,
    shingles,
    simhash,
    to_signed64,
    to_unsigned64,
)

_BASE = (
    "The Security Council adopted a resolution on Mali on Tuesday, extending the mission "
    "mandate by one year and calling on all parties to resume political dialogue"
)

STORY = norm(_BASE)
SAME_BUT_PUNCTUATED = norm(_BASE.replace(",", ";"))
TAGLINE_APPENDED = norm(_BASE + " immediately")
MASTHEAD_PREFIXED = norm("UN: " + _BASE)
ONE_WORD_SUBSTITUTED = norm(_BASE.replace("the mission", "that mission"))
DIFFERENT = norm(
    "An aid convoy of twelve trucks reached the north on Monday after weeks of negotiation "
    "with local groups over access routes and security guarantees"
)
HEADLINE = norm("Security Council adopts Mali resolution")
HEADLINE_EDIT = norm("Security Council adopts a Mali resolution")


# --- exact ⟵ FR-2.5 ---------------------------------------------------------


def test_exact_hash_ignores_punctuation_because_it_hashes_the_folded_form():
    assert hash_exact(STORY) == hash_exact(SAME_BUT_PUNCTUATED)


def test_exact_hash_separates_different_stories():
    assert hash_exact(STORY) != hash_exact(DIFFERENT)


# --- near ⟵ FR-2.6 ----------------------------------------------------------


def test_appended_tagline_is_a_duplicate():
    """The commonest real case: the same wire copy with a syndication line
    tacked on the end."""
    assert is_near_duplicate(STORY, TAGLINE_APPENDED) is True


def test_prefixed_masthead_is_a_duplicate():
    assert is_near_duplicate(STORY, MASTHEAD_PREFIXED) is True


def test_different_story_is_not_a_duplicate():
    assert is_near_duplicate(STORY, DIFFERENT) is False


def test_substitution_is_treated_as_a_different_story():
    """Deliberate, not a miss. Syndication republishes; it does not paraphrase.
    A rewritten story merged into the same cluster would inflate IND-03's
    amplification score, so the line sits between additions and substitutions."""
    assert is_near_duplicate(STORY, ONE_WORD_SUBSTITUTED) is False
    assert jaccard(shingles(STORY), shingles(ONE_WORD_SUBSTITUTED)) < 0.85


# --- the corrected threshold ------------------------------------------------


def test_trd_hamming_threshold_of_3_would_reject_real_duplicates():
    """Regression guard for a measured spec defect.

    TRD §5.4's ≤ 3 is the standard rule for large documents. A 26-token news
    item has ~24 shingles, so one shingle moves a large share of the majority
    vote — a masthead prefix alone costs 10 bits. Left at 3, this stage finds
    nothing beyond exact hashing, and IND-03 reports no amplification when what
    it means is blind.
    """
    assert hamming(simhash(STORY), simhash(MASTHEAD_PREFIXED)) > 3
    assert hamming(simhash(STORY), simhash(MASTHEAD_PREFIXED)) <= MAX_HAMMING


def test_jaccard_is_the_decision_not_the_hamming_filter():
    """Hamming is deliberately loose, so Jaccard has to carry the decision. A
    substituted-word variant passes the Hamming filter and is rejected only by
    Jaccard — without it, edits would merge into syndication clusters."""
    assert hamming(simhash(STORY), simhash(ONE_WORD_SUBSTITUTED)) <= MAX_HAMMING
    assert is_near_duplicate(STORY, ONE_WORD_SUBSTITUTED) is False


def test_short_headlines_are_the_hard_case():
    """Documents a real limit rather than asserting it away: the shorter the
    text, the more one edit moves the fingerprint. Headline-only items are where
    near-duplicate detection is weakest, and Week 8 measures what it costs."""
    assert jaccard(shingles(HEADLINE), shingles(HEADLINE_EDIT)) < 0.85


# --- mechanics --------------------------------------------------------------


def test_bands_split_into_four_sixteen_bit_chunks():
    """`bands` is retained but unused: the pigeonhole guarantee it depends on
    only holds at Hamming ≤ 3, and the threshold is now 12. At ~700 items in a
    7-day window a scan takes microseconds and is correct as well as simpler."""
    b = bands(simhash(STORY))
    assert len(b) == 4
    assert all(0 <= chunk < 1 << 16 for chunk in b)


def test_simhash_is_deterministic():
    assert simhash(STORY) == simhash(STORY)


def test_empty_text_hashes_to_zero_rather_than_raising():
    assert simhash("") == 0
    assert shingles("") == set()


def test_short_text_falls_back_to_tokens():
    """A headline-only item is shorter than one 3-gram. It must still produce a
    fingerprint rather than nothing."""
    assert shingles("two words") == {"two", "words"}


def test_jaccard_edges():
    assert jaccard(set(), set()) == 1.0
    assert jaccard({"a"}, set()) == 0.0
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0


def test_signed_conversion_round_trips_and_preserves_hamming():
    """PostgreSQL bigint is signed and SimHash fills all 64 bits, so about half
    of all values exceed 2**63 and fail to insert. The bug looks intermittent
    because the other half store fine. Bit patterns must survive the conversion,
    and comparisons must work across the two representations."""
    for text in (STORY, MASTHEAD_PREFIXED, DIFFERENT):
        u = simhash(text)
        assert to_unsigned64(to_signed64(u)) == u
        assert -(2**63) <= to_signed64(u) < 2**63

    a, b = simhash(STORY), simhash(MASTHEAD_PREFIXED)
    assert hamming(to_signed64(a), to_signed64(b)) == hamming(a, b)
    # Mixed representations must agree too — the database returns signed while a
    # freshly computed fingerprint is unsigned.
    assert hamming(a, to_signed64(b)) == hamming(a, b)


def test_signed_conversion_handles_the_all_ones_edge():
    assert to_signed64((1 << 64) - 1) == -1
    assert to_unsigned64(-1) == (1 << 64) - 1
    assert to_signed64(0) == 0
