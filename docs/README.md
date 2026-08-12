# POLIS Documentation

**Political Open Source Language Intelligence System** — a university Final Year Project. Not affiliated with the United Nations.

This index is the map of the full documentation package. Read `01-PRD.md` first — it is the product source of truth every other document derives from. The dependency chain is:

```
PRD → TRD → APP FLOW → UI/UX → BACKEND SCHEMA → IMPLEMENTATION PLAN
                                                        ↓
        ML/DATASET → EVALUATION → SECURITY → API → DEPLOYMENT
                                                        ↓
                          USER GUIDE → TESTING → DATA GOVERNANCE → ADR
```

Decision-status convention used throughout: **[CONFIRMED]** agreed decision · **[PROPOSED]** recommended, not ratified · **[FUTURE]** explicitly out of MVP · **[TBD]** genuinely undecided, never silently assumed.

---

## Core Documents (1–6)

| # | Document | Purpose | Owner | Source of truth for | Status | Version |
|---|---|---|---|---|---|---|
| 01 | [PRD](01-PRD.md) | Product requirements, indicator framework, **§11.1 latency budget**, success metrics, MVP scope | All | Requirements, roles, the 6 indicators, the latency derivation | Complete | 1.1 |
| 02 | [TRD](02-TRD.md) | Technical architecture, `score_text()` contract, **chained `pipeline_cycle`**, API spec | Team C + B | Component design, API endpoints, scheduler model | Complete | 1.1 |
| 03 | [App Flow](03-APP-FLOW.md) | User journeys, page specs, alert/review flows, security flows | Team D + C | Page behaviour, state machine, navigation | Complete | 1.1 |
| 04 | [UI/UX Spec](04-UI-UX-SPEC.md) | Design system, severity/colour system, wireframes, accessibility | Team D | Visual design, component inventory, chart specs | Complete | 1.0 |
| 05 | [Backend Schema](05-BACKEND-SCHEMA.md) | Database design, ER diagram, SQL DDL, migrations | Team C | Table structure, indexes, retention, security grants | Complete — **freezes Week 3** | 1.0 |
| 06 | [Implementation Plan](06-IMPLEMENTATION-PLAN.md) | 16-week schedule, phases, risk register, git workflow, **§11.1 documentation register (01–15)** | All | Task ownership, dependencies, definition of done | Complete | 1.1 |

## Extended Documents (7–15)

| # | Document | Purpose | Owner | Depends on | Status | Version |
|---|---|---|---|---|---|---|
| 07 | [ML & Dataset Spec](07-ML-DATASET-SPEC.md) | ML task scope, dataset plan, provenance, leakage prevention, model architecture | Team B | PRD §9/§10, TRD §5.5/§7 | Plan complete; **dataset sections [TBD] pending Phase 3** | 1.0 |
| 08 | [ML Evaluation & Model Card](08-ML-EVALUATION-MODEL-CARD.md) | Evidence document: model card, metrics, error analysis, acceptance | Team B | Doc 07 | Template complete; **all metrics NOT RUN** | 0.1 |
| 09 | [Security & Privacy Report](09-SECURITY-PRIVACY-REPORT.md) | Threat model, ASVS checklist, privacy controls, test results | Team C + A2 | PRD §12/§13, TRD §14 | Design complete; **all tests NOT TESTED** | 0.1 |
| 10 | [API Documentation](10-API-DOCUMENTATION.md) | All 44 endpoints, contract matrix, OpenAPI plan, code reconciliation | Team C | TRD §12 (authoritative source) | Complete; **all endpoints SPECIFIED, NOT IMPLEMENTED** | 1.0 |
| 11 | [Deployment & Operations Guide](11-DEPLOYMENT-OPERATIONS-GUIDE.md) | Local/cloud setup, env vars, DR, troubleshooting | Team C + D1 | TRD §10 | Procedure complete; **not yet executed** | 1.0 |
| 12 | [User Guide](12-USER-GUIDE.md) | Role-specific guides (Analyst/Supervisor/Admin), terminology | D1 | Flow doc, UX doc | Complete — behaviour-accurate, no screenshots yet | 1.1 |
| 13 | [Testing & QA Report](13-TESTING-QA-REPORT.md) | Test strategy, traceability, release gate | All | TRD §16, PRD §22/§23 | Template complete; **all results NOT RUN — RELEASE BLOCKED** | 0.1 |
| 14 | [Data Source & Governance](14-DATA-SOURCE-GOVERNANCE.md) | Source register, licensing, ethical safeguards | Team A | PRD §9/§13, TRD §5.1 | Categories confirmed; **specific source instances [TBD]** | 1.0 |
| 15 | [Architecture Decision Records](15-ARCHITECTURE-DECISIONS.md) | The *why* behind 15 major decisions the TRD already specifies | Team C + B | TRD (the *how*) | Complete — **4 statuses corrected to match source docs** | 1.1 |
| 16 | [Solo Execution Plan](16-SOLO-EXECUTION-PLAN.md) | The plan that is actually executed. One developer, ~225 h, ~75% scope cut with every deferral reasoned | Solo | DOC-006 (superseded §3/§5/§6) | **Confirmed — read this before DOC-006** | 1.0 |

## Supporting Files

| File | Purpose |
|---|---|
| [DOCUMENT-CONSISTENCY-REPORT.md](DOCUMENT-CONSISTENCY-REPORT.md) | **v2.0** — 20-point audit, latency verification (16.0 ≤ 20.0 min), ADR status audit, 7 findings, 21-item open tracker. Verdict: **PASS WITH FINDINGS** |

---

## How to Use This Package

| If you are... | Start with |
|---|---|
| A new developer | 01 → 02 → 06, then your team's directory in TRD §4.1 |
| An ML engineer | 07 → 08, referencing PRD §9/§10 for the contract you must not break |
| A frontend/backend engineer | 03 → 04 (frontend) or 02 → 05 → 10 (backend) |
| The project supervisor | 01 (requirements) → 13 (release gate) → `DOCUMENT-CONSISTENCY-REPORT.md` |
| An FYP evaluator | 01, then 08/09/13 for evidence of what is actually built and measured, not just planned |
| A future maintainer | 15 (why things are the way they are) → 11 (how to run it) |
| The demo operator | 11 §7 (production/demo checklist), 12 (what to say about each screen) |

## What "Complete" Means in This Package

A document marked **Complete** has a fully specified design with no unresolved ambiguity in its own scope — it does not mean the system it describes has been built, tested, or deployed. Documents 8, 9, 10 (implementation status), 11 (execution), and 13 are explicit about this: their *design* is complete while their *evidence* is honestly `NOT RUN`/`NOT TESTED`/`NOT IMPLEMENTED`, because the repository contains no application code at the time of this documentation package's authorship (confirmed: `docs/` is the only content). These documents are the reporting shells Implementation Plan Phases 1–11 will fill with real results — re-issuing them with fabricated numbers instead of running the actual work would defeat their purpose.
