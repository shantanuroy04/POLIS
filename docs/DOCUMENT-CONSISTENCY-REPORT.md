# POLIS — Document Consistency Report

**Political Open Source Language Intelligence System**

---

> **This tracker is historical.** The live list is `STATUS.md` in the repository root — eight open items, not thirty-four. Entries below are kept as the record of what was decided and why, not as a to-do list.

## 1. Document Control

| Field | Value |
|---|---|
| Document ID | POLIS-CONSISTENCY-001 |
| Version | 2.0 (supersedes v1.0 of 11 Aug 2026) |
| Date | 12 August 2026 |
| Status | Complete — second audit performed, corrections applied, re-verified |
| Owner | Documentation package author |
| Scope | All 15 documents + README + this report |

**v2.0 changes:** v1.0 declared the package "internally consistent." That verdict was **wrong** — it missed an arithmetic error in ADR-001's latency claim and four ADRs whose status exceeded their source documents' status. Both classes of defect are corrected in this version. The v1.0 verdict is retracted, not amended.

---

## 2. Audit Result

# PASS WITH FINDINGS

Seven findings. Five corrected in this pass (F-5, F-6, F-7, F-8, F-9); four carried forward from v1.0 as low-severity documentation-hygiene items (F-1…F-4, one of which — F-4 — is now closed).

The package is **arithmetically sound and status-honest** as of this version. It is **not** claimed to be complete in the sense of describing a built system — see §6.

---

## 3. Findings

| ID | Severity | Document | Problem | Why it matters | Correction | Status |
|---|---|---|---|---|---|---|
| **F-5** | **Critical** | 15-ADR §ADR-001; propagated to 01-PRD, 02-TRD, 03-FLOW, 06-IMPL, 14-GOV | ADR-001 claimed "15-min ingest poll + 10-min score poll + 30-min indicator compute ≈ well within 20 min." **The arithmetic is false.** Four independent timers give a worst case of the *sum of intervals* (up to 80 min), not the sum of durations. NFR-1.5 was unachievable as designed. | The single most-cited NFR in the package was structurally unsatisfiable. Every downstream document that cited "≤20 min" was citing a target the architecture could not hit. An FYP evaluator checking this arithmetic would find it in under a minute. | **Execution model changed from four independent timers to one chained `pipeline_cycle` job** (stages B→C→D→E, sequential in-process calls, 10-min tick). No new infrastructure — no Kafka, Redis, Celery, or microservice. Poll interval 15→10 min. Indicator computation moved off its own timer onto the chain and scoped to touched subjects only. NFR-1.5 split into 1.5a/b/c. Full derivation added at **PRD §11.1**. | **Corrected** |
| **F-6** | **High** | 15-ADR | ADR-003 (PostgreSQL FTS) and ADR-011 (free-tier deployment topology) carried `Status: Accepted` while their source documents (PRD FR-6.4, TRD §10.1) still mark those decisions **[PROPOSED]**. | An ADR silently promoting a proposal to a ratified decision is exactly how undecided things get treated as settled. The package's own decision-status convention was being violated by the document meant to record decisions. | Both downgraded to **`Status: Proposed`** with the source-document label cited inline. | **Corrected** |
| **F-7** | **High** | 15-ADR | ADR-006 (XLM-R) conflated two decisions: base-model choice ([CONFIRMED] in PRD §5) and head topology ([PROPOSED] in TRD §7.2, open as TBD-9). ADR-007 (CPU inference) was marked flatly Accepted despite its deployment placement depending on unresolved TBD-10. | Reading ADR-006 as written would tell a developer the multi-head architecture is settled. It is not — it is a Week-7 decision. | ADR-006 → **`Partially Accepted`** (base model Accepted, head topology Proposed, TBD-9 cited). ADR-007 → **`Accepted with unresolved contingency`** (TBD-10 cited). | **Corrected** |
| **F-8** | **Medium** | 01-PRD §11 | NFR-1.3 (≤1.5 s/item ⇒ ~2,400 items/hr) and NFR-1.4 (floor ≥300 items/hr) differ by 8×. The §11.1 stage-C bound of 2.5 min for a 100-item batch requires the NFR-1.3 figure; at the NFR-1.4 floor the same batch would take 20 min and blow the entire budget. | A latency budget that silently depends on the optimistic end of an 8× measurement range is not a budget. This was discovered *while* deriving the F-5 correction and would otherwise have shipped as a hidden assumption. | Tension **disclosed explicitly** in PRD §11.1 with the mitigation stated: if Phase 3 benchmarking lands near the 300/hr floor, the batch cap drops from 100 to ~25 and the budget is re-derived. NFR-1.4's row now cross-references the tension. Folded into TBD-16. | **Corrected (disclosed, not resolved)** |
| **F-9** | **Low** | 12-USER-GUIDE §2, §3.3 | "Read public sources continuously" and "The continuous feed" implied event-streaming to a non-technical reader. | POLIS is scheduled-batch. User-facing copy implying continuous delivery sets a false expectation about how quickly an item appears. | Reworded to "on a repeating schedule (roughly every 10 minutes)" and "refreshed each time the scheduled pipeline runs… not a live stream." Added an explicit "POLIS does not deliver anything instantly" row. | **Corrected** |
| F-1 | Low | 07-ML §4 | Dataset table lists LIAR/FakeNewsNet/Kaggle as "planned sources" without repeating §5's `[TBD]` licence caveat inline. | A reader of §4 alone could assume licensing is settled. | §5 remains authoritative and correctly flags all three. Recommend an inline cross-reference at next revision. **Not release-blocking for documentation; release-blocking for actual training** per Doc 07 §5. | Open (carried from v1.0) |
| F-2 | Low | 14-GOV §2 | Source register rows read like configured sources rather than category placeholders. | Skim-readability only; §1.1 and §5 (GOV-8) state the position clearly. | No content change. Recommend an inline table-header reminder at next revision. | Open (carried from v1.0) |
| F-3 | None | 09-SEC §11 | 21 ASVS controls vs 28 PRD SEC requirements. | Apparent discrepancy for a future reader. | Explained: ASVS does not require 1:1 requirement-to-control mapping; several PRD SEC items elaborate a single ASVS control. | Closed — explained, not a defect |
| F-4 | Low | 06-IMPL §12 | Four separate `[TBD]` trackers with no master list and no cross-reference from the Implementation Plan to Docs 07–15. | A reader could miss an open item. | **Now closed** — Impl Plan §11.1 (new Documentation Deliverables Register) explicitly enumerates Docs 07–15, and §6 of this report remains the consolidated master tracker. | **Closed in v2.0** |

---

## 4. Latency Verification

The calculation the v1.0 audit failed to perform.

### 4.1 Execution Model (corrected)

```
APScheduler tick, every 10 minutes  →  pipeline_cycle  (single advisory-locked job)
    stage B  ingest_due_sources      →  writes raw_content + processed_content
    stage C  score_pending(limit=100) →  writes nlp_results
    stage D  compute_indicators(subjects touched by C only)
    stage E  evaluate_alerts(same subjects)
```

Stages are ordinary sequential Python calls inside one job — **no broker, no queue, no additional service**. Consistent with ADR-002 (modular monolith), ADR-009 (APScheduler), ADR-010 (no Redis).

### 4.2 Worst-Case Calculation

| Stage | Component | Worst case | Basis |
|---|---|---:|---|
| A | Wait for next poll cycle | 10.0 min | Poll interval, PRD FR-1.2 |
| B | Fetch + parse + clean + language + dedupe + store | 2.0 min | [PROPOSED] target, verify Phase 7 |
| C | Score pending batch (≤100 items × 1.5 s) | 2.5 min | PRD NFR-1.3 per-item p95 |
| D | Indicator computation, touched subjects only | 1.0 min | PRD NFR-1.6 (≤60 s full pass) |
| E | Alert candidate → dedup → persist | 0.5 min | [PROPOSED], verify Phase 7 |

```
NFR-1.5a  publication → visible in feed          = A + B                 = 12.0 min  ≤ 20  ✔  margin 8.0
NFR-1.5b  publication → classification visible   = A + B + C             = 14.5 min  ≤ 20  ✔  margin 5.5
NFR-1.5c  publication → alert raised and visible = A + B + C + D + E     = 16.0 min  ≤ 20  ✔  margin 4.0

WORST CASE TOTAL:  10.0 + 2.0 + 2.5 + 1.0 + 0.5  =  16.0 minutes
REQUIRED:                                              ≤ 20.0 minutes
RESULT:                                                PASS, margin 4.0 minutes (20%)
```

### 4.3 Preconditions — the calculation is conditional, and the conditions are not yet verified

| # | Precondition | If violated | Tracked as |
|---|---|---|---|
| 1 | New items per 10-min cycle ≤ 100 (scoring batch cap) | Backlog forms; 1.5b/c degrade. **1.5a still holds** — feed visibility does not depend on scoring. | TBD-16, Phase 7 |
| 2 | Measured scoring throughput near NFR-1.3 (~2,400/hr), not near the NFR-1.4 floor (300/hr) | Stage C becomes 20 min at a 100-item cap; batch cap must drop to ~25 and the budget be re-derived | TBD-16 / F-8, Phase 3 |
| 3 | Stage B completes within 2.0 min and stage E within 0.5 min | Budget shrinks proportionally; margin 4.0 min absorbs modest overrun | Phase 7 measurement |
| 4 | Cloud only: instance stays awake (uptime pinger at 10-min interval) | Scheduler does not tick; no stage runs; all three NFRs fail in the cloud environment | Doc 11 §6.1 |

**The calculation is arithmetically valid and its preconditions are stated. It is not empirically verified — no code exists to measure. Compliance is therefore *demonstrable by design*, not *demonstrated by evidence*.** Phase 7 task 7.3 is where that changes.

---

## 5. ADR Verification

### 5.1 Statuses Changed in This Audit

| ADR | v1.0 status | v2.0 status | Reason |
|---|---|---|---|
| ADR-003 PostgreSQL FTS | Accepted | **Proposed** | PRD FR-6.4 marks it **[PROPOSED]** |
| ADR-006 XLM-RoBERTa | Accepted | **Partially Accepted** | Base model [CONFIRMED]; head topology [PROPOSED] / TBD-9 |
| ADR-007 CPU inference | Accepted | **Accepted with contingency** | Placement contingent on TBD-10 |
| ADR-011 Free-tier topology | Accepted | **Proposed** | TRD §10.1 marks it **[PROPOSED]**; also contingent on TBD-10 |
| ADR-001 Scheduled batch | Accepted | Accepted *(content rewritten)* | Status correct; **arithmetic and decision content corrected** per F-5 |

### 5.2 Statuses Verified Unchanged

ADR-002, 004, 005, 008, 009, 010, 012, 013, 014, 015 — each traced to a source document marking the decision **[CONFIRMED]**. No change required.

### 5.3 ADRs Deliberately Not Written

| Open decision | Why no ADR exists |
|---|---|
| TBD-12 — JWT HS256 vs RS256 | Genuinely undecided (Week 6). An ADR would imply settlement. |
| TBD-15 — enable RLS vs application-layer RBAC only | Genuinely undecided (Week 10). Same reasoning. |

**No TBD was closed by this audit.** Writing an ADR is not a decision-making act; it records one that has already been made elsewhere.

---

## 6. Documentation Status

| Document | Status | Evidence Required |
|---|---|---|
| 01 PRD | Complete v1.1 *(§11.1 latency budget added)* | No |
| 02 TRD | Complete v1.1 *(§6.2 chained scheduler)* | No |
| 03 App Flow | Complete v1.1 *(alert-flow diagram intervals)* | No |
| 04 UI/UX Spec | Complete v1.0 | No |
| 05 Backend Schema | Complete v1.0 — freezes Week 3 | No |
| 06 Implementation Plan | Complete v1.1 *(§11.1 documentation register)* | No |
| 07 ML & Dataset Spec | Plan complete; dataset fields `[TBD]` | **Yes** — Phase 3 (Weeks 2–8) |
| 08 ML Evaluation & Model Card | Template complete; **all metrics NOT RUN** | **Yes** — Phase 3 + 7 |
| 09 Security & Privacy Report | Design complete; **all controls NOT TESTED (0 PASS claims — verified by grep)** | **Yes** — Phase 8 (Week 13) |
| 10 API Documentation | 44 endpoints **SPECIFIED, NOT IMPLEMENTED** | **Yes** — Phase 5 (Weeks 5–10) |
| 11 Deployment & Ops Guide | Procedure complete, **DOCUMENTED NOT EXECUTED**; free-tier terms marked as a dated assumption | **Yes** — Phase 1 + 10 |
| 12 User Guide | Complete v1.1 *(scheduled-batch terminology)*; behaviourally accurate | Partial — screenshots at Phase 6 |
| 13 Testing & QA Report | Template complete; **25/25 ACs NOT RUN — RELEASE BLOCKED** | **Yes** — Phase 9 (Weeks 13–14) |
| 14 Data Source & Governance | Categories confirmed; source instances `[TBD]` | **Yes** — Phase 2 (Weeks 2–5) |
| 15 Architecture Decisions | Complete v1.1 *(4 statuses corrected, ADR-001 rewritten)* | No — re-audit whenever a TBD closes |
| README.md | Complete | No |
| This report | Complete v2.0 | Re-run after Phase 9 |

---

## 7. Consolidated Open-Items Tracker

**21 open items at v2.0. As of 2026-08-13: 9 closed, 3 opened, 15 open.** Nine closures are recorded below — three are genuine resolutions (TBD-1/2/3), five are descopes under DOC-016 marked *descoped, not verified*, and one is completed work (GOV-8). **A descope is never recorded as a pass.** Three new items were opened by the same work (TBD-18 resolved, TBD-20 and TBD-21 open).

| ID | Item | Origin | Owner | Due |
|---|---|---|---|---|
| ~~TBD-1~~ | **RESOLVED 2026-08-13 — Arabic, English, French.** Doc 07 §4.1 | Doc 07 §4.1 | — | closed |
| ~~TBD-2~~ | **RESOLVED 2026-08-13 — 16 multi-label topics + `other`.** Doc 07 §4.2 | Doc 07 §4.2 | — | closed |
| ~~TBD-3/14~~ | **RESOLVED 2026-08-13 — UN M49, two levels, assigned from content not source.** Doc 07 §4.3 | Doc 07 §4.3 | — | closed |
| TBD-4 | Stance classification survival | PRD App. B / Doc 07 §2 | B1 | Week 7 |
| TBD-5 | Viable compliant X/Twitter path | PRD App. B / Doc 14 §2.1 | A1 | Week 3 |
| TBD-6/13 | Syndication collapsing list (IND-03) | PRD App. B / TRD §18 | A1 | Week 8 |
| TBD-7 | Final IND-06 component weights | PRD App. B | B2 | Week 11 |
| TBD-8 | Known-events calendar (IND-05) | PRD App. B | A1 | Week 9 |
| TBD-9 | Multi-head vs split models | PRD App. B / ADR-006 | B1 | Week 7 |
| TBD-10 | Free-tier RAM sufficiency; else precompute | TRD §18 / ADR-007, ADR-011 | C1 | Week 12 |
| TBD-11 | Final `n_min` values from measured volume | PRD App. B | A1 + B2 | Week 9 |
| TBD-12 | JWT HS256 vs RS256 | TRD §18 | C1 | Week 6 |
| TBD-15 | Enable RLS vs RBAC-only | DB §11.2 | C1 | Week 10 |
| **TBD-16** | **§11.1 latency preconditions: items/cycle ≤ 100 **and** measured throughput near NFR-1.3 not the NFR-1.4 floor** | **PRD §11.1 (F-5, F-8)** | **A1 + C1** | **Phase 3 benchmark + Phase 7 timing** |
| ~~GOV-1~~ | **CLOSED — descoped, not verified** (disinfo head cut) | Doc 14 §5 | — | closed |
| ~~GOV-2~~ | **CLOSED — descoped, not verified** | Doc 14 §5 | — | closed |
| ~~GOV-3~~ | **CLOSED — descoped, not verified** | Doc 14 §5 | — | closed |
| ~~GOV-4~~ | **CLOSED — descoped** (translation layer cut) | Doc 14 §5 | — | closed |
| GOV-5 | Confirm `robots.txt` per source | Doc 14 §5 | A1 | Weeks 2–3, ongoing |
| ~~GOV-6~~ | **CLOSED — descoped** (no Telegram adapter) | Doc 14 §5 | — | closed |
| GOV-7 | Design takedown-request procedure | Doc 14 §5 | A1 + C1 | Week 5 |
| ~~GOV-8~~ | **CLOSED — eight feeds named and probed** | Doc 14 §2 | — | closed |
| **TBD-18** | **RESOLVED 2026-08-13 — `cardiffnlp/tweet_sentiment_multilingual`, CC BY 3.0 + Twitter ToS, terms read** | Doc 07 §5 | — | closed |
| **TBD-20** | **Hostility corpus licence NOT verified.** The CC BY 4.0 found covers the SemEval *paper*, not the data | Doc 07 §5 | You | **blocks Week 8** |
| **TBD-21** | **Half closed 2026-08-13.** France 24 read → forbids collection and storage for software operation → **3 feeds removed**. BBC unread (`bbc.co.uk` blocks automated fetch) → **not ingested**. Register is now 7 UN News + ReliefWeb | Doc 14 §2.0.0, §2.0.3 | You | BBC half open |
| **GOV-11** | **Publisher concentration** — 7 of 8 feeds are UN News. Declared as a corpus limitation, not hidden | Doc 14 §2.0.2 | You | before Week 20 |

---

## 8. Full Re-Audit — 20 Checks

| # | Check | Method | Result |
|---|---|---|---|
| 1 | PRD → TRD | Traceability matrix spot-check; every TRD requirement carries a `⟵ FR/SEC/NFR` back-reference | **PASS** |
| 2 | TRD → App Flow | Flow §8.1 coverage table vs TRD §12 endpoint list | **PASS** — zero orphans either direction |
| 3 | App Flow → UX | UX §7 wireframes vs Flow §4 page specs; all 6 states present per page | **PASS** |
| 4 | TRD → Database | DB §6 DDL vs TRD §5 components; `pipeline_cycle` lock key updated to match DB advisory-lock pattern | **PASS** |
| 5 | Database → API | DB §10 API↔entity mapping vs Doc 10 §12 | **PASS** — every table reachable, every endpoint backed |
| 6 | API → Frontend | Doc 10 "Frontend consumer" column vs TRD §13.2 routes | **PASS** |
| 7 | PRD → ML | Doc 07 §2 task list vs PRD FR-3.x | **PASS** — no ML task exists that PRD does not specify |
| 8 | ML → Evaluation | Doc 08 fields vs Doc 07 spec; every PRD SM-1…SM-19 has an evaluation row | **PASS** |
| 9 | PRD → Security | Doc 09 vs PRD SEC-1…SEC-28 | **PASS** — every SEC has a control, task, or documented N/A |
| 10 | Security → Testing | Doc 13 §6 defers to Doc 09 §13 as authoritative | **PASS** — no duplicated/conflicting status |
| 11 | PRD → Governance | Doc 14 vs PRD PRIV-1…PRIV-13 | **PASS** |
| 12 | TRD → Deployment | Doc 11 §6 vs TRD §10.1; **new**: verified deployment does not contradict single-instance chained scheduler | **PASS** — sleep-vs-latency conflict now explicitly documented |
| 13 | PRD/TRD → ADR | Every ADR status vs its source document's decision label | **PASS after correction** — 4 statuses changed (§5.1) |
| 14 | Implementation Plan → all docs | Impl §11.1 register covers 01–15 + supporting | **PASS** — F-4 closed |
| 15 | All TBDs traceable | 21 items at v2.0; **re-checked 2026-08-13**: 9 closed, 3 opened, 15 open, each with origin/owner/due (§7) | **PASS** |
| 16 | No fabricated evidence | `grep -cE "\| PASS \|"` on Docs 09/13 → **0** and **0**; all metric cells `NOT RUN` | **PASS** |
| 17 | No Accepted ADR silently resolves a TBD | §5.1 corrections; §5.3 confirms no ADR written for TBD-12/TBD-15 | **PASS after correction** |
| 18 | 20-min latency mathematically demonstrable | §4.2 — 16.0 ≤ 20.0, margin 4.0, preconditions stated | **PASS after correction** |
| 19 | Scheduled-batch terminology accurate | `grep -i "real.?time\|continuous"` across all docs; all surviving uses either *disclaim* streaming or were corrected (F-9) | **PASS** |
| 20 | Documentation status matches repository state | **STALE AS WRITTEN, re-run 2026-08-13.** The v2.0 claim “repository contains only `docs/`” was true then and is false now: Weeks 1–2 added the scaffold, the frozen `score_text` stub, the SSRF guard and the guarded fetch layer — 73 tests, CI green. Docs 08/09/10/11/13 still carry NOT RUN / NOT IMPLEMENTED / NOT TESTED / NOT EXECUTED, which remains correct: no model is trained, no ASVS control is tested, no endpoint beyond `/health` exists | **PASS on re-run** — the row is corrected rather than left asserting something untrue |

---

## 9. Final Statement

**The POLIS documentation package passes this audit with findings.**

Specifically:

- **The ≤20-minute latency requirement is now mathematically demonstrable**: worst case 10.0 + 2.0 + 2.5 + 1.0 + 0.5 = **16.0 minutes against a 20.0-minute requirement**, with a 4.0-minute margin, achieved by chaining the pipeline stages within a single scheduler tick and introducing no new infrastructure. Four preconditions are stated (§4.3), two of which (TBD-16) are measurement-dependent and unverified. The claim is *demonstrable by design*, not *demonstrated by evidence* — no code exists to measure.
- **The ADR status audit passes after correction**: four ADR statuses were reduced to match their source documents (§5.1), and no ADR resolves an open TBD.
- **No fabricated evidence exists** anywhere in the package — verified by grep, not by assertion (§8 check 16).

The package is **not** claimed to be "fully internally consistent" without qualification. It is: arithmetically sound, status-honest, and traceable, with **seven findings — five corrected, two open at low severity** — and **21 open `[TBD]` items**, none of which this audit closed by assumption.

The package describes a system that has **not been built, tested, or deployed**. Documents 07–14 carry that state explicitly rather than implying readiness. Document 13's release verdict remains **RELEASE BLOCKED**, which is the correct verdict for a project at the end of Phase 0.

**Next audit:** Implementation Plan Week 14 (post-Phase 9), when Docs 08/09/10/13 have executed evidence to check and the latency budget has been measured rather than derived. This report will be re-issued at v3.0, not silently amended.

---

*Audit performed 12 August 2026 by reading all 15 documents and cross-verifying quantitative claims via the grep/find commands cited in §8. The v1.0 verdict of "internally consistent" is retracted — it was reached without performing check 18, which the correction in F-5 shows would have failed.*
