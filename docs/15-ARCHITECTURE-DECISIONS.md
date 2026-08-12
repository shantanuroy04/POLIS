# POLIS — Architecture Decision Records

**Political Open Source Language Intelligence System**

---

## 1. Document Control

| Field | Value |
|---|---|
| Document ID | POLIS-DOC-015 |
| Version | 1.0 |
| Date | 11 August 2026 |
| Status | Complete — records decisions already made in POLIS-TRD-002; introduces none new |
| Owner | Team C (Backend/DB) with Team B (ML-specific ADRs) |
| Derives from | POLIS-PRD-001, POLIS-TRD-002 (primary source of the *how*) |

### 1.1 Purpose

**The TRD explains how; this document explains why.** Every ADR here documents a decision the TRD already states as `[CONFIRMED]` or `[PROPOSED]` — this document adds the alternatives considered and the reasoning, none of which changes what the TRD specifies. Where a TRD section is the implementation detail, this ADR is the argument that led there.

---

## ADR-001

**Title:** Scheduled batch processing instead of event streaming
**Status:** Accepted
**Date:** 2026-08-11 (Phase 0)
**Decision:** POLIS processes ingestion, scoring, indicator computation, and alerting as **one chained scheduled job** (`pipeline_cycle`, APScheduler) firing every 10 minutes, not as four independent timers and not as a continuous event stream.
**Context:** Political monitoring needs signals within minutes-to-tens-of-minutes, not milliseconds. PRD NFR-1.5a/b/c requires publication-to-visible ≤ 20 minutes for each of three separately observable events (feed visibility, classification, alert).
**Options considered:** (a) Kafka/RabbitMQ event streaming with continuous consumers; (b) four independent scheduled timers; (c) one chained sequential job per tick.
**Decision rationale:** Option (b) was the original design and **is arithmetically incapable of meeting NFR-1.5c**: with independent 10/10/30/30-minute timers, an item can wait for each interval in turn, giving a worst case of 80 minutes, not 20. Chaining the stages in-process (option c) makes the worst case `poll interval + Σ stage durations = 16.0 min` — see PRD §11.1 for the full derivation. This is achieved with no additional infrastructure: the stages are ordinary sequential function calls inside one job.
**Consequences:** Simpler deployment; single point of scheduling (mitigated by an advisory lock, TRD §2.3); latency floor is bounded by the 10-minute poll interval, not real-time. A cycle that overruns its 10-minute tick causes the next tick to be skipped rather than queued (`max_instances=1`), which degrades latency observably rather than corrupting state.
**Security implications:** Fewer exposed services (no broker port) — smaller attack surface.
**Performance implications:** **Worst case A+B+C+D+E = 10.0 + 2.0 + 2.5 + 1.0 + 0.5 = 16.0 min ≤ 20 min required** (PRD §11.1). Margin 4.0 min. This holds **only while** new items per cycle ≤ the 100-item scoring batch cap — an unverified precondition tracked as TBD-16, to be measured in Phase 7. If the precondition fails, NFR-1.5a still holds (feed visibility does not depend on scoring) while 1.5b/c degrade.
**Alternatives rejected:** Kafka/RabbitMQ — no throughput requirement justifies the operational cost at this scale. Four independent timers — rejected on the arithmetic above; this is a **corrected decision**, not the original one (see `DOCUMENT-CONSISTENCY-REPORT.md` finding F-5).
**Related documents:** PRD §11.1 (authoritative latency derivation), TRD §2.1, §2.3, §6.2.

---

## ADR-002

**Title:** Modular monolith instead of microservices
**Status:** Accepted
**Date:** 2026-08-11
**Decision:** One FastAPI process hosts the API and the scheduler; module boundaries (`ingestion/`, `ml/`, `alerts/`, `backend/`) are enforced by directory ownership and import discipline, not network hops.
**Context:** Six-person team, 16 weeks, free-tier hosting that typically offers one always-on service per project.
**Options considered:** (a) Microservices per team (ingestion service, ML service, backend service); (b) modular monolith with strict internal boundaries.
**Decision rationale:** Microservices would require each team to also own deployment, inter-service auth, and network failure handling — work with no payoff at this scale and team size. A monolith with `ml/predict.py::score_text()` as the one frozen interface (PRD §9.1) gives the same team-isolation benefit without the network complexity.
**Consequences:** Faster local development (one process to run); the interface discipline that would be enforced by a network boundary must instead be enforced by code review and the frozen-contract rule (PRD §21.2).
**Security implications:** No inter-service network traffic to secure; single process means a compromise of one module has a larger blast radius than in a properly isolated microservice — accepted given the academic threat model (PRD C-10).
**Performance implications:** No network latency between modules; `score_text()` is an in-process function call.
**Alternatives rejected:** Per-team microservices — rejected specifically because free-tier hosting typically grants one service slot per project, making this architecturally forced as well as pragmatically correct.
**Related documents:** TRD §2.1, §4.1, PRD §9.1.

---

## ADR-003

**Title:** PostgreSQL full-text search instead of a separate search engine
**Status:** **Proposed** — PRD FR-6.4 still marks PostgreSQL FTS as **[PROPOSED]**. This ADR records the reasoning; it does not ratify the decision. Ratification requires the PRD label changing to [CONFIRMED].
**Date:** 2026-08-11
**Decision:** Content search (PRD FR-6.4) uses PostgreSQL's native `tsvector`/GIN indexing, not Elasticsearch/OpenSearch.
**Context:** FR-6.4 requires full-text search across original and translated text, filterable and paginated, at up to ~50k items.
**Options considered:** (a) Elasticsearch/OpenSearch as a dedicated search datastore; (b) PostgreSQL GIN full-text index.
**Decision rationale:** A second datastore means a second thing to secure, deploy, keep schema-consistent with, and back up — for a search workload well within what PostgreSQL's native FTS handles at this scale. Supabase hosts PostgreSQL for free; hosting Elasticsearch for free is not a comparable option.
**Consequences:** No relevance-tuning ecosystem (analyzers, custom scoring plugins) that Elasticsearch offers — acceptable, since POLIS's search requirement is filtered lexical search, not a ranking-critical product feature.
**Security implications:** One fewer exposed service; search queries are bound parameters into `plainto_tsquery`, never raw user syntax (SEC-11) — a control that would need re-implementing per search engine if one were added later.
**Performance implications:** GIN index meets the < 500ms target (DB §7.1) at the documented corpus size; would need revisiting only far beyond MVP scale.
**Alternatives rejected:** Elasticsearch — explicitly rejected in TRD §17.1 as adding a second datastore for a search requirement PostgreSQL already satisfies.
**Related documents:** TRD §17.1, DB §6 (`search_vector` generated column), FR-6.4.

---

## ADR-004

**Title:** React SPA for the frontend
**Status:** Accepted
**Date:** 2026-08-11
**Decision:** The frontend is a React 18 + TypeScript single-page application built with Vite, not a server-rendered framework.
**Context:** POLIS's frontend is an authenticated internal analyst dashboard, not a public content site.
**Options considered:** (a) Next.js (SSR/hybrid); (b) React SPA (Vite); (c) Vue/Svelte SPA.
**Decision rationale:** SSR exists to improve first-paint and SEO for public, unauthenticated content — neither applies to an internal dashboard behind a login. A plain SPA avoids the Node runtime SSR requires and deploys as static files to a free CDN host (Vercel). React was chosen over Vue/Svelte for team familiarity (PRD A-8) and ecosystem maturity for the specific components needed (charting, forms, data-fetching).
**Consequences:** No server-rendering complexity; every route requires a client-side auth check before rendering sensitive data (mitigated: the check is cosmetic only, TRD §13.5 — the server is the actual authority).
**Security implications:** React's default text-escaping is the primary XSS defence (SEC-14); `dangerouslySetInnerHTML` is banned repo-wide.
**Performance implications:** Vite's fast dev loop; static output serves from a CDN with no origin compute cost.
**Alternatives rejected:** Next.js — rejected because SSR benefits (SEO, public first-paint) do not apply to an authenticated internal tool, and it would introduce a Node server to operate for no corresponding gain.
**Related documents:** TRD §13.1, §17 (technology decision matrix, "Explicitly Rejected Technologies").

---

## ADR-005

**Title:** FastAPI for the backend
**Status:** Accepted
**Date:** 2026-08-11
**Decision:** The backend REST API and scheduler run on FastAPI, not Flask or Django.
**Context:** POLIS needs typed request/response validation as an actual security control (SEC-10), async support, and low framework overhead for a single backend developer to maintain.
**Options considered:** (a) Flask (manual validation); (b) Django (heavier, ORM-coupled, admin-panel overhead not needed); (c) FastAPI.
**Decision rationale:** FastAPI's Pydantic-based validation is not a convenience — it is how SEC-10 (input validation) is implemented by default rather than by discipline. Flask would require bolting on the same validation manually, which is exactly the kind of "forgot to validate this one endpoint" gap PRD's security requirements are designed to prevent. Django's ORM lock-in conflicts with the SQLAlchemy-based schema design already specified in DB §8, and its admin panel is unneeded surface area.
**Consequences:** Smaller ecosystem than Django for things POLIS doesn't need (built-in admin, built-in auth) — RBAC and auth are built explicitly instead (TRD §14.1–14.2), which is required regardless of framework given POLIS's specific role model.
**Security implications:** Validation-by-default is the core benefit; auto-generated OpenAPI docs are explicitly disabled outside local environments (SEC-19) so this convenience doesn't become a reconnaissance surface.
**Performance implications:** Async request handling; dependency-injection pattern used for RBAC checks (TRD §5.9) with no measurable overhead at POLIS's scale.
**Alternatives rejected:** Flask (validation would be manual and inconsistent); Django (ORM and admin-panel mismatch).
**Related documents:** TRD §11.2, §17.

---

## ADR-006

**Title:** XLM-RoBERTa as the multilingual classification base model
**Status:** **Partially Accepted.** The *base model* choice (`xlm-roberta-base`) is Accepted — PRD §5 names it as a confirmed stack element. The *head topology* (one shared encoder with six heads vs. split single-task models) is **Proposed**, marked [PROPOSED] in TRD §7.2 and open as TBD-9 until Week 7. This ADR must not be read as ratifying the multi-head design.
**Date:** 2026-08-11
**Decision:** All four classification tasks (sentiment, hostility, disinformation, stance) and the NER/topic heads are built on `xlm-roberta-base`, fine-tuned once, rather than per-language models.
**Context:** Multilingual capability is POLIS's core differentiator — most comparable disinformation/sentiment tooling is English-only, and SPM-relevant deployments are overwhelmingly non-English contexts (PRD §5).
**Options considered:** (a) `xlm-roberta-base` — single multilingual model; (b) per-language monolingual BERT models; (c) a hosted LLM API for classification.
**Decision rationale:** XLM-R handles ~100 languages from one fine-tune, so the team trains once instead of per-language — directly relevant given the 16-week schedule and limited GPU quota (PRD R-7). A hosted LLM API is excluded outright by the ₹0 budget constraint (PRD C-1) and would send public content to a third party, in tension with data-minimisation intent even though the content is public (PRIV-1 spirit).
**Consequences:** Larger model (1.1 GB) and slower to fine-tune than `bert-base`; must budget more Colab time (documented risk, PRD R-7).
**Security implications:** Self-hosted — no text ever leaves the system to a third-party API, which a hosted-LLM alternative could not offer without new data-handling risk.
**Performance implications:** CPU inference in production is the binding constraint this decision creates — addressed by ADR-007 (quantisation) and the multi-head design (ADR distinct from this one, TRD §7.2) rather than by choosing a smaller, weaker base model.
**Alternatives rejected:** Per-language BERT models (4× training cost for no accuracy guarantee at this data scale); hosted LLM API (budget and data-handling violation).
**Related documents:** PRD §5, §9, TRD §7.2, §7.3, §17.

---

## ADR-007

**Title:** CPU-only inference in production
**Status:** **Accepted with unresolved contingency.** CPU-only inference is Accepted (PRD C-4 forecloses GPU on budget grounds — there is no alternative to decide between). *Where* that inference runs is contingent on TBD-10: if free-tier RAM proves insufficient even after int8 quantisation, scoring moves offline and the cloud instance serves precomputed results. Unresolved until Week 12.
**Date:** 2026-08-11
**Decision:** The deployed backend runs model inference on CPU (with int8 dynamic quantisation), not GPU. GPU is used only for offline training on Colab/Kaggle.
**Context:** Free-tier hosting (Render) does not offer GPU instances; the ₹0 budget constraint rules out paid GPU inference hosting.
**Options considered:** (a) CPU inference with quantisation; (b) paid GPU inference hosting; (c) precompute scores offline entirely, serve only static results.
**Decision rationale:** Quantised XLM-R-base meets the ≤ 1.5s per-item inference target (NFR-1.3) on CPU at the batch sizes POLIS needs (≤ 300 items scored per 10-minute cycle comfortably clears NFR-1.4's 300/hr floor). This avoids introducing a paid dependency the project cannot sustain. Fully offline precomputation (option c) was rejected as the primary path because it would make the "live system" demonstration dishonest; it remains the documented fallback (TBD-10) only if free-tier RAM proves genuinely insufficient even after quantisation.
**Consequences:** Inference is slower than GPU would allow; batching (8 items/forward pass) and scheduling (every 10 minutes, not per-request) absorb this.
**Security implications:** None beyond the general model-artefact integrity concern already covered by the model registry (DB §5.4).
**Performance implications:** Directly shapes NFR-1.3/1.4 targets and the free-tier RAM risk tracked as TBD-10 (TRD §18), to be resolved empirically at Implementation Plan Week 12 rather than assumed here.
**Alternatives rejected:** Paid GPU hosting (violates PRD C-1); pure offline-only serving as the default (would misrepresent the system as live when it is not — only acceptable as a documented, disclosed fallback).
**Related documents:** TRD §7.1, §10.1, PRD NFR-1.3/1.4, TBD-10.

---

## ADR-008

**Title:** Single `score_text()` contract as the only ML↔backend interface
**Status:** Accepted
**Date:** 2026-08-11 — **frozen Week 1 per the Implementation Plan**
**Decision:** All ML output reaches the backend through exactly one pure function, `ml/predict.py::score_text(text, lang=None) -> dict`, with a schema frozen in PRD §9.1.
**Context:** Team B (ML) and Team C (backend) must work in parallel starting Week 1, but the trained model will not exist until Week 8.
**Options considered:** (a) Multiple narrow ML functions (one per task) called individually by the backend; (b) one function returning a complete result dict; (c) an ML microservice with its own API.
**Decision rationale:** A single function with a frozen schema lets Team C build the entire backend against a **stub** from Week 1 (PRD R-9), and Team D build the entire frontend against Team C's API from Week 1 — without either waiting six-plus weeks for a trained model. Multiple narrow functions would multiply the surface that must stay frozen; an ML microservice reintroduces the network-boundary cost ADR-002 already rejected.
**Consequences:** The contract is intentionally rigid — any change after Week 4 requires both team leads' sign-off and a synchronised update across PRD §9.1, TRD §5.5, and POLIS-DOC-007 §3.1 in the same PR.
**Security implications:** The function is architecturally pure (no I/O, no DB, no network at call time) — this is itself a security property, since it means the ML code path cannot be a vector for anything beyond its declared classification output.
**Performance implications:** In-process function call, zero network overhead; batching is the backend's responsibility, not the function's.
**Alternatives rejected:** ML microservice — rejected on the same grounds as ADR-002.
**Related documents:** PRD §9.1, TRD §5.5, POLIS-IMPL-006 Phase 1 task 1.12, POLIS-DOC-007 §3.

---

## ADR-009

**Title:** APScheduler instead of a distributed task queue
**Status:** Accepted
**Date:** 2026-08-11
**Decision:** All scheduled jobs (ingestion, scoring, indicator computation, alerting, retention purge) run via APScheduler inside the FastAPI process.
**Context:** POLIS needs recurring jobs on fixed intervals (15–60 min typical), not a general-purpose distributed task queue.
**Options considered:** (a) Celery + Redis/RabbitMQ; (b) cron invoking standalone scripts; (c) APScheduler in-process.
**Decision rationale:** Celery is explicitly named in PRD's original technical direction as something to avoid absent a demonstrated scalability need — none exists at POLIS's volume. Cron would work but loses application context (DB sessions, settings, logging) that in-process scheduling gets for free. APScheduler meets every timing requirement with one dependency.
**Consequences:** Single-instance limitation — jobs do not survive a process crash mid-run (mitigated by idempotent job design: unique constraints make re-runs safe, DB §6).
**Security implications:** No broker port exposed; no broker credentials to secure.
**Performance implications:** Negligible in-process overhead; `max_instances=1` per job plus a PostgreSQL advisory lock prevents double-processing (TRD §2.3).
**Alternatives rejected:** Celery+Redis (see ADR-010); cron (loses application context).
**Related documents:** PRD original technical direction ("do not introduce Celery+Redis unless a genuine scalability requirement is demonstrated"), TRD §2.3, §6.2.

---

## ADR-010

**Title:** No Redis, no message broker
**Status:** Accepted
**Date:** 2026-08-11
**Decision:** POLIS runs with zero message-broker or distributed-cache infrastructure. Rate limiting uses an in-memory store; scheduling uses APScheduler (ADR-009); there is no pub/sub layer.
**Context:** Redis is a natural companion to Celery (ADR-009) and to distributed rate limiting — POLIS uses neither pattern.
**Options considered:** (a) Redis for caching, rate-limit state, and/or a Celery broker; (b) no Redis — in-memory state where single-instance is provably sufficient.
**Decision rationale:** Every candidate Redis use case in POLIS (rate limiting via `slowapi`, job scheduling) is satisfied by a single-instance in-memory solution given the single-instance deployment (ADR-002). Adding Redis for POLIS's actual scale would be complexity with no corresponding capability gained — the definition of the over-engineering this project's constraints explicitly guard against.
**Consequences:** Rate-limit state and scheduler locks do not survive a process restart and are not shared across instances — both are documented as `# ponytail:`-style scoped limitations (TRD §14.7) with an explicit upgrade path ("move to a shared store if the deployment ever scales out") rather than silently assumed permanent.
**Security implications:** One fewer service to secure and patch.
**Performance implications:** None at POLIS's scale; the in-memory rate limiter and the PostgreSQL advisory lock both operate at negligible cost for a single free-tier instance.
**Alternatives rejected:** Redis — rejected for the same "no demonstrated scalability requirement" reasoning as Celery.
**Related documents:** TRD §14.7, §17.1 ("Explicitly Rejected Technologies").

---

## ADR-011

**Title:** Free-tier deployment topology (Vercel + Render + Supabase)
**Status:** **Proposed** — TRD §10.1 marks the hosted topology **[PROPOSED]**, and it is further contingent on TBD-10 (free-tier RAM sufficiency for the quantised model), unresolved until Week 12. The *local* deployment path within this ADR is [CONFIRMED]; the cloud topology is not.
**Date:** 2026-08-11
**Decision:** Frontend on Vercel, backend on Render, database on Supabase — all free tiers — with a fully documented and rehearsed local deployment as the primary demo path.
**Context:** ₹0 budget constraint (PRD C-1) applies to the entire stack, including hosting.
**Options considered:** (a) This three-host free-tier split; (b) a single free-tier PaaS hosting everything; (c) local-only, no cloud deployment at all.
**Decision rationale:** Each service is hosted where it is strongest for free: Vercel for static frontend CDN delivery, Render for a backend that needs an always-on-ish process (for the scheduler), Supabase for managed PostgreSQL with TLS and backups. A single combined free host was not found that offers all three properties at adequate free-tier limits. Cloud deployment is retained (not dropped to local-only) because it demonstrates the system operating as a real deployed service, which local-only would not.
**Consequences:** Three separate free-tier limitation profiles to manage (cold starts, RAM caps, connection limits) rather than one — judged worth it for the demonstration value of a real deployed system.
**Security implications:** CORS must be configured precisely across two origins (Vercel frontend, Render backend) — an explicit allowlist, never a wildcard (SEC-15).
**Performance implications:** Cold-start latency on Render is the primary risk (TRD §10.1) — mitigated by an uptime pinger and, more fundamentally, by making local deployment the primary (not backup) demo path, so this risk cannot sink the actual evaluation.
**Alternatives rejected:** Local-only (loses the "real deployed system" demonstration value); a single combined host (none found meeting all three needs at adequate free tier).
**Related documents:** TRD §10.1–§10.3, PRD R-8, A-4.

---

## ADR-012

**Title:** Human-in-the-loop alert decisions — architectural, not policy
**Status:** Accepted
**Date:** 2026-08-11
**Decision:** No POLIS code path exists that takes, recommends, or triggers any action from an alert. The pipeline terminates at "visible to a human analyst in the Alert Center."
**Context:** POLIS is explicitly a decision-support system, not an autonomous political-intelligence decision-maker (PRD, "Important Architectural Principle").
**Options considered:** (a) Alerts as pure information with no automated downstream effect (chosen); (b) alerts that could trigger a configurable webhook/notification with implied urgency; (c) alerts with a "recommended action" field.
**Decision rationale:** This is stated as a non-negotiable architectural principle in the PRD, not a feature choice weighed against alternatives on technical merit. Any automated action — even a notification implying urgency beyond what a measured z-score supports — risks POLIS being perceived as (or actually functioning as) a system that acts rather than informs, which the project's ethical framing explicitly rejects.
**Consequences:** No webhook/email delivery in MVP (FUT-1, explicitly deferred, not because it's hard, but because in-app-only keeps the human-review step un-bypassable for MVP); every alert requires an explicit analyst action to move out of `new` status.
**Security implications:** Removes an entire class of risk (a compromised or malfunctioning alert engine cannot trigger any external effect, because none exists to trigger).
**Performance implications:** None — this is a scope boundary, not a performance trade-off.
**Alternatives rejected:** Configurable automated notification/action — deferred to [FUTURE] specifically so it can be designed with its own deliberate safeguards later, not bolted on now under schedule pressure.
**Related documents:** PRD "Important Architectural Principle," FR-5.10, PRIV-5, §10.6.

---

## ADR-013

**Title:** Immutable analyst decisions
**Status:** Accepted
**Date:** 2026-08-11
**Decision:** `analyst_reviews` rows are never updated or deleted by the application. A corrected decision is a new row with `supersedes_id` set; both remain visible in history.
**Context:** Analyst decisions are the accountability record the entire system's legitimacy depends on (PRD PRIV-9, Principle 3 in DB §2).
**Options considered:** (a) Mutable reviews (a decision can be edited in place); (b) immutable, append-only reviews with an explicit supersession chain.
**Decision rationale:** A mutable decision record would let a later edit silently rewrite what an analyst originally concluded — undermining both the audit trail's evidentiary value and the alert-precision metric's honesty (a rewritten "confirmed" could hide an original "rejected" that better reflected the analyst's real-time judgment). Immutability with visible supersession preserves both the original judgment and the correction.
**Consequences:** No `PATCH`/`DELETE` route exists on `/reviews` (API §9) — this is a deliberate absence, not an oversight.
**Security implications:** A compromised session cannot retroactively alter what an analyst is on record as having decided — it can only add a new, separately audited record.
**Performance implications:** Slightly larger table growth over time (superseded rows retained) — negligible at POLIS's demo scale.
**Alternatives rejected:** Mutable reviews — rejected on accountability grounds specifically, not a technical limitation.
**Related documents:** PRD FR-7.3, AC-13, DB §5.6, §6 (`ux_review_current_*` indexes).

---

## ADR-014

**Title:** Public-source-only ingestion
**Status:** Accepted
**Date:** 2026-08-11
**Decision:** POLIS's source adapters support exactly four types — RSS/Atom, public HTML pages, public Telegram channels, public Reddit — and no adapter for any authenticated or private source exists in the codebase.
**Context:** PRD PRIV-1 states public-source-only collection as a privacy/ethics requirement.
**Options considered:** (a) Public sources only, enforced by which adapters exist (chosen); (b) public sources by policy, with authenticated-source capability present but administratively restricted.
**Decision rationale:** Enforcing this by *which code exists* rather than *which code is allowed to run* is a stronger guarantee — there is no configuration flag that could be flipped, accidentally or otherwise, to point POLIS at a private data source, because the capability to do so was never built. This is the same reasoning pattern as ADR-012 (architectural constraint, not policy).
**Consequences:** Any future [FUTURE] expansion to a new source type must pass the same "genuinely public, no individual surveillance, attributable" test documented in POLIS-DOC-014 §4 before an adapter is written.
**Security implications:** Removes an entire category of credential-management risk (no stored credentials for accessing anyone's private account).
**Performance implications:** None.
**Alternatives rejected:** Policy-only restriction with dormant capability — rejected as a weaker guarantee than not building the capability at all.
**Related documents:** PRD PRIV-1, PRIV-3, PRIV-11, TRD §4.1 (`ingestion/sources/`), POLIS-DOC-014 §2, §4.

---

## ADR-015

**Title:** No predictive claims about political events
**Status:** Accepted
**Date:** 2026-08-11
**Decision:** No indicator, alert, API response, or UI surface states or implies that POLIS predicts, forecasts, or anticipates any specific future political event, violence, or crisis. Every indicator computation is framed as a measurement against a subject's own historical baseline.
**Context:** The word "early-warning" in POLIS's own name creates a real risk of overclaiming; PRD §10.6 exists specifically to foreclose that risk in language, not just in a disclaimer.
**Options considered:** (a) Predictive language where the statistics seem to support it (e.g. "elevated risk of escalation"); (b) strictly measurement-framed language, always relative to a stated baseline, with a mandatory non-prediction clause on every alert.
**Decision rationale:** A z-score against a 14-day baseline is a statement about *how unusual recent activity is relative to recent history* — it is not, and cannot honestly be presented as, a statement about what will happen next. The six indicators' documented false-positive risks (PRD §10.4) make this doubly important: IND-03 in particular explains that its own strongest trigger pattern (rapid multi-source spread) is *also* the normal signature of legitimate wire-service syndication. Predictive language on top of a measurement this uncertain would misrepresent the system's actual capability.
**Consequences:** Every generated alert explanation ends with a fixed, non-configurable sentence: "This is a monitoring signal requiring analyst assessment; it is not a prediction of any future event." (TRD §8.1) — asserted by an automated test, not left to manual copywriting discipline.
**Security implications:** None directly, but this is a governance/reputational-risk control as significant as any technical one for a project in this problem space.
**Performance implications:** None.
**Alternatives rejected:** Predictive language calibrated to statistical confidence — rejected because even a well-calibrated confidence score does not make a prediction about *human political behaviour* honest; confidence in a measurement and confidence in a forecast are different claims, and POLIS makes only the former.
**Related documents:** PRD §10.6, FR-4.9, TRD §8.1, UX §2.1 and §8.1 (mandatory copy).

---

## 2. ADR Index

| ID | Title | Status | Source status it must match | Open item |
|---|---|---|---|---|
| ADR-001 | Chained scheduled batch instead of streaming | Accepted | TRD §2.1 [CONFIRMED] | TBD-16 (latency precondition) |
| ADR-002 | Modular monolith instead of microservices | Accepted | TRD §2.1 [CONFIRMED] | — |
| ADR-003 | PostgreSQL FTS instead of a separate search database | **Proposed** | PRD FR-6.4 **[PROPOSED]** | — |
| ADR-004 | React SPA | Accepted | PRD technical direction [CONFIRMED] | — |
| ADR-005 | FastAPI backend | Accepted | PRD technical direction [CONFIRMED] | — |
| ADR-006 | XLM-RoBERTa multilingual base model | **Partially Accepted** (base model Accepted; head topology Proposed) | PRD §5 [CONFIRMED] / TRD §7.2 **[PROPOSED]** | TBD-9 |
| ADR-007 | CPU inference in production | **Accepted with contingency** | PRD C-4 [CONFIRMED] / placement contingent | TBD-10 |
| ADR-008 | Single `score_text()` contract | Accepted | PRD §9.1 [CONFIRMED], frozen Week 1 | — |
| ADR-009 | APScheduler, not a distributed task queue | Accepted | TRD §2.3, §6.2 [CONFIRMED] | — |
| ADR-010 | No Redis, no message broker | Accepted | TRD §17.1 [CONFIRMED] | — |
| ADR-011 | Free-tier deployment topology | **Proposed** | TRD §10.1 **[PROPOSED]** | TBD-10 |
| ADR-012 | Human-in-the-loop alert decisions | Accepted | PRD PRIV-5, FR-5.10 [CONFIRMED] | — |
| ADR-013 | Immutable analyst decisions | Accepted | PRD FR-7.3 [CONFIRMED] | — |
| ADR-014 | Public-source-only ingestion | Accepted | PRD PRIV-1 [CONFIRMED] | — |
| ADR-015 | No predictive claims | Accepted | PRD §10.6 [CONFIRMED] | — |

**Status integrity rule.** An ADR's status may not exceed the status of the decision in its source document. Three ADRs (003, 006 in part, 011) were downgraded from `Accepted` to `Proposed` on 12 August 2026 because their source documents still mark those decisions `[PROPOSED]`, and ADR-007 was qualified because its deployment placement depends on TBD-10. **An ADR existing is not evidence that a decision was ratified** — it records reasoning, not authority.

**Deliberately absent ADRs.** No ADR exists for TBD-12 (JWT HS256 vs RS256) or TBD-15 (enable row-level security vs application-layer RBAC only). This is intentional: both are genuinely undecided, and writing an ADR for either would create exactly the false impression of settlement this rule exists to prevent. ADRs will be added when those decisions are actually made, at Weeks 6 and 10 respectively.

---

*End of Document 15. New ADRs are added, never inserted between existing numbers, if a future architectural decision needs recording — existing ADR numbers are permanent.*
