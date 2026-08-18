# DOC-016 — Solo Execution Plan

| | |
|---|---|
| **Status** | `[CONFIRMED]` — supersedes DOC-006 §3, §5, §6 for execution |
| **Version** | 1.2 — deadline corrected from 16 weeks to 6 months; the v1.1 cuts are restored |
| **Date** | 2026-08-13 |
| **Supersedes** | Nothing. DOC-006 remains the *designed* plan; this is the *executed* plan. |
| **Depends on** | DOC-001 (PRD), DOC-002 (TRD), DOC-006 (Implementation Plan) |

---

## 1. Why this document exists

DOC-006 schedules 16 weeks of work across six people. The project has one person — and, it turns out, six months rather than sixteen weeks.

```
DOC-006 assumes    6 people × 16 weeks   =  96 person-weeks  ≈  3,840 hours
Actual capacity    1 person × 24 weeks × 9 h/week            =    216 hours
```

Still an **18× gap**, so the scope cut in §3 stands. But 216 hours is not 126, and a plan built for the wrong deadline is as wrong as one built for the wrong headcount.

> **This document has now been corrected twice, in opposite directions.**
>
> | | Assumed | Reality | Effect |
> |---|---|---|---|
> | v1.0 | 6 people | 1 person | Cut ~75% |
> | v1.1 | 15 h/week | 9 h/week | Cut again, to 122 h |
> | **v1.2** | **16 weeks** | **~26 weeks** | **Restore §3.3 in full, to 176 h** |
>
> Every round is recorded. None is quietly overwritten, including the one that turned out to be too pessimistic — a plan that only ever cuts is not being corrected, it is being ratcheted.

This document does the multiplication and cuts scope until the plan fits. It is written to be read by an examiner. A declared descope with reasons is engineering; an undeclared one is failure.

> **Nothing in DOC-001 through DOC-015 is retracted.** Those documents describe the system POLIS is *designed* as, and that design is the intellectual contribution. This document records which subset is *built* in the available time, and why each cut was chosen.

---

## 2. Capacity **[CONFIRMED — TBD-17 and TBD-22 resolved 2026-08-13]**

Stated availability: **1–2 hours per day.** Stated deadline: **6 months.**

| | |
|---|---|
| Hours per week | **9** (1.5 h × 6 days — the honest midpoint, not the optimistic 14) |
| Weeks remaining | **24** (6 months ≈ 26 weeks; Weeks 1 and 2 complete) |
| Nominal submission | **mid-February 2027** ⟵ **[TBD-23]** — confirm the exact university date |
| Gross budget | **216 hours** |
| Reserve held back | 32 h (~15%), of which three are whole buffer weeks in §6 (13, 22, 26) |
| **Spendable** | **184 hours** |

> **Why 9 and not 14.** "1 to 2 hours per day" almost never means seven days. Coursework, exams and illness take whole weeks, not hours. Budgeting the optimistic end of a stated range is how a plan quietly becomes fiction. That reasoning is unchanged by the longer deadline — **more calendar, not more hours per week.**

### 2.1 What the extra ten weeks buy

They do **not** buy a bigger system. They buy back what v1.1 cut under a false deadline, and they buy slack — which at 9 h/week is worth more than features.

| | v1.0 | v1.1 | **v1.2** |
|---|---|---|---|
| Assumed weeks | 15 | 14 | **24** |
| Budget | 225 h | 126 h | **216 h** |
| Planned scope | 225 h | 122 h | **176 h** |
| Margin against spendable | 20 h | **−14 h** | **+8 h** |

v1.1 planned 122 hours against 108 spendable — a 14-hour overrun that only worked if nothing went wrong. v1.2 plans 176 against 184. **The margin is small; the three dedicated buffer weeks in §6 are the real gain.**

Weeks 1 and 2 both finished early and that cushion still stands. It is not spent here.

---

## 3. What is built, and what is not

Each cut names what is lost. "Deferred" means specified in DOC-001–015 and not built; it does **not** mean the requirement was wrong.

### 3.1 Built — the solo MVP **[revised for 24 weeks at 9 h/week]**

Both earlier columns are kept. The point of this table is that the scope moved twice and the reason for each move is legible.

| Area | Scope | v1.0 | v1.1 | **v1.2** |
|---|---|---|---|---|
| Ingestion | **RSS only.** The 8 feeds in DOC-014 §2, 3 languages. SSRF guard, HTTP client, cleaner, language detection, hash + SimHash dedupe | 30 | 18 | **18** — `url_guard` and `http_client` already done |
| Database | **8 tables** (§5), Alembic migrations, SQLAlchemy models | 20 | 12 | **16** — `entities` and `topics` normalised again |
| Pipeline | Chained `pipeline_cycle`, advisory lock, 10-min tick — TRD §6.2 unchanged | 15 | 10 | **12** |
| ML | Fine-tune XLM-R, **sentiment + hostility**, on Colab's free GPU | 35 | 16 | **26** — hostility restored, conditional on §4.5 |
| Indicators | **IND-01 and IND-02.** Real z-score-vs-baseline, real `n_min` gates | 20 | 8 | **16** |
| Alerts | Candidate → dedup → persist → review. Six severity levels, human-in-the-loop | 15 | 10 | **12** |
| Backend | **10 endpoints**, single-user auth, audit log | 25 | 13 | **18** |
| Frontend | **4 pages:** Monitoring Feed, Alert Center, Alert Detail, Dashboard with one chart + its table twin | 30 | 14 | **26** |
| Testing | Unit + integration + the surviving acceptance criteria | 15 | 9 | **12** |
| Deploy + docs | Local demo **and** one cloud deployment. FYP report | 20 | 12 | **20** |
| | | **225** | **122** | **176** |

**176 against 184 spendable — an 8-hour margin, plus three whole buffer weeks in §6.** That is the first version of this plan with real slack in it.

> The v1.2 column sums to 176, which is 54 hours more than v1.1. The five restorations in §3.1.1 account for 48 of those. The remaining 6 are spread across pipeline, backend and testing, where a four-page UI and eight tables cost slightly more to wire and cover than a two-page UI and six did. Stated rather than rounded away — this document has already been wrong twice about a number, and the fix both times was to publish the arithmetic.

### 3.1.1 What v1.2 restores, and why it is a restoration rather than growth

Every row below is an item v1.1 cut *because of the 14-week deadline*, taken back in the exact order §3.3 fixed in advance. **Nothing new was invented to fill the time** — that is how a budget increase turns into a schedule overrun.

| Restored | Cost | Was cut in v1.1 because |
|---|---|---|
| **Dashboard chart + table twin** | 10 h | §3.3 rank 1. A screenshot of a real indicator over time is what a report and a viva remember |
| **Hostility head + IND-02** | 20 h | §3.3 rank 2. Restored together, because either alone is wasted. Still gated on TBD-20 at Week 6 (§4.5) |
| **Alert Detail as its own page** | 6 h | §3.3 rank 3. The review flow reads badly crammed into a panel |
| **Cloud deployment** | 8 h | §3.3 rank 4. Now affordable, and it retires risk R-8 — free-tier RAM against a transformer — with evidence rather than a shrug |
| `entities` / `topics` back to real tables | 4 h | JSONB was a two-page-UI compromise. With four pages and a search-shaped future, the normalised form is worth the two migrations |

**Not restored, deliberately:** IND-03…IND-06, the disinfo and stance heads, Telegram and Reddit, the translation layer, the RBAC matrix, and the other nine pages. They stay in §3.2 with their original reasons. **The next thing to restore, if you run ahead, is IND-03 (~10 h)** — not a new page and not a new source.

### 3.2 Deferred — with the reason

| Deferred | Cost if built | Why it goes |
|---|---|---|
| **Manual labelling sprint (800+ items)** | 40 h+ | Highest-cost item in DOC-006 and it is pure grind. Fine-tuning an existing licensed dataset keeps the ML contribution and removes six weeks. |
| **Multi-head: disinfo + stance** | 20 h | Each head needs its own labelled data. Two heads prove the architecture; four only repeat it. `score_text` still returns all four blocks with `not_applicable` — **the contract does not change.** |
| **IND-03…IND-06** | 25 h | Two indicators demonstrate the full mechanism: baseline, z-score, `n_min` gate, severity cap. Four more are the same code with different inputs. IND-03 is first on the restore ladder (§3.3). |
| **Telegram + Reddit adapters** | 25 h | API auth, rate limits, ToS review, and a Telegram session file that is itself a credential (SEC-17). RSS is the same pipeline with none of that. |
| **Translation layer** | 15 h | A second model, its own latency budget, its own failure mode. Language is *detected* and stored; the model is multilingual, so translation was never required for scoring. |
| **RBAC: 3 roles, 25 permissions** | 15 h | Separation of duties needs two people to separate. One account, and the audit log stays — the audit log is the ethics story, the role matrix is only its enforcement. |
| **9 of 13 pages** | 35 h | Admin, model registry, source management, search, review queue. Four pages carry the demo narrative end to end; search is second on the restore ladder. |
| ~~Cloud deployment~~ | — | **Restored in v1.2.** Now a Week 21 deliverable with a hard stop: if it is not working by end of W21, R-8 is written up with the real numbers and the local demo stands ⟵ §6.2 |

### 3.3 Restore order — what is left on the ladder

v1.2 consumed ranks 1–4. What remains, if 9 h/week turns out pessimistic:

| Order | Restore | Cost | Why this order |
|---|---|---|---|
| 1 | **IND-03** | 10 h | A third indicator on data already collected. Cheapest real capability left |
| 2 | **Search page** | 12 h | The one deferred page an examiner is most likely to ask for |
| 3 | **Reddit adapter** | 12 h | A second source *type* — proves the adapter abstraction is real, not decorative |
| 4 | **Stance head** | 15 h | Last. Needs its own labelled data, and PRD TBD-4 already contemplates descoping it |

**Do not start any of these before Week 20.** Restoring scope early is how the buffer disappears; the ladder exists for a run of good weeks near the end, not for optimism in the middle.

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

## 5. Reduced schema — 8 tables

From DOC-005's 23. Dropped tables are not redesigned later; they are simply absent.

| Kept | Dropped |
|---|---|
| `sources`, `raw_content`, `clean_content` | `translations`, `content_clusters` |
| `nlp_results`, `entities`, `topics` | `model_registry` — one model, so a config value |
| `indicators`, `alerts` | `alert_reviews` → folds into `alerts` |
| `audit_log`, `users` | `roles`, `permissions`, `role_permissions`, `sessions` |

`users` keeps its Argon2id hash and the audit foreign key. Single account, real password hashing — **SEC-5 is not descoped.** Security requirements do not scale with team size or deadline.

> **`entities` and `topics` are tables again.** v1.1 folded them into `nlp_results` as JSONB, which was right for a two-page UI that never joined on them. v1.2 has four pages and the search page is first on the restore ladder, so "every item mentioning X" becomes a query someone actually runs. Normalising later means a data migration; normalising now costs two migrations and nothing else.

## 6. Schedule — 24 weeks at 9 h

Weeks 1 and 2 are complete. Each week ends with something that runs. Two weeks are pure buffer and are not to be filled.

| Wk | Focus | Ends when | h |
|---|---|---|---|
| ~~1~~ | ~~Repo, CI, frozen stub, tokens~~ | ✅ **Done** | ~~—~~ |
| ~~2~~ | ~~Decisions + SSRF guard + guarded fetch~~ | ✅ **Done** — 73 tests, CI green | ~~—~~ |
| **3** | **Read France 24 / BBC terms (TBD-21).** Then RSS adapter | All 8 feeds parse into a common item shape | 9 |
| **4** | Cleaner, NFKC, language detection, dedupe (hash + SimHash) | Dedupe catches a syndicated re-post across two feeds | 9 |
| **5** | 8 tables, migrations 0001–0004 | `alembic upgrade head` clean from empty | 9 |
| **6** | Models, repositories, ingest writes rows. **Decide the hostility head (§4.5)** | Real articles in PostgreSQL; TBD-20 answered either way | 9 |
| **7** | `pipeline_cycle` chained, advisory lock | Forced overlap proves the lock holds | 9 |
| **8** | Pipeline unattended on the stub | Runs 24 h with no intervention | 9 |
| **9** | Backend: auth, audit, 4 endpoints | Login works; every mutation writes an audit row | 9 |
| **10** | Backend: remaining 6 endpoints | Feed and alert data served from real tables | 9 |
| **11** | Frontend: Monitoring Feed | Real API data in the browser, RTL correct for Arabic | 9 |
| **12** | Frontend: Alert Center | Alert list live against the stub's scores | 9 |
| **13** | **Buffer. Do not fill it.** | Slack absorbed | 9 |
| **14** | **ML.** Dataset prep, split by cluster, training script | Split verified leak-free ⟵ TRD §7.3 | 9 |
| **15** | **ML.** Fine-tune on Colab; evaluate per language | Checkpoint saved; per-language macro-F1, never pooled-only | 9 |
| **16** | **Real `score_text`.** Swap the stub. Model card | `test_score_text_contract.py` passes **unchanged** | 9 |
| **17** | IND-01: baseline, z-score, `n_min` gate | PRD §8 worked example reproduces exactly | 9 |
| **18** | IND-02 + alert rules + severity + dedup | Alert raised, deduped, persisted | 9 |
| **19** | Alert Detail page + review flow | Alert reviewable end to end, decision audited | 9 |
| **20** | Dashboard: one chart + its table twin | Chart and table agree; palette validated ⟵ UX §6.1 | 9 |
| **21** | Cloud deployment | Reachable, or R-8 documented with real numbers | 9 |
| **22** | **Buffer. Do not fill it.** | Slack absorbed | 9 |
| **23** | Security pass: ASVS L1, injection, rate limit, SSRF re-test | DOC-009 carries real verdicts, not `NOT TESTED` | 9 |
| **24** | Tests to ≥ 70%; run the acceptance criteria | DOC-013 verdict flips from RELEASE BLOCKED, with evidence | 9 |
| **25** | FYP report, demo rehearsal, tag `v1.0.0` | Demo rehearsed twice, no manual DB intervention | 9 |
| **26** | **Submission buffer** | Submitted | 9 |

**Three weeks of slack: 13, 22, 26.** At 9 h/week a single bad fortnight costs 18 hours, which is more than any single feature in §3.1. Buffer is the feature.

**ML sits at Weeks 14–16, not Week 8.** The pipeline must be feeding real, cleaned, deduplicated text before the model is worth training against, and the stub means nothing downstream waits for it.

### 6.1 Solo critical path

```
W3-4 ingest → W5-6 schema → W7-8 pipeline → W14-15 fine-tune
   → W16 real model → W17-18 indicators → W23 security → W25 demo
```

Backend (W9–10) and frontend (W11–12, W19–20) sit **off** the critical path — they build against the stub, exactly as task 1.12 intended. **If a week slips, slip those. Never slip W6's hostility decision or W14–16.**

The chain that cannot be reordered: text must be ingested and cleaned before it is worth training against; the model must exist before indicators mean anything; indicators must exist before an alert is more than a row.

### 6.2 Slip rules — decide now, not in the moment

| If | Then |
|---|---|
| TBD-21 (France 24 / BBC terms) unresolved at W3 | **Ingest only UN News and ReliefWeb**, whose terms are read. Four feeds is enough to build against. Do not fetch a source whose terms you have not read |
| TBD-20 unanswered by end of W6 | Treat it as **not cleared**. Sentiment only, hostility returns `not_applicable`, IND-02 drops. Deciding late costs more than deciding pessimistically |
| Fine-tune fails or overruns W16 | Ship the stub, labelled as a stub. **Do not spend W17–18 rescuing it.** A working system with an honest stub beats a broken one with a real model |
| Indicators slip past W18 | Cut IND-02 first, then take from W22's buffer. IND-01 alone still proves the mechanism |
| Frontend slips | Cut the Dashboard chart, then fold Alert Detail back into a panel — in that order. Feed + Alert Center carry the demo alone |
| Cloud deploy (W21) is not working by end of W21 | **Stop.** Write R-8 up with the real numbers you hit. A documented free-tier limit is a finding; a week lost to it is not |
| Both buffer weeks gone by W20 | Freeze scope where it stands. Spend everything remaining on W23 security, W24 tests, W25 report |

Weeks 23, 24 and 25 are never cut. A prototype that fails its own security report is worse than a smaller prototype that passes, and an unwritten report fails regardless of what was built.

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
| Add a feature "since it's small" | Every hour spent here comes out of the W13/W22/W26 buffer. Write it in §3.2 instead. |

Keep, because they are not team overhead:

- **CI green before merge** — the only reviewer you have
- **Secrets never in git** — gitleaks over full history
- **`[TBD]` markers** — the honesty discipline that makes the docs credible
- **Evidence markers** (`NOT RUN` / `NOT TESTED`) — never write `PASS` without a run behind it

---

## 8. What changes in the other documents

| Doc | Change | When |
|---|---|---|
| DOC-006 | §3 Team Structure → points here. §6 schedule → superseded, not deleted | ✅ done Week 2 |
| DOC-001 | §7 MVP scope → add a "solo delivery subset" column | Week 5 |
| DOC-005 | 23 tables → mark the 15 unbuilt as **deferred**, keep the DDL | Week 5 |
| DOC-008 | Add the limitations: training corpus ≠ deployment domain, and no French hostility data | Week 16 |
| DOC-013 | Reduce the 25 acceptance criteria to those in scope; record which were dropped and why | Week 24 |
| Consistency report | New finding: DOC-006 team assumption vs actual capacity | ✅ done Week 2 |

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
| ~~TBD-22~~ | Real deadline | **RESOLVED 2026-08-13 — 6 months, ~24 weeks remaining.** v1.1 had planned against 14 | closed |
| **TBD-23** | Exact university submission date | **OPEN.** "6 months" is planned as mid-February 2027. A schedule built on an approximate deadline is the same defect as one built on an approximate headcount | **Week 3** |

TBD-1, TBD-2 and TBD-3 closed on 2026-08-13 — see DOC-007 §4.1–4.3.

---

## 10. The honest summary

A six-person, sixteen-week plan met one person with nine hours a week and six months. The response is a scope cut of roughly **85%** against DOC-006 — cut twice, then partly restored once the real deadline was known — chosen so that what remains still demonstrates every idea the project is actually about:

- a scheduled multilingual pipeline with a proven latency budget
- a real fine-tuned multilingual model behind a frozen contract
- indicators computed from an explicit statistical definition, not a vibe
- alerts that stop at a human, by architecture

What is lost is **breadth**: two heads instead of four, two indicators instead of six, four pages instead of thirteen, one source type instead of three. Not the argument. Every one of those is a number in a table with a reason beside it, and §3.3 says which comes back first.

The plan has now been wrong twice — once about the team, once about the deadline — and corrected both times against evidence rather than defended. That is the habit worth keeping for the remaining 24 weeks.

A finished small system beats an unfinished large one — in the demo, in the report, and in the viva.
