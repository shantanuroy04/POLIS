# DOC-016 — Solo Execution Plan

| | |
|---|---|
| **Status** | `[CONFIRMED]` — supersedes DOC-006 §3, §5, §6 for execution |
| **Version** | 1.1 — capacity corrected from 15 h/week to 9, scope cut a second time |
| **Date** | 2026-08-13 |
| **Supersedes** | Nothing. DOC-006 remains the *designed* plan; this is the *executed* plan. |
| **Depends on** | DOC-001 (PRD), DOC-002 (TRD), DOC-006 (Implementation Plan) |

---

## 1. Why this document exists

DOC-006 schedules 16 weeks of work across six people. The project has one person.

```
DOC-006 assumes    6 people × 16 weeks   =  96 person-weeks  ≈  3,840 hours
Actual capacity    1 person × 14 weeks   =  126 hours        ≈  3 person-weeks
```

That is a **30× gap**. No amount of effort closes it. The plan is not "behind" — it is arithmetically unachievable, and pretending otherwise is the same class of error as ADR-001's original latency claim: a number asserted without doing the multiplication.

> **This document has been corrected once already.** v1.0 assumed 15 h/week and cut scope by 75%. The real figure turned out to be 9, so v1.1 cuts again (§3.1.1). Both rounds are recorded; neither is quietly overwritten.

This document does the multiplication and cuts scope until the plan fits. It is written to be read by an examiner. A declared descope with reasons is engineering; an undeclared one is failure.

> **Nothing in DOC-001 through DOC-015 is retracted.** Those documents describe the system POLIS is *designed* as, and that design is the intellectual contribution. This document records which subset is *built* in the available time, and why each cut was chosen.

---

## 2. Capacity **[CONFIRMED — TBD-17 resolved 2026-08-13]**

Stated availability: **1–2 hours per day.**

| | |
|---|---|
| Hours per week | **9** (1.5 h × 6 days — the honest midpoint, not the optimistic 14) |
| Weeks remaining | 14 (Weeks 1 and 2 complete) |
| Gross budget | **126 hours** |
| Reserve held back | 18 h (~14%) — larger than v1.0's 9%, because a thinner week absorbs a bad day less well |
| **Spendable** | **108 hours** |

v1.0 of this document assumed 15 h/week and budgeted 225 hours. The real figure is **9**, so the budget is **126** — a **44% overrun against a plan that had already been cut 75%**. This section is the second correction, and the numbers in §3.1 and §6 are revised to match rather than left standing.

> **Why 9 and not 14.** "1 to 2 hours per day" almost never means seven days. Coursework, exams and illness take whole weeks, not hours. Budgeting the optimistic end of a stated range is how a plan quietly becomes fiction — the same failure this document exists to correct. If you consistently beat 9, §3.3 says what to restore first.

### 2.1 What the shortfall buys back

Two weeks of work are already banked: Week 1's scaffold and Week 2's decisions **and** its code, both delivered early. That cushion is real and is why the revision below is uncomfortable rather than fatal.

---

## 3. What is built, and what is not

Each cut names what is lost. "Deferred" means specified in DOC-001–015 and not built; it does **not** mean the requirement was wrong.

### 3.1 Built — the solo MVP **[revised for 9 h/week]**

Hours are the revised figures. The v1.0 column is kept so the size of the second cut is visible rather than quietly absorbed.

| Area | Scope | v1.0 h | **Now** |
|---|---|---|---|
| Ingestion | **RSS only.** The 8 feeds in DOC-014 §2, 3 languages. SSRF guard, HTTP client, cleaner, language detection, hash + SimHash dedupe | 30 | **18** — `url_guard` and `http_client` are already done |
| Database | **6 tables** (§5), Alembic migrations, SQLAlchemy models | 20 | **12** |
| Pipeline | Chained `pipeline_cycle`, advisory lock, 10-min tick — TRD §6.2 unchanged | 15 | **10** |
| ML | Fine-tune XLM-R, **sentiment head only**, on Colab's free GPU | 35 | **16** |
| Indicators | **IND-01 (sentiment shift)** only. Real z-score-vs-baseline, real `n_min` gate | 20 | **8** |
| Alerts | Candidate → dedup → persist → review. Six severity levels, human-in-the-loop | 15 | **10** |
| Backend | **6 endpoints**, single-user auth, audit log | 25 | **13** |
| Frontend | **2 pages:** Monitoring Feed, Alert Center (detail is a panel, not a page) | 30 | **14** |
| Testing | Unit + integration + the surviving acceptance criteria | 15 | **9** |
| Deploy + docs | **Local demo only.** FYP report | 20 | **12** |
| | | **225** | **122** |

122 against 108 spendable. **That is a 14-hour overrun, and it is stated rather than massaged away** — the honest reading is that this plan fits only if nothing goes badly wrong, which is exactly what a reserve is for. §3.3 lists what gets cut first when it does.

### 3.1.1 The second round of cuts, and what each costs

| Cut | Saves | What is lost |
|---|---|---|
| **Hostility head → conditional** | 12 h | POLIS classifies sentiment only unless TBD-20 clears. See §4.5 — this is a decision point at Week 6, not a guess made now |
| **IND-02 → deferred** | 8 h | One indicator instead of two. It still demonstrates baseline, z-score, `n_min` gate and severity cap in full — the mechanism, which is what is being argued |
| **Frontend 4 pages → 2** | 16 h | No Dashboard, no chart. Alert detail becomes a panel inside Alert Center. **A chart is the first thing restored** if hours allow (§3.3) |
| **Backend 12 → 6 endpoints** | 12 h | Only what the two pages and the pipeline actually call |
| **8 tables → 6** | 8 h | `entities` and `topics` fold into `nlp_results` as JSONB. Denormalised on purpose: nothing joins on them in a 2-page UI |
| **Cloud deploy → dropped, not "best effort"** | 8 h | Local demo only. It was always the primary path (DOC-006 §6.1), and "best effort" is how 8 hours disappear in Week 12 |

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

### 3.3 Restore order, if you beat 9 h/week

Decided now, so a good month is spent on the highest-value thing instead of whatever is nearest.

| Order | Restore | Cost | Why this order |
|---|---|---|---|
| 1 | **One chart + its table twin** on a Dashboard page | 10 h | Highest demo value per hour. A screenshot of a real indicator over time is what a report and a viva remember |
| 2 | **Hostility head + IND-02** | 20 h | Restores the second signal and the second indicator together — one without the other is wasted |
| 3 | **Alert Detail as its own page** | 6 h | The review flow reads better with room |
| 4 | **Cloud deployment** | 8 h | Last. It proves nothing the local demo does not, and free-tier RAM against a transformer is still the biggest unknown (R-8) |

**Everything deferred stays specified.** The FYP report presents DOC-001–015 as the design and this document as the delivery, with §3.2 as the roadmap. That is a stronger submission than a half-built version of all of it.

---

## 4. The five decisions that make this work

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

### 4.5 The hostility head is a decision point at Week 6, not a guess today

DOC-007 §5 records that the hostility corpus licence is **unverified** (TBD-20): the CC BY 4.0 that surfaces for OffensEval covers the paper, not the data. Separately, that corpus has **no French**, so French hostility would rest entirely on cross-lingual transfer.

Rather than guess now, the decision is scheduled:

| At end of Week 6 | Then |
|---|---|
| TBD-20 cleared — data terms read and they permit this use | Build the hostility head in Week 8 alongside sentiment. Same script, second head, ~12 h. IND-02 comes back with it |
| TBD-20 not cleared, or terms forbid it | **Sentiment only.** `score_text` returns `hostility: not_applicable`, exactly as it does for disinfo and stance. Nothing else changes — no contract edit, no backend change, no frontend change |

Either branch is a complete system, which is the whole point of the frozen contract. **Do not start the licence check in Week 7.**

---

## 5. Reduced schema — 6 tables

From DOC-005's 23. Dropped tables are not redesigned later; they are simply absent.

| Kept | Dropped |
|---|---|
| `sources`, `raw_content`, `clean_content` | `translations`, `content_clusters`, `model_registry` |
| `nlp_results` — **entities and topics fold in here as JSONB** | `entities`, `topics` as separate tables |
| `indicators`, `alerts` — `alert_reviews` folds into `alerts` | `roles`, `permissions`, `role_permissions`, `sessions` |
| `audit_log`, `users` | |

`users` keeps its Argon2id hash and the audit foreign key. Single account, real password hashing — **SEC-5 is not descoped.** Security requirements do not scale with team size.

> **Why `entities` and `topics` are JSONB and not tables.** Normalising them earns you joins and aggregate queries. A two-page UI runs neither: the feed shows an item's entities inline, and the one indicator aggregates on sentiment, not on entities. Two tables, two migrations, two model classes and their tests, for a query nothing makes. If a future page needs to ask "every item mentioning X", promote them then — the data is already captured, only its shape changes.

## 6. Schedule — 14 weeks at 9 h

Weeks 1 and 2 are complete. Each week ends with something that runs.

| Wk | Focus | Ends when | h |
|---|---|---|---|
| ~~1~~ | ~~Repo, CI, frozen stub, tokens~~ | ✅ **Done** — 73 tests, CI green | ~~—~~ |
| ~~2~~ | ~~Decisions + SSRF guard + guarded fetch~~ | ✅ **Done** — TBD-1/2/3/17/18 resolved, 8 feeds named and probed, `url_guard` + `http_client` shipped | ~~—~~ |
| **3** | RSS adapter, cleaner, language detection, dedupe. **Read the France 24 / BBC terms first (TBD-21)** | All 8 feeds parse; dedupe catches a re-post | 9 |
| **4** | 6 tables, migrations 0001–0004, models | `alembic upgrade head` clean from empty; ingest writes rows | 9 |
| **5** | `pipeline_cycle` chained end to end, on the stub | Runs unattended 24 h; advisory lock proven by a forced overlap | 9 |
| **6** | Backend: 6 endpoints, auth, audit. **Decide the hostility head (§4.5)** | Login works; every mutation writes an audit row; TBD-20 answered either way | 9 |
| **7** | Frontend: Monitoring Feed + Alert Center | Real data from the real API in the browser | 9 |
| **8** | **ML.** Fine-tune XLM-R (sentiment; + hostility only if §4.5 cleared) on Colab | Checkpoint saved; metrics on a held-out split | 9 |
| **9** | **Real `score_text`.** Swap the stub. Model card with the declared limitations | `tests/ml/test_score_text_contract.py` passes **unchanged** | 9 |
| **10** | IND-01, alert rules, severity | PRD §8 worked examples reproduce exactly | 9 |
| **11** | Alert review flow (panel), polish | Alert reviewable end to end | 9 |
| **12** | **Buffer. Do not fill it.** | Slack absorbed | 9 |
| **13** | Security pass: ASVS L1 walkthrough, injection tests, rate limit | DOC-009 carries real verdicts, not `NOT TESTED` | 9 |
| **14** | Tests to ≥ 70% coverage; run the acceptance criteria | DOC-013 verdict flips from RELEASE BLOCKED, with evidence | 9 |
| **15** | FYP report, demo rehearsal, tag `v1.0.0` | Demo rehearsed twice, no manual DB intervention | 9 |

**Week 12 is real buffer.** It is not spare capacity to fill — it is the only thing between a slip and a missed submission. At 9 h/week it matters more than it did at 15, not less.

**Two weeks are banked.** Weeks 1 and 2 both finished early. That cushion is why a 122-against-108 plan is tight rather than broken, and it is the only cushion there is — do not spend it in Week 3.

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
| IND-01 slips past W11 | There is nothing left to cut — take it from Week 12's buffer, and only from there. IND-02 was already cut in §3.1.1. |
| Frontend slips | Cut the review panel to read-only. The feed and the alert list carry the demo on their own. |
| W12 buffer is gone by W10 | Stop building. Freeze scope where it stands and spend everything left on W13 security and W14 tests. Do not cut those two. |

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

| ID | Item | Status | Due |
|---|---|---|---|
| ~~TBD-17~~ | Actual hours per week | **RESOLVED 2026-08-13 — 9 h/week.** Every estimate in §3.1 and §6 recomputed from it | closed |
| ~~TBD-18~~ | Which corpus, under what licence | **RESOLVED 2026-08-13** — `cardiffnlp/tweet_sentiment_multilingual`, CC BY 3.0 + Twitter ToS, terms read. DOC-007 §5 | closed |
| ~~TBD-19~~ | Whether cloud deployment is attempted | **RESOLVED — no.** Dropped outright in §3.1.1 rather than left as "best effort", which is how 8 hours vanish in Week 12 | closed |
| **TBD-20** | Hostility corpus licence. The CC BY 4.0 that surfaces for OffensEval covers the **paper**, not the data | **OPEN** — decision point §4.5 | **end of Week 6** |
| **TBD-21** | France 24 and BBC terms of service unread. `robots.txt` is a crawling rule, not a licence | **OPEN** — GOV-9 | **before first ingest, Week 3** |

TBD-1, TBD-2 and TBD-3 closed on 2026-08-13 — see DOC-007 §4.1–4.3.

---

## 10. The honest summary

A six-person plan met a one-person team with nine hours a week. The response is a scope cut of roughly **90%** against DOC-006, in two rounds, chosen so that what remains still demonstrates every idea the project is actually about:

- a scheduled multilingual pipeline with a proven latency budget
- a real fine-tuned multilingual model behind a frozen contract
- an indicator computed from an explicit statistical definition, not a vibe
- alerts that stop at a human, by architecture

What is lost is **breadth**: fewer heads, one indicator, two pages, no cloud. Not the argument. Every one of those is a number in a table, and each can be restored in the order §3.3 fixes if the hours turn out better than nine.

A finished small system beats an unfinished large one — in the demo, in the report, and in the viva.
