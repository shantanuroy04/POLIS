# POLIS — Status

**The only file you need to open.** Updated every session. Everything else is reference.

| | |
|---|---|
| Today | **Week 5 of 26** · target **31 Jan 2027** |
| Capacity | 1 person, ~9 h/week |
| Tests | **141 passing** (18 against real PostgreSQL), CI green |
| Repo | https://github.com/shantanuroy04/POLIS |

---

## Do this next

Three things, in order. Nothing else.

| # | Task | Why now |
|---|---|---|
| **1** | **Repositories + the ingest writer** — RawItem → `raw_content` → `processed_content` | The tables exist and nothing writes to them yet |
| **2** | **Wire dedupe to the database** — assign `cluster_id` from the 7-day window | Dedupe has never run on data that persists, so it is still unproven |
| **3** | **Decide TBD-20** — is the hostility corpus licence usable? | Gates Week 8. Deciding late costs more than deciding pessimistically |

```bash
docker start polis-db          # or the run command in tests/db/conftest.py
alembic upgrade head
```

## Done

| Week | What | Evidence |
|---|---|---|
| 1 | Repo, CI, security headers, frozen `score_text` stub, design tokens | 36 tests, 3 CI gates green |
| 2 | Decisions: languages, topics, regions, corpus. SSRF guard + guarded fetch | 73 tests |
| 3 | RSS adapter, source registry, live source checker | 86 tests, 4 feeds parsing |
| 4 | Cleaner, language detection, dedupe | 123 tests |
| 5 | 8 tables, Alembic migration, models, advisory lock | **141 tests**, 18 against real PostgreSQL |

**The whole ingestion path runs end to end on real feeds:**

```
110 items   en 47 · ar 30 · fr 32 · other 1
0 uncertain · 0 truncated · avg 718 chars cleaned
```

Feed → SSRF-guarded fetch → RSS parse → HTML stripped → NFKC normalised →
language detected → fingerprinted.

**The schema is live.** 8 tables, one migration, verified three ways: it applies
to an empty database, `alembic check` finds no drift from the models, and
downgrade-then-upgrade round-trips. CI runs a PostgreSQL service container and
fails if it is unreachable, so the 18 schema tests cannot silently skip.

> **Dedupe is not yet validated on real data.** A single poll contains no
> duplicates, because duplication shows up *across* polls and across days. It
> can only be measured once items persist — Week 5, and properly in Week 8.

## The decisions already made — do not reopen

| | |
|---|---|
| Languages | **Arabic, English, French** |
| Sources | UN News ×3 + ReliefWeb. Terms read. France 24 removed (licence forbids it), BBC held (terms unreadable) |
| Training corpus | `cardiffnlp/tweet_sentiment_multilingual`, CC BY 3.0 |
| Model | Fine-tune XLM-R. **Sentiment head certain, hostility conditional** |
| Indicators | **IND-01 and IND-02 only** |
| UI | **4 pages**: Feed, Alert Center, Alert Detail, Dashboard (1 chart) |
| Auth | Single account, Argon2id, audit log. No RBAC matrix |
| Deploy | Local demo primary; one cloud attempt in Week 21 |

---

## Open questions — 8, not 34

Everything else is closed or descoped. This table is now the **only** authoritative list.

| ID | Question | Needed by |
|---|---|---|
| **TBD-11** | Real `n_min` values, measured from actual volume | Week 8 ⟵ **highest risk** |
| **TBD-20** | Hostility corpus licence — is OffensEval's data actually usable? | end of Week 6 |
| **GOV-11** | One non-UN publisher with compatible terms | before Week 20 |
| **GOV-8** | PRD wants ≥ 8 sources; 4 are live | with GOV-11 |
| **TBD-16** | Latency budget preconditions, measured not assumed | Week 8, re-checked Week 23 |
| **TBD-10** | Does free-tier RAM hold a transformer? | Week 21 |
| **GOV-7** | Takedown-request procedure (short, write it once) | Week 12 |
| **GOV-10** | Re-verify every feed still works | Week 25 |

### The one that can actually sink the demo

**TBD-11.** Four sources yield roughly 50–100 new items a day. The indicators split that by language, by region, and by 24-hour window before comparing against a 14-day baseline. `n_min` was sized for eight sources, so it may suppress **every** indicator — the system correctly refusing to speak, and a blank demo at the same time.

Measure real volume in Weeks 5–8. If it is too thin: widen the window to 72 h, or compute at macro-region instead of subregion. **Never lower `n_min` until something fires** — that is fitting the threshold to the answer you want.

---

## Schedule

| Weeks | | Ends |
|---|---|---|
| 6 | Repositories, ingest writes rows. **Decide TBD-20** | 13 Sep |
| 7–8 | `pipeline_cycle` chained, running unattended 24 h | 27 Sep |
| 9–10 | Backend: auth, audit, 10 endpoints | 11 Oct |
| 11–12 | Frontend: Feed + Alert Center | 25 Oct |
| **13** | **Buffer — do not fill** | 1 Nov |
| 14–16 | **ML: fine-tune, evaluate, swap out the stub** | 22 Nov |
| 17–18 | IND-01, IND-02, alerts, severity | 6 Dec |
| 19–20 | Alert Detail, review flow, dashboard chart | 20 Dec |
| 21 | Cloud deploy — hard stop at week's end | 27 Dec |
| **22** | **Buffer — exam season lands here** | 3 Jan 2027 |
| 23 | Security: ASVS L1, injection, rate limit | 10 Jan |
| 24 | Tests to 70%, acceptance criteria | 17 Jan |
| 25 | Report, demo rehearsal, tag v1.0.0 | 24 Jan |
| **26** | **Submission buffer** | 31 Jan |

**~2 weeks clear of mid-February.** That gap is insurance against the faculty announcing a date early — not spare time.

---

## Rules

**On documentation.** `docs/01` through `docs/15` are **frozen design reference**. They are examiner-facing and already written. Do **not** update them week to week — that ritual costs hours and produces no system. They change only when a design decision genuinely changes, and DOC-016 records delivery.

**Update this file, and nothing else, as you work.**

**On scope.** The only list scope may grow from is DOC-016 §3.3, and not before Week 20. "It's small, I'll just add it" is how the buffer disappears.

**On working alone.** Self-merge PRs — CI is the reviewer. One vertical slice per week, always in a working state. 70% coverage on the paths the acceptance criteria touch, not 100%.

**On honesty.** Never write `PASS` without a run behind it. `NOT RUN` is a valid, correct answer. A declared limitation scores; a hidden one gets found in the viva.

---

## Which documents you will actually open, and when

18 documents exist. You will open **four** in the next two months.

### Open now

| Doc | Why |
|---|---|
| **[STATUS.md](STATUS.md)** | This file. The only one you keep current |
| **[16 Solo Plan](docs/16-SOLO-EXECUTION-PLAN.md)** | Scope, cuts, slip rules. Read §6.2 when a week goes wrong |
| **[14 Governance](docs/14-DATA-SOURCE-GOVERNANCE.md)** | Sources and their terms. Read before touching a feed |
| **[07 ML/Dataset §4–5](docs/07-ML-DATASET-SPEC.md)** | Languages, topics, regions, corpus — the label space you build against |

### Open later, once, at a specific week

Do **not** read these now. Each is needed exactly once.

| Doc | Open at | For |
|---|---|---|
| [05 Backend Schema](docs/05-BACKEND-SCHEMA.md) | **Week 5** | The DDL you write migrations from. Ignore the 15 tables you are not building |
| [10 API Documentation](docs/10-API-DOCUMENTATION.md) | **Week 9** | Endpoint contracts. Only 10 of the 44 matter |
| [04 UI/UX Spec](docs/04-UI-UX-SPEC.md) | **Week 11** | Severity system, palette, component specs |
| [03 App Flow](docs/03-APP-FLOW.md) | **Week 11, 19** | Page states. Only 4 of 13 pages matter |
| [01 PRD §10](docs/01-PRD.md) | **Week 17** | Indicator formulas and worked examples. **The single most important section in the package** |
| [02 TRD §6](docs/02-TRD.md) | **Week 7** | The chained `pipeline_cycle` design |
| [08 Model Card](docs/08-ML-EVALUATION-MODEL-CARD.md) | **Week 16** | You *fill this in*. It is a deliverable, not a reference |
| [09 Security Report](docs/09-SECURITY-PRIVACY-REPORT.md) | **Week 23** | You fill it in. Deliverable |
| [13 Testing Report](docs/13-TESTING-QA-REPORT.md) | **Week 24** | You fill it in. Holds the release gate |
| [11 Deployment Guide](docs/11-DEPLOYMENT-OPERATIONS-GUIDE.md) | **Week 21** | Cloud attempt, then the demo runbook |
| [12 User Guide](docs/12-USER-GUIDE.md) | **Week 25** | Feeds the report and the demo script |
| [15 ADRs](docs/15-ARCHITECTURE-DECISIONS.md) | **Week 25** | *Why* the architecture is what it is. Strongest material in the viva |

### Dead — never open again

| Doc | Why |
|---|---|
| ~~[06 Implementation Plan](docs/06-IMPLEMENTATION-PLAN.md)~~ | **Superseded by DOC-016.** A 16-week schedule for six people. Kept only because the report may cite the original design intent |
| ~~[Consistency Report](docs/DOCUMENT-CONSISTENCY-REPORT.md)~~ | A one-time audit that has already been performed and acted on. Historical record, not a tool |

### One that should shrink

**DOC-010** hand-writes 44 endpoint contracts. FastAPI generates OpenAPI from the code itself. From Week 9, the generated schema is the truth and DOC-010 becomes a short page pointing at `/openapi.json` — maintaining both is duplicate work with a guaranteed drift.

---

## Where things are

| | |
|---|---|
| **The plan** | [docs/16-SOLO-EXECUTION-PLAN.md](docs/16-SOLO-EXECUTION-PLAN.md) — scope, cuts, slip rules |
| Design reference (frozen) | [docs/](docs/README.md) 01–15 |
| Sources and their terms | [docs/14](docs/14-DATA-SOURCE-GOVERNANCE.md) |
| Languages, topics, regions, corpus | [docs/07 §4–5](docs/07-ML-DATASET-SPEC.md) |
| The one interface that matters | `ml/predict.py::score_text` — frozen, do not change |

```bash
pytest                              # 86 tests
python -m ingestion.check_sources   # are the feeds still alive?
uvicorn backend.main:app --reload   # http://localhost:8000/api/v1/health
```
