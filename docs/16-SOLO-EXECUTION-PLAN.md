# DOC-016 — Solo Execution Plan

| | |
|---|---|
| **Status** | `[CONFIRMED]` — supersedes DOC-006 §3, §5, §6 for execution |
| **Version** | 1.0 |
| **Date** | 2026-08-13 |
| **Supersedes** | Nothing. DOC-006 remains the *designed* plan; this is the *executed* plan. |
| **Depends on** | DOC-001 (PRD), DOC-002 (TRD), DOC-006 (Implementation Plan) |

---

## 1. Why this document exists

DOC-006 schedules 16 weeks of work across six people. The project has one person.

```
DOC-006 assumes    6 people × 16 weeks   =  96 person-weeks
Actual capacity    1 person × 15 weeks   ≈  225 hours  ≈  6 person-weeks
```

That is a **16× gap in person-weeks**, or roughly **6× against a full-time single developer**. No amount of effort closes it. The plan is not "behind" — it is arithmetically unachievable, and pretending otherwise is the same class of error as ADR-001's original latency claim: a number asserted without doing the multiplication.

This document does the multiplication and cuts scope until the plan fits. It is written to be read by an examiner. A declared descope with reasons is engineering; an undeclared one is failure.

> **Nothing in DOC-001 through DOC-015 is retracted.** Those documents describe the system POLIS is *designed* as, and that design is the intellectual contribution. This document records which subset is *built* in the available time, and why each cut was chosen.

---

## 2. Capacity assumption **[TBD-17]**

| | |
|---|---|
| Hours per week | **15** (assumed — revise if wrong, every number below scales) |
| Weeks remaining | 15 (Week 1 complete) |
| Total budget | **225 hours** |
| Reserve held back | 20 h (~9%) for the unknown |
| Spendable | **205 hours** |

If the real figure is 8 h/week, cut Phase 6 to two pages and drop the fine-tune (§4, row ML). If it is 25 h/week, restore IND-03 and the Reddit adapter first — in that order.

---

## 3. What is built, and what is not

Each cut names what is lost. "Deferred" means specified in DOC-001–015 and not built; it does **not** mean the requirement was wrong.

### 3.1 Built — the solo MVP

| Area | Scope | Hours |
|---|---|---|
| Ingestion | **RSS only.** 6–8 feeds, 3 languages. SSRF guard, HTTP client, cleaner, language detection, hash + SimHash dedupe | 30 |
| Database | **8 tables** (see §5), Alembic migrations, SQLAlchemy models | 20 |
| Pipeline | Chained `pipeline_cycle`, advisory lock, 10-min tick — exactly as TRD §6.2 | 15 |
| ML | Fine-tune XLM-R on an **existing public labelled dataset**. Sentiment + hostility heads only | 35 |
| Indicators | **IND-01 (sentiment shift)** and **IND-02 (hostility rise)**. Real z-score-vs-baseline maths, real `n_min` gates | 20 |
| Alerts | Candidate → dedup → persist → review. Six severity levels, human-in-the-loop | 15 |
| Backend | 12 endpoints, single-user auth, audit log | 25 |
| Frontend | **4 pages:** Monitoring Feed, Alert Center, Alert Detail, Dashboard (1 chart + table twin) | 30 |
| Testing | Unit + integration + the 25 acceptance criteria that survive descope | 15 |
| Deploy + docs | Local demo primary, one cloud deploy attempt, FYP report | 20 |
| **Total** | | **225** |

### 3.2 Deferred — with the reason

| Deferred | Cost if built | Why it goes |
|---|---|---|
| **Manual labelling sprint (800+ items)** | 40 h+ | Highest-cost item in DOC-006 and it is pure grind. Fine-tuning an existing licensed dataset keeps the ML contribution and removes six weeks. |
| **Multi-head: disinfo + stance** | 20 h | Each head needs its own labelled data. Two heads prove the architecture; four only repeat it. `score_text` still returns all four blocks with `not_applicable` — **the contract does not change.** |
| **IND-03…IND-06** | 25 h | Two indicators demonstrate the full mechanism: baseline, z-score, `n_min` gate, severity cap. Four more are the same code with different inputs. |
| **Telegram + Reddit adapters** | 25 h | API auth, rate limits, ToS review, and a Telegram session file that is itself a credential (SEC-17). RSS is the same pipeline with none of that. |
| **Translation layer** | 15 h | A second model, its own latency budget, its own failure mode. Language is *detected* and stored; the model is multilingual, so translation was never required for scoring. |
| **RBAC: 3 roles, 25 permissions** | 15 h | Separation of duties needs two people to separate. One account, and the audit log stays — the audit log is the ethics story, the role matrix is only its enforcement. |
| **9 of 13 pages** | 35 h | Admin, model registry, source management, search, review queue. Four pages carry the demo narrative end to end. |
| **Cloud deployment as a gate** | 10 h | Free-tier RAM against a transformer was always the biggest unknown (R-8). Local demo was always the primary path — DOC-006 §6.1 says so. Cloud becomes best-effort. |

**Everything deferred stays specified.** The FYP report presents DOC-001–015 as the design and this document as the delivery, with §3.2 as the roadmap. That is a stronger submission than a half-built version of all of it.

---

## 4. The four decisions that make this work

### 4.1 Do not build a labelled dataset — fine-tune on one that exists

The single biggest change. DOC-006 spends Weeks 3–7 labelling. Instead: find a public, **licence-verified** multilingual sentiment corpus, fine-tune XLM-RoBERTa on it, and evaluate honestly on its held-out split.

What you keep: a real trained model, real metrics, a real model card, real error analysis.
What you lose: a POLIS-specific label distribution. **Declare this as a limitation** in DOC-008 — domain mismatch between the training corpus and political news is a genuine finding, and naming it scores better than hiding it.

⟵ resolves the Week 3–7 critical path. Blocks on **GOV-1/2/3** licence verification.

### 4.2 The `score_text` contract does not change

Frozen in Week 1, and it stays frozen. Disinfo and stance return `not_applicable` with the confidence floor unmet. Backend, frontend, and every contract test are untouched by the ML descope.

**This is why Week 1 built the stub first.** That decision now pays for itself.

### 4.3 Build in pipeline order, not team order

DOC-006 parallelises because six people cannot share one file. Alone, parallelism is pure overhead — context-switching between four workstreams costs more than it saves. Build one vertical slice at a time, end to end, and keep it working.

### 4.4 Ship the stub if the model slips

Already the stated fallback (DOC-006 §6.1). Alone it is more likely, so make it explicit: **if Week 9 ends without a trained model, demo on the stub, labelled as a stub, and write the shortfall into the report.** A working system with an honest stub beats a broken system with a real model.

---

## 5. Reduced schema — 8 tables

From DOC-005's 23. Dropped tables are not redesigned later; they are simply absent.

| Kept | Dropped |
|---|---|
| `sources`, `raw_content`, `clean_content` | `translations`, `content_clusters` |
| `nlp_results`, `entities`, `topics` | `model_registry` (one model — a config value) |
| `indicators`, `alerts` | `alert_reviews` → folded into `alerts` |
| `audit_log`, `users` | `roles`, `permissions`, `role_permissions`, `sessions` |

`users` keeps its Argon2id hash and the audit foreign key. Single account, real password hashing — **SEC-5 is not descoped.** Security requirements do not scale with team size.

---

## 6. Fifteen-week schedule

15 h/week. Week 1 is complete. Each week ends with something that runs.

| Wk | Focus | Ends when | h |
|---|---|---|---|
| ~~1~~ | ~~Repo, CI, stub, tokens~~ | ✅ **Done** — 6 commits, 36 tests, CI green | ~~15~~ |
| **2** | **Decisions.** TBD-1/2/3, GOV-1/2/3 licence checks, pick the ML corpus. Then `url_guard.py` + `http_client.py` | Every Week-2 TBD closed; SSRF guard tested against the blocked-range list | 15 |
| **3** | RSS adapter, cleaner, language detection, dedupe | 6 feeds parse; dedupe catches a re-post | 15 |
| **4** | 8 tables, migrations 0001–0004, models | `alembic upgrade head` clean from empty; ingest writes rows | 15 |
| **5** | `pipeline_cycle` chained end to end, on the stub | Runs unattended 24 h; advisory lock proven by a forced overlap | 15 |
| **6** | Backend: 12 endpoints, auth, audit | Login works; every mutation writes an audit row | 15 |
| **7** | Frontend: Monitoring Feed + Alert Center | Real data from the real API in the browser | 15 |
| **8** | **ML.** Fine-tune XLM-R on the chosen corpus | Checkpoint saved; metrics computed on a held-out split | 15 |
| **9** | **Real `score_text`.** Swap the stub. Model card | `tests/ml/test_score_text_contract.py` passes **unchanged** | 15 |
| **10** | IND-01, IND-02, alert rules, severity | Worked examples from PRD §8 reproduce exactly | 15 |
| **11** | Alert Detail + review flow + Dashboard chart | Alert reviewable end to end; chart has its table twin | 15 |
| **12** | **Buffer.** Cloud deploy attempt if the buffer is unspent | Slack absorbed, or deployed | 15 |
| **13** | Security pass: ASVS L1 walkthrough, injection tests, rate limit | Findings recorded in DOC-009 with real verdicts, not `NOT TESTED` | 15 |
| **14** | Tests to ≥ 70% coverage; run the acceptance criteria | DOC-013 verdict flips from RELEASE BLOCKED with evidence | 15 |
| **15** | FYP report, demo rehearsal, tag `v1.0.0` | Demo rehearsed twice with no manual DB intervention | 15 |

**Week 12 is real buffer.** It is not spare capacity to fill — it is the only thing standing between a slip and a missed submission. Protect it.

### 6.1 Solo critical path

```
W2 decisions → W3 ingest → W4 schema → W5 pipeline → W8 fine-tune
   → W9 real model → W10 indicators → W13 security → W15 demo
```

Backend (W6) and frontend (W7, W11) sit off the critical path — they build against the stub, exactly as designed. **If a week slips, slip those, never W2 or W8.**

### 6.2 Slip rules — decide now, not in the moment

| If | Then |
|---|---|
| W2 decisions slip | **Stop everything.** Nothing downstream is correct without them. |
| Fine-tune fails or overruns W9 | Ship the stub, labelled. Do not spend W10–W11 rescuing it. |
| Indicators slip past W11 | Cut IND-02. One indicator, done properly, still proves the mechanism. |
| Frontend slips | Cut the Dashboard chart. Feed + Alert Center + Detail carry the demo. |
| W12 buffer is gone by W10 | Cut IND-02 **and** the cloud deploy in the same decision. Do not cut W13 or W14. |

Security (W13) and testing (W14) are never cut. A prototype that fails its own security report is worse than a smaller prototype that passes.

---

## 7. Rules for working alone

Things that exist in DOC-006 only because six people did. Doing them alone is cargo cult.

| Do not | Do instead |
|---|---|
| Require PR review (nobody to review) | Keep the PR + CI flow, self-merge. `enforce_admins` stays off. CI is the reviewer. |
| Track directory ownership | Ignore. It solved merge conflicts that cannot occur. |
| Work four workstreams in parallel | One vertical slice per week, always in a working state. |
| Write a task ticket for every item | The §6 table is the tracker. |
| Chase 100% coverage | 70% on the paths the acceptance criteria touch. |
| Add a feature "since it's small" | Every hour spent here comes out of W12 buffer. Write it in §3.2 instead. |

Keep, because they are not team overhead:

- **CI green before merge** — the only reviewer you have
- **Secrets never in git** — gitleaks over full history
- **`[TBD]` markers** — the honesty discipline that makes the docs credible
- **Evidence markers** (`NOT RUN` / `NOT TESTED`) — never write `PASS` without a run behind it

---

## 8. What changes in the other documents

| Doc | Change | When |
|---|---|---|
| DOC-006 | §3 Team Structure → points here. §6 schedule → superseded, not deleted | Week 2 |
| DOC-001 | §7 MVP scope → add a "solo delivery subset" column | Week 2 |
| DOC-005 | 23 tables → mark the 15 unbuilt as **deferred**, keep the DDL | Week 4 |
| DOC-008 | Add a limitation: training corpus ≠ deployment domain | Week 9 |
| DOC-013 | Reduce the 25 acceptance criteria to those in scope; record which were dropped and why | Week 14 |
| Consistency report | New finding: DOC-006 team assumption vs actual capacity | Week 2 |

**No document is deleted or quietly edited.** Every change is a marked supersession with a reason.

---

## 9. Open items this document adds

| ID | Item | Owner | Due |
|---|---|---|---|
| **TBD-17** | Actual hours per week — every estimate above scales from 15 | You | Week 2 |
| **TBD-18** | Which public corpus is fine-tuned, and under what licence | You | Week 2 ⟵ blocks W8 |
| **TBD-19** | Whether cloud deployment is attempted at all | You | Week 12 |

Existing TBD-1, TBD-2, TBD-3 and GOV-1/2/3 are unchanged and still gate Week 2.

---

## 10. The honest summary

A six-person plan met a one-person team. The response is a **75% scope cut**, chosen so that what remains still demonstrates every idea the project is actually about:

- a scheduled multilingual pipeline with a proven latency budget
- a real fine-tuned multilingual model behind a frozen contract
- indicators computed from an explicit statistical definition, not a vibe
- alerts that stop at a human, by architecture

What is lost is **breadth**: fewer sources, fewer heads, fewer indicators, fewer pages. Not the argument.

A finished small system beats an unfinished large one — in the demo, in the report, and in the viva.
