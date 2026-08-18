"""Cleaner tests. ⟵ TRD §5.3, SEC-13, FR-2.1/2.2/2.11"""

from __future__ import annotations

from ingestion.clean import MAX_CHARS, clean, clean_text, normalize_for_hashing, strip_html


def test_strips_tags_to_text():
    assert clean_text("<p>Hello <b>world</b></p>").cleaned_text == "Hello world"


def test_script_and_style_contents_are_removed_not_just_their_tags():
    """A bleach-style strip keeps the JavaScript between <script> tags as text,
    where it then reads as article body and gets scored as prose ⟵ SEC-13."""
    html = '<p>Real text</p><script>var evil = "payload";</script><style>.x{color:red}</style>'
    out = clean_text(html).cleaned_text
    assert out == "Real text"
    assert "payload" not in out
    assert "color:red" not in out


def test_decodes_entities():
    assert "&" in clean_text("<p>Salt &amp; pepper</p>").cleaned_text
    assert "&amp;" not in clean_text("<p>Salt &amp; pepper</p>").cleaned_text


def test_preserves_case_and_diacritics_for_the_model():
    """FR-2.2. Lowercasing is a bag-of-words reflex that destroys signal
    XLM-R's tokenizer uses — "US" and "us" are different tokens."""
    out = clean_text("<p>The US and the UN met in Genève</p>").cleaned_text
    assert "US" in out and "UN" in out
    assert "Genève" in out


def test_normalized_form_is_folded_for_hashing_only():
    r = clean_text("<p>The US met in Genève, again.</p>")
    assert r.normalized_text == "the us met in genève again"
    assert r.cleaned_text != r.normalized_text


def test_removes_bidi_overrides():
    """Bidi controls make stored text render as something other than what it
    says ⟵ TRD §14.6."""
    out = clean_text("Report\u202egnihsahp\u202c ends").cleaned_text
    assert "\u202e" not in out and "\u202c" not in out


def test_removes_zero_width_characters():
    out = clean_text("mal\u200bicious\u200d word").cleaned_text
    assert "\u200b" not in out and "\u200d" not in out


def test_collapses_whitespace():
    assert clean_text("a\n\n  b\t\tc").cleaned_text == "a b c"


def test_nfkc_runs_before_whitespace_collapse():
    """NFKC turns exotic spaces into ordinary ones, which the collapse must
    then absorb. Doing it the other way round leaves them behind."""
    assert clean_text("a\u00a0\u00a0b").cleaned_text == "a b"


def test_truncates_with_a_flag():
    r = clean_text("x" * (MAX_CHARS + 500))
    assert r.truncated is True
    assert len(r.cleaned_text) <= MAX_CHARS


def test_short_text_is_not_flagged_truncated():
    assert clean_text("short").truncated is False


def test_decodes_bytes_with_declared_charset():
    r = clean(b"<p>Caf\xe9</p>", "text/html; charset=iso-8859-1")
    assert "Café" in r.cleaned_text
    assert r.degraded is False


def test_bad_charset_falls_back_and_flags_degraded():
    """A lying charset is common and is not a reason to drop an item — but the
    degradation must be visible rather than silently entering the corpus."""
    r = clean(b"<p>\xff\xfe invalid</p>", "text/html; charset=utf-8")
    assert r.degraded is True
    assert "invalid" in r.cleaned_text


def test_unknown_charset_name_falls_back():
    r = clean(b"<p>ok</p>", "text/html; charset=not-a-real-charset")
    assert r.degraded is True


def test_normalize_for_hashing_absorbs_punctuation_differences():
    a = normalize_for_hashing("Security Council adopts resolution on Mali.")
    b = normalize_for_hashing("Security Council adopts resolution on Mali")
    assert a == b


def test_strip_html_on_plain_text_is_a_noop():
    assert strip_html("no tags here").strip() == "no tags here"
