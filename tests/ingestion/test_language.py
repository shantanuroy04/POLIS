"""Language detection tests. ⟵ TRD §5.3, FR-2.3, FR-2.4"""

from __future__ import annotations

import pytest

from ingestion.language import CONFIDENCE_FLOOR, detect

ARABIC = "اعتمد مجلس الأمن قرارا بشأن مالي هذا الأسبوع بعد مشاورات مطولة بين الأعضاء."
FRENCH = "Le Conseil de sécurité a adopté une résolution sur le Mali cette semaine."
ENGLISH = "The Security Council adopted a resolution on Mali this week after long talks."
SPANISH = "El Consejo de Seguridad adoptó una resolución sobre Mali esta semana tras consultas."


@pytest.mark.parametrize(("text", "code"), [(ARABIC, "ar"), (FRENCH, "fr"), (ENGLISH, "en")])
def test_detects_the_three_demo_languages(text, code):
    r = detect(text)
    assert r.code == code
    assert r.supported is True
    assert r.uncertain is False
    assert r.confidence >= CONFIDENCE_FLOOR


def test_unsupported_language_becomes_other_rather_than_a_wrong_guess():
    """The detector's candidate set is wider than the supported set on purpose.
    Restricted to ar/en/fr it would confidently call this French and poison the
    French baseline."""
    r = detect(SPANISH)
    assert r.code == "other"
    assert r.supported is False


def test_too_short_to_judge_is_undetermined_not_guessed():
    r = detect("Mali")
    assert r.code == "und"
    assert r.uncertain is True
    assert r.confidence == 0.0


def test_empty_text_is_undetermined():
    assert detect("").code == "und"
    assert detect("   ").code == "und"


def test_result_is_stable_across_calls():
    """The detector is cached; a per-call rebuild would be both slow and a
    silent source of nondeterminism."""
    assert detect(ENGLISH) == detect(ENGLISH)
