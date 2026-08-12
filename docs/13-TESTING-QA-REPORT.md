# POLIS — Testing & QA Report

**Political Open Source Language Intelligence System**

---

## 1. Document Control

| Field | Value |
|---|---|
| Document ID | POLIS-DOC-013 |
| Version | 0.1 — **no tests have been run; the repository contains no code** |
| Date | 11 August 2026 |
| Status | Reporting shell. Test strategy is fully specified (inherited from TRD §16); actual results are all `NOT RUN`. |
| Owner | All six team members (per Implementation Plan Phase 9) |
| Derives from | POLIS-TRD-002 §16 (testing architecture — authoritative strategy, not restated); POLIS-PRD-001 §22 (25 acceptance criteria), §17 (success metrics), §23 (MVP release criteria) |

### 1.1 Rule Followed in This Document

Per the source instruction: *"Do not fabricate results. If tests have not yet been run, write NOT RUN rather than inventing results."* Every result cell in this document is `NOT RUN`. This is the correct and expected state of a QA report produced before Implementation Plan Phase 1 has executed. This document's job is to be the **template that gets filled with real numbers** at Phase 9 (Weeks 13–14) — not to project what those numbers will be.

---

## 2. Test Strategy

Inherited in full from TRD §16 — restated here only as a checklist of what this report will cover, not redefined.

| Layer | Tool | Scope |
|---|---|---|
| Unit — backend | pytest | Services, security, validation |
| Unit — ingestion | pytest + `respx` | Adapters, cleaners, dedupe, language, URL guard |
| Unit — indicators | pytest | 4 tests × 6 indicators (worked example, n_min suppression, zero-variance baseline, severity cap) |
| Contract — ML | pytest | `score_text()` schema conformance (stub and real) |
| Integration | pytest + ephemeral Postgres | Ingest → score → indicator → alert, plus 5 failure paths |
| API | pytest + `TestClient` | Every endpoint × every role × happy/unauthorised/invalid |
| ML | pytest | Determinism, truncation flag, empty-input raise, score-sum sanity |
| Data pipeline | pytest | Dedup precision/recall, language-detection accuracy |
| Security | pytest + scripted tools | TRD §14.9 matrix |
| Frontend | Vitest + React Testing Library | Component states, API client refresh logic |
| E2E | Playwright | Full user journeys |
| Accessibility | axe-core + manual | WCAG 2.2 AA on primary screens |
| Performance | Load test scripts | NFR-1.x targets |

---

## 3. Requirements Traceability

Every PRD §22 acceptance criterion, its intended test, and its current status. Test IDs are copied from PRD §22/TRD §16, not invented here.

| Requirement | Test | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|
| AC-1 Ingestion | `test_rss_adapter` | New items stored with full metadata; repeat run stores zero duplicates | — | NOT RUN | — |
| AC-2 Source failure isolation | `test_source_isolation` | One source failing (HTTP 500) does not abort the cycle | — | NOT RUN | — |
| AC-3 SSRF defence | `test_ssrf_guard` | Fetch to `127.0.0.1`/`169.254.169.254` blocked pre-connect | — | NOT RUN | — |
| AC-4 Deduplication | `test_dedup_clustering` | 10 near-duplicate items share one `cluster_id` | — | NOT RUN | — |
| AC-5 Language detection | `test_language_accuracy` | ≥ 95% correct ISO code on demo-language fixtures | — | NOT RUN | — |
| AC-6 Classification | `test_predict_schema` | `nlp_results` row conforms exactly to §9.1 schema | — | NOT RUN | — |
| AC-7 Indicator computation | `test_indicator_scoring` | `indicator_scores` row with raw value, z, threshold, severity, confidence, evidence | — | NOT RUN | — |
| AC-8 n_min suppression | `test_indicator_below_nmin` | No alert regardless of z-score below n_min | — | NOT RUN | — |
| AC-9 Alert creation | `test_alert_creation` | Alert with explanation and ≥1 evidence item | — | NOT RUN | — |
| AC-10 Alert deduplication | `test_alert_dedup_race` | No duplicate open alert within 6h window; occurrence counter increments | — | NOT RUN | — |
| AC-11 Explainability | `test_alert_evidence_reachable` | Evidence text reachable in ≤2 clicks; formula/baseline/threshold shown | — | NOT RUN | — |
| AC-12 Review | `test_review_recording` | Decision persisted, alert status updates, audit written | — | NOT RUN | — |
| AC-13 Review immutability | `test_review_supersede` | Correction creates a new row; both retained | — | NOT RUN | — |
| AC-14 RBAC — analyst | `test_analyst_denied_admin_route` | 403 + audited denial on admin endpoint | — | NOT RUN | — |
| AC-15 RBAC — supervisor | `test_threshold_change_audited` | Threshold change succeeds, old/new/actor audited | — | NOT RUN | — |
| AC-16 Authentication | `test_login_flow` | Valid → tokens issued + audited; invalid → generic error + audited | — | NOT RUN | — |
| AC-17 Session expiry | `test_session_expiry_redirect` | 401 → login redirect with `?next=` preserved | — | NOT RUN | — |
| AC-18 Rate limiting | `test_login_rate_limit` | 7th failed attempt in 15min → 429 + audited | — | NOT RUN | — |
| AC-19 Audit immutability | `test_audit_append_only` | `UPDATE`/`DELETE` on `audit_logs` rejected by DB role | — | NOT RUN | — |
| AC-20 XSS resistance | `test_xss_render_literal` | `<script>` payload renders as literal text, zero CSP violations | — | NOT RUN | — |
| AC-21 Secrets hygiene | `gitleaks` CI scan | Zero findings at any commit | — | NOT RUN | — |
| AC-22 Accessibility | axe-core scan | Zero critical violations, full keyboard nav | — | NOT RUN | — |
| AC-23 Multilingual display | `test_translation_display` | Original + translation shown, disclaimer present, analysis on original | — | NOT RUN | — |
| AC-24 Model registry | `test_model_version_link` | Classification links to its exact model version's metrics | — | NOT RUN | — |
| AC-25 Health | `test_health_detail` | DB/model/scheduler/ingestion status reported | — | NOT RUN | — |

**25/25 NOT RUN.**

---

## 4. Test Summary

| Category | Tests | Passed | Failed | Skipped | Coverage |
|---|---:|---:|---:|---:|---:|
| Unit — backend | NOT RUN | — | — | — | — |
| Unit — ingestion | NOT RUN | — | — | — | — |
| Unit — indicators (24 planned: 4 × 6) | NOT RUN | — | — | — | — |
| Contract — ML | NOT RUN | — | — | — | — |
| Integration | NOT RUN | — | — | — | — |
| API | NOT RUN | — | — | — | — |
| ML | NOT RUN | — | — | — | — |
| Data pipeline | NOT RUN | — | — | — | — |
| Security | NOT RUN | — | — | — | — |
| Frontend | NOT RUN | — | — | — | — |
| E2E | NOT RUN | — | — | — | — |
| **Overall** | **NOT RUN** | — | — | — | **Target ≥ 70% (PRD NFR-5.1) — not yet measurable** |

No test suite exists to execute — `pytest`/`vitest`/`playwright` configuration is a Phase 1 deliverable (Implementation Plan §5, task 1.9) not yet completed.

---

## 5. Performance Testing

| Metric | PRD target | Measured | Status |
|---|---|---:|---|
| API list-endpoint response (p95) | NFR-1.2, ≤ 500ms | NOT RUN | — |
| Content-detail single round trip (p95) | NFR-1.2 | NOT RUN | — |
| Search latency (p95) | FR-6.4-derived, ≤ 500ms | NOT RUN | — |
| Ingestion cycle: item retrieval → stored (stage B) | PRD §11.1 budget, ≤ 2.0 min | NOT RUN | — |
| Publication → visible in feed (p95) | NFR-1.5a, ≤ 20 min (budgeted 12.0) | NOT RUN | — |
| Publication → classification visible (p95) | NFR-1.5b, ≤ 20 min (budgeted 14.5) | NOT RUN | — |
| Publication → alert raised (p95) | NFR-1.5c, ≤ 20 min (budgeted 16.0) | NOT RUN | — |
| Items ingested per 10-min cycle (§11.1 precondition, TBD-16) | ≤ 100 (scoring batch cap) | NOT RUN | — |
| Single-item ML inference on CPU (p95) | NFR-1.3, ≤ 1.5s | NOT RUN | — |
| Batch scoring throughput on CPU | NFR-1.4, ≥ 300 items/hr | NOT RUN | — |
| Dashboard initial render (p95) | NFR-1.1, ≤ 2.5s | NOT RUN | — |
| Indicator computation, full 14-day pass | NFR-1.6, ≤ 60s | NOT RUN | — |
| Database queries (feed page, 50k rows) | DB §7.1, < 200ms | NOT RUN | — |

**Status: NOT RUN.** No deployed instance and no load-test corpus exist. Per Implementation Plan Phase 9, task 9.13, this table is populated against a 50k-item synthetic corpus at Week 13–14.

---

## 6. Security Testing

Reference: **POLIS-DOC-009 §13** — the security test results live there as the authoritative source, not duplicated here. Summary status: **NOT TESTED** across all 14 security test areas (authentication, authorization, IDOR, SQL injection, XSS, SSRF, rate limiting, secret scan, dependency audit, error leakage, audit immutability, session lifecycle, security headers, CORS).

---

## 7. Accessibility Testing

| Check | Target (PRD NFR-10.1/10.2, AC-22) | Result |
|---|---|---|
| axe-core automated scan — 5 primary screens | Zero critical violations | NOT RUN |
| Keyboard-only traversal of primary journey (login → dashboard → alert → evidence → resolve) | Fully completable, no mouse | NOT RUN |
| Focus visibility | 2px ring on every focusable element, never removed | NOT RUN |
| Colour contrast | WCAG 2.2 AA (4.5:1 text, 3:1 non-text) | NOT RUN — palette pre-validated via the dataviz skill's script at design time (POLIS-UX-004 §6.1), but that validates the **chart palette formula**, not the rendered application |
| Chart alternatives | Every chart has a working "View as table" toggle | NOT RUN |
| Screen reader | Landmark regions, skip-link, `aria-live` on toasts, severity announced as words | NOT RUN |

---

## 8. E2E Journeys

Per the source instruction, at minimum these five, mapped to Playwright specs:

| # | Journey | Spec (planned) | Status |
|---|---|---|---|
| 1 | Login → Dashboard | `e2e/login_dashboard.spec.ts` | NOT RUN |
| 2 | Dashboard → Alert → Evidence → Review | `e2e/alert_review.spec.ts` | NOT RUN |
| 3 | Search → Content Analysis | `e2e/search_content.spec.ts` | NOT RUN |
| 4 | Admin → Source configuration | `e2e/admin_source.spec.ts` | NOT RUN |
| 5 | Supervisor → Indicator threshold change | `e2e/supervisor_threshold.spec.ts` | NOT RUN |

---

## 9. Release Gate

Per PRD §23 MVP Release Criteria, all 16 criteria must hold before POLIS is releasable for demonstration. Current state against each:

| # | Criterion | State |
|---|---|---|
| 1 | All MVP functional requirements implemented | Not started |
| 2 | All 25 acceptance criteria pass | 0/25 run |
| 3 | 72-hour unattended run | Not started |
| 4 | Model evaluation with per-language metrics | Not started (POLIS-DOC-008) |
| 5 | SM-1–SM-3 met or shortfall documented | Not started |
| 6 | ≥ 20 alerts reviewed | Not started |
| 7 | Alert precision reported | Not started |
| 8 | Backend/ingestion coverage ≥ 70% | Not measurable |
| 9 | ASVS L1 ≥ 90% | 0% (POLIS-DOC-009) |
| 10 | Zero secrets, zero high/critical CVEs | Not evaluable — no dependency manifest exists yet |
| 11 | Zero critical a11y violations | Not evaluable |
| 12 | Demo + local deployment verified | Not started |
| 13 | All 6 core documents complete and consistent | **Complete** — this is the one criterion currently met |
| 14 | User/API/ML/security/deployment docs complete | **Complete as of this document set** (Docs 7–15) — content is specification-stage, marked accordingly throughout |
| 15 | Demo script rehearsed | Not started |
| 16 | Zero open `[TBD]` items | **Not met** — see consolidated tracker in `DOCUMENT-CONSISTENCY-REPORT.md` |

### 9.1 Verdict

## **RELEASE BLOCKED**

This is the only honest verdict available: no code exists, no test has executed, and PRD §23's criteria are overwhelmingly unmet by definition at this stage of the project. This is **expected and correct** for a project at the end of Phase 0 (Requirements & Architecture) — it is not a negative finding about the documentation package itself, which is complete (criteria 13–14). The verdict will be re-issued at Implementation Plan Week 14 (Phase 9 exit) once real evidence exists, and is expected to move toward `RELEASE READY` or `CONDITIONAL` only when backed by actual passing tests — never by editing this table without the underlying evidence.

---

*End of Document 13. Re-issue with real results, in place, at the end of Implementation Plan Phase 9 (Week 14) and again before each demo rehearsal. Never backfill a NOT RUN cell without a corresponding executed test.*
