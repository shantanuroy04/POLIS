# POLIS — ML Evaluation Report & Model Card

**Political Open Source Language Intelligence System**

---

## 1. Document Control

| Field | Value |
|---|---|
| Document ID | POLIS-DOC-008 |
| Version | 0.1 — **skeleton, no training run has occurred** |
| Date | 11 August 2026 |
| Status | **NOT RUN.** This document reports evidence only. No model has been trained; no evaluation has been executed. |
| Owner | Team B (ML/NLP) |
| Derives from | POLIS-DOC-007 (ML & Dataset Spec — the plan this document reports against); POLIS-PRD-001 §10 (indicators), §17 (SM-1…SM-19) |
| Update cadence | Re-issued (version bump) after every training/evaluation run — first real update expected end of Phase 3, Week 8 (Implementation Plan) |

### 1.1 How to Read This Document

This document is an **evidence document, not a design document**. Every metric field is either:

- a real measured number with its provenance (dataset version, model version, evaluation date, script), or
- explicitly marked **`NOT RUN`**.

No number in this version is fabricated. Where the prompt that generated this document set expects a metric, the honest state — "training has not started" — is recorded instead of a plausible-looking placeholder value. This is intentional and is the correct state for a document produced before Phase 3 (Weeks 2–8) executes.

---

## 2. Model Card

| Field | Value |
|---|---|
| Model name | `polis-xlmr` (working name — final `version_tag` assigned at first training run) |
| Version | **NOT RUN** — no `model_versions` row exists yet |
| Base model | `xlm-roberta-base` (planned — POLIS-DOC-007 §8) |
| Intended use | Multilingual classification (sentiment, hostility, disinformation signal, stance) and extraction (entities, topics) over publicly available political-monitoring text, as one input to the POLIS early-warning indicator engine. Output is a decision-support signal for human analysts, not an autonomous determination. |
| Out-of-scope use | Any use as a standalone truth-detection system; any use to make or trigger automated decisions; any use on private/authenticated content; any use to profile individuals; any deployment outside the POLIS FYP demonstration context |
| Languages | **[TBD]** — final demo set fixed Week 3 per POLIS-DOC-007 §4 (proposed: English, Arabic, French + 1 more) |
| Tasks | Sentiment, hostility, disinformation signal, stance (may descope), NER, topic classification — per POLIS-DOC-007 §2 |
| Training data | **NOT RUN** — see POLIS-DOC-007 §4, §5 for the planned dataset; actual composition recorded here once labelling and the split are finalised (Week 6) |
| Evaluation data | **NOT RUN** — held-out 15% test split, isolated per POLIS-DOC-007 §6 |
| Training procedure | **NOT RUN** — planned hyperparameters at POLIS-DOC-007 §8, marked [PROPOSED]/[TBD] there |
| Hardware | **NOT RUN** — planned: Google Colab / Kaggle free-tier GPU |
| Software | **NOT RUN** — planned pinned versions per TRD §4.2 |
| Limitations | See POLIS-DOC-007 §11 for the commitments; this section will report **measured** limitations once evaluation runs |
| Ethical considerations | Model output is never displayed as ground truth (PRD §10.6); disinformation label capped at indicator severity `high`, never `critical` (PRD IND-04); per-language performance is a mandatory, non-optional report field (PRD NFR-12.2) so that uneven quality across languages cannot be hidden by a pooled average |

---

## 3. Evaluation Methodology **[PROPOSED — not yet executed]**

For each task, the following will be reported once a model exists. The table below is the **template**; every cell is `NOT RUN`.

| Task | Accuracy | Precision | Recall | F1 | Macro-F1 | Weighted-F1 | Confusion matrix | Per-class | Per-language |
|---|---|---|---|---|---|---|---|---|---|
| Sentiment | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| Hostility | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| Disinformation | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| Stance (if retained) | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| NER | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — | NOT RUN | NOT RUN |
| Topics | — | NOT RUN | NOT RUN | NOT RUN | NOT RUN | — | — | NOT RUN | NOT RUN |

**Per-language reporting is mandatory** ⟵ PRD NFR-12.2, SM-6 — a pooled-only result in a future version of this document is itself a defect against the PRD, not an acceptable simplification.

---

## 4. Baselines **[PROPOSED — not yet executed]**

| Model | Purpose | Status |
|---|---|---|
| TF-IDF + LogisticRegression | The bar the transformer must clear — a transformer that does not beat this is a reportable finding, not a hidden failure (POLIS-DOC-007 §8, TRD §7.3) | NOT RUN |
| `xlm-roberta-base` fine-tuned (multi-head) | The shipped model | NOT RUN |

No improvement claim is made anywhere in this document. Document 8 v0.2+ will state the baseline and model numbers side by side, whatever they are.

---

## 5. Error Analysis **[NOT RUN]**

Planned per POLIS-DOC-007 §11 and TRD §7.3 (≥ 50 misclassified items read by hand). Categories to be populated once data exists:

| Category | Planned examples to collect | Status |
|---|---|---|
| False positives | Cases where the model over-flags (e.g. quoted hostile speech misclassified as the author's own hostility) | NOT RUN |
| False negatives | Cases where genuinely hostile/unreliable content is missed | NOT RUN |
| Ambiguous language | Sarcasm, rhetorical questions, quoted adversarial speech | NOT RUN |
| Multilingual errors | Transliteration variants, code-switching, dialectal variation | NOT RUN |
| Domain-specific failures | Political register vs the training corpora's fact-check register | NOT RUN |
| Low-confidence predictions | Items below the 0.55 confidence floor (FR-3.12) — characterised as a group, not just counted | NOT RUN |

No example text will be reproduced in this document if it contains identifiable personal information beyond a public author handle already covered under PRD PRIV-2/PRIV-3; any example used is checked against that constraint before inclusion.

---

## 6. Reproducibility **[NOT RUN]**

| Field | Value |
|---|---|
| Dataset version | NOT RUN |
| Model version | NOT RUN |
| Configuration | NOT RUN — will reference the exact config artefact saved alongside the checkpoint (POLIS-DOC-007 §9) |
| Seed | NOT RUN |
| Hardware | NOT RUN |
| Training date | NOT RUN |
| Evaluation date | NOT RUN |
| Code commit | NOT RUN — no repository has been initialised yet outside this `docs/` package |
| Evaluation script | NOT RUN — planned as `ml/evaluate.py` per TRD §4.1 |

---

## 7. Indicator Evaluation

Indicator evaluation is distinct from ML classifier evaluation — indicators are deterministic statistical formulas over stored classifications (PRD §10), not learned models, so their "evaluation" is (a) a formula-correctness check against hand-computed worked examples and (b) a real-world precision measurement once analysts start reviewing alerts (Phase 7).

### 7.1 Formula Correctness — Test Coverage Plan

| Indicator | Formula (from PRD §10) | n_min | Baseline window | Threshold | FP-risk rating | Worked example defined? | Unit test status |
|---|---|---|---|---|---|---|---|
| IND-01 Hostile Rhetoric Surge | `z = (p_cur − μ_p) / max(σ_p, 0.05)` | 15 | 14-day trailing | z ≥ 2.0 | High | Yes — PRD §10.4 (μ=0.12, σ=0.05, 38 items, 11 hostile → z=3.4, `high`) | NOT RUN — planned `test_hrs_matches_prd_worked_example` |
| IND-02 Negative Sentiment Shift | `z = (μ_s − s_cur) / max(σ_s, 0.05)` | 20 | 14-day trailing | z ≥ 2.0 | Med-High | Yes — μ_s=−0.05, σ_s=0.08, s_cur=−0.31 → z=3.25, `high` | NOT RUN |
| IND-03 Narrative Amplification | `z = (A − μ_A) / max(σ_A, 0.05)`, gated on size≥5, sources≥3 | 5 members / 3 sources | 14-day trailing | z ≥ 2.0 + gates | Very High | Yes — 14 items/7 sources/3h → A=32.7, z=6.6, `critical` | NOT RUN |
| IND-04 Disinformation Density | `z = (p_cur − μ_p) / max(σ_p, 0.05)`, capped `high` | 15 | 14-day trailing | z ≥ 2.0 | Very High | Yes — μ_p=0.08, σ_p=0.06, 31 items/8 unreliable → z=3.0, capped `high` | NOT RUN |
| IND-05 Entity Attention Spike | `z = (c_cur − μ_c) / max(σ_c, 1.0)`, capped `medium` | 10 mentions, μ_c≥3 | 14-day trailing | z ≥ 2.5 | Medium | Yes — μ_c=6, σ_c=3, c_cur=27 → z=7.0, capped `medium` | NOT RUN |
| IND-06 Multi-Signal Convergence | Weighted sum of clamped component z-scores, 2-family gate | inherited | inherited | MSC ≥ 2.5 + gate | Medium | Yes — worked example shows correct **non-firing** case (MSC=2.24 < 2.5) | NOT RUN |

**All six worked examples are already defined in PRD §10.4 and copied verbatim into TRD §16.1 as the required unit-test fixtures.** This document does not redefine them — it tracks whether the corresponding test (`tests/unit/test_indicators.py`) has been written and passes. As of this version, `alerts/indicators.py` does not exist yet (pre-Phase 4), so all six rows are `NOT RUN`.

### 7.2 Real-World Precision — Not Yet Measurable

Alert precision (`confirmed / (confirmed + rejected)`, PRD FR-7.5) requires: (1) live or replayed content, (2) the classifier deployed, (3) the indicator engine running, (4) analysts recording review decisions. None of these exist yet. This section will be populated from `GET /alerts/stats` once Phase 7 (Integration, Weeks 12–13) produces ≥ 20 reviewed alerts, per PRD §23 MVP Release Criteria #6.

| Indicator | Target precision (informal) | Measured precision | Status |
|---|---|---|---|
| IND-01…06 | No formal per-indicator target in PRD beyond overall SM-8 ≥ 0.60 | NOT RUN | Pending Phase 7 |

---

## 8. Acceptance — Mapped Against PRD Success Metrics

Every target from PRD §17 is listed. **Nothing is hidden or omitted because it has not been met** — at this stage, nothing has been *measured*, which is a different and disclosed state.

| ID | Metric | PRD target | Observed | Gap | Likely cause | Mitigation | Affects MVP release? |
|---|---|---|---|---|---|---|---|
| SM-1 | Sentiment macro-F1 | ≥ 0.70 | NOT RUN | — | — | — | Yes — blocks release until measured |
| SM-2 | Hostility macro-F1 | ≥ 0.65 | NOT RUN | — | — | — | Yes |
| SM-3 | Disinformation macro-F1 | ≥ 0.65 | NOT RUN | — | — | — | Yes |
| SM-4 | `threatening_language` precision | ≥ 0.70 | NOT RUN | — | — | — | Yes |
| SM-5 | `threatening_language` recall | ≥ 0.60 | NOT RUN | — | — | — | Yes |
| SM-6 | Worst-language macro-F1 gap vs pooled | ≤ 0.15 | NOT RUN | — | — | — | Yes — this is the bias-disclosure metric; must be reported even if it fails |
| SM-7 | NER F1 (PERSON/ORG/GPE) | ≥ 0.70 | NOT RUN | — | — | — | Yes |
| SM-8 | Alert precision (overall) | ≥ 0.60 | NOT RUN | — | — | — | Yes |
| SM-9 | Alert precision per indicator | reported for all 6 | NOT RUN | — | — | — | Yes |
| SM-10 | False-alert rate | ≤ 0.40 | NOT RUN | — | — | — | Yes |
| SM-19 | Deduplication F1 | ≥ 0.90 | NOT RUN | — | — | — | Yes (Team A, but listed here as it gates IND-03/IND-01 validity) |

**Per PRD §22/§23:** the MVP is releasable only when acceptance criteria pass and metrics are reported — not necessarily only when every target is hit. A miss with honest analysis (§5 above) is an acceptable FYP outcome under PRD's own release philosophy (PRIV-6: "false positives are expected and must be visible"). A miss that is not reported would not be.

---

## 9. Document Status Summary

| Section | Status |
|---|---|
| Model card | Skeleton complete; values pending Phase 3 |
| Evaluation methodology | Template defined; zero measurements exist |
| Baselines | Not run |
| Error analysis | Not run |
| Reproducibility record | Not run |
| Indicator formula tests | Defined in PRD/TRD; not yet implemented or executed |
| Indicator real-world precision | Not measurable until Phase 7 |
| Acceptance vs success metrics | All targets listed; zero measured |

**This document must not be cited as evidence that POLIS's ML component works.** It is the reporting shell that Phase 3 and Phase 7 will fill in. The next substantive update is expected at Implementation Plan Week 8 (real `score_text()` deployed) with a fuller update at Week 14 (post-testing).

---

*End of Document 8. Re-issue after every training/evaluation run — do not silently backfill numbers into this version.*
