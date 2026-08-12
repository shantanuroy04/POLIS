# POLIS — API Documentation

**Political Open Source Language Intelligence System**

---

## 1. Document Control

| Field | Value |
|---|---|
| Document ID | POLIS-DOC-010 |
| Version | 1.0 |
| Date | 11 August 2026 |
| Status | Draft — **specification only; no FastAPI application exists yet to verify against** |
| Owner | Team C (Backend/DB) |
| Derives from | POLIS-TRD-002 §12 (authoritative endpoint list); POLIS-FLOW-003 §8 (page↔API mapping); POLIS-DB-005 §10 (API↔entity mapping) |
| Base path | `/api/v1` |

### 1.1 Provenance Rule

**Every endpoint below is copied from TRD §12, not re-derived.** This document adds operational detail (worked request/response examples, consolidated error catalogue) but introduces zero new endpoints and drops none. Where this document and TRD §12 could ever disagree, TRD §12 is authoritative and the disagreement is a defect to be logged in `DOCUMENT-CONSISTENCY-REPORT.md`, not silently resolved here.

### 1.2 Implementation Status Disclosure

**No backend code exists in this repository yet** (confirmed: the repository contains only `docs/` at time of writing — pre-Phase-1 of the Implementation Plan). Every endpoint in this document is therefore `SPECIFIED, NOT IMPLEMENTED`. This document does not claim otherwise. Once `backend/main.py` and its routers exist, this document's §12 "Code Reconciliation" section is where implemented-vs-documented drift gets tracked.

---

## 2. Conventions

| Convention | Detail |
|---|---|
| Format | JSON, `Content-Type: application/json` |
| Time | ISO-8601 UTC, e.g. `2026-08-11T12:00:00Z` |
| Auth | `Authorization: Bearer <access_token>` header, plus an `HttpOnly` refresh cookie scoped to `/api/v1/auth` |
| Errors | `{"detail": "...", "request_id": "<uuid>"}`; validation errors: `{"detail": [...], "request_id": "<uuid>"}` |
| Pagination | `Page[T]` envelope: `{items, page, size, total, pages, has_next, has_prev}`; `size` default 25, max 100, server-clamped |
| Standard status codes | `400` malformed · `401` unauthenticated · `403` unauthorised · `404` not found · `409` conflict · `422` validation · `429` rate limited · `500` server error |

---

## 3. Authentication

| Method | Path | Auth | Request | Response | Status codes | Rate limit | Audit | DB | Frontend consumer |
|---|---|---|---|---|---|---|---|---|---|
| POST | `/auth/login` | none | `{email, password}` | `{access_token, token_type, expires_in, user}` + refresh cookie | 200, 401, 429 | 5/15min per account+IP | login_success / login_failed / rate_limited | `users`, `refresh_tokens` (insert) | Login page |
| POST | `/auth/refresh` | refresh cookie | none | `{access_token, ...}` + rotated cookie | 200, 401 | 30/hr per user | refresh (implicit) / refresh_reuse_detected | `refresh_tokens` (rotate) | Axios interceptor (silent) |
| POST | `/auth/logout` | bearer | none | 204 | 204, 401 | 30/hr | logout | `refresh_tokens` (revoke) | Header logout |
| GET | `/auth/me` | bearer | — | `{id, name, email, role, permissions[]}` | 200, 401 | 100/min | none (read) | `users`, `role_permissions` | Auth context bootstrap |
| POST | `/auth/change-password` | bearer | `{current, new}` | 204 | 204, 401, 422 | 5/hr | password_changed | `users` (update), `refresh_tokens` (revoke all) | Account settings [FUTURE UI] |

**Validation errors:** `422` on password policy failure (< 12 chars, common-password match). **Authorization errors:** none beyond authentication itself — every authenticated user may call `/auth/me` and `/auth/change-password` for their own account.

---

## 4. Dashboard

| Method | Path | Permission | Request | Response | Status codes | DB | Frontend consumer |
|---|---|---|---|---|---|---|---|
| GET | `/dashboard/summary` | `content:read` | — | `DashboardSummaryResponse` — active alerts by severity, 24h counts, ingestion health, review backlog | 200, 401, 403 | Aggregates over `alerts`, `indicator_scores`, `sources` | Dashboard §7.1 |
| GET | `/dashboard/trends` | `content:read` | `?days=7\|14\|30` | `DashboardTrendsResponse` — indicator + topic time series | 200, 401, 403, 422 | `indicator_scores`, `content_topics` | Dashboard indicator small multiples |

No rate limit beyond the general 100/min — these are the two most frequently polled endpoints (§dashboard auto-refresh, UX §7.1) so they are deliberately not more restrictively limited.

---

## 5. Content

| Method | Path | Permission | Request | Response | Status codes | Rate limit | DB | Frontend consumer |
|---|---|---|---|---|---|---|---|---|
| GET | `/content` | `content:read` | `?from&to&language&source_id&topic&entity&severity&sentiment&hostility&disinfo&review_status&cluster_canonical_only&page&size&sort` | `Page[ContentListItem]` | 200, 401, 403, 422 | 100/min | `processed_content` ⋈ `raw_content` ⋈ `sources` ⋈ `nlp_results` | Live Monitoring |
| GET | `/content/{id}` | `content:read` | — | `ContentDetailResponse` — original, translation, source, all NLP outputs + confidences + model version, entities, topics, contributing indicators, cluster siblings | 200, 401, 403, 404 | 100/min | Joins across `processed_content`, `nlp_results`, `entities`, `topics`, `model_versions` | Content Analysis (single round trip — TRD §12.4) |
| GET | `/content/{id}/related` | `content:read` | `?limit` | `List[ContentListItem]` (same `cluster_id`) | 200, 401, 403, 404 | 100/min | `processed_content` by `cluster_id` | Content Analysis "Related content" |
| GET | `/content/search` | `content:search` | `?q&...filters...&page&size` | `Page[ContentSearchResult]` with highlight | 200, 401, 403, 422, 429 | **20/min** — the most expensive read | GIN `search_vector` | Search page |

**Validation:** `q` length 2–200 chars ⟵ FR-6.5. **Note:** there is no public "score arbitrary text" endpoint — deliberately absent, not an oversight (TRD §12.5).

---

## 6. Analysis

| Method | Path | Permission | Request | Response | Status codes | Audit | DB | Frontend consumer |
|---|---|---|---|---|---|---|---|---|
| GET | `/analysis/{content_id}` | `content:read` | — | `NlpResultResponse` — all labels, all per-class scores, model version | 200, 401, 403, 404 | none (read) | `nlp_results` | Content Analysis (embedded in `/content/{id}` in practice, exposed separately for direct use) |
| POST | `/analysis/rescore/{content_id}` | `model:activate` | — | `202 {job}` | 202, 401, 403, 404 | analysis.rescore_requested | inserts a new `nlp_results` row against the active model; old row retained | Admin Model Registry |
| GET | `/analysis/stats` | `content:read` | `?from&to&group_by=language\|source\|topic` | `AnalysisStatsResponse` | 200, 401, 403, 422 | none | Aggregates over `nlp_results` | Dashboard |

---

## 7. Indicators

| Method | Path | Permission | Request | Response | Status codes | Audit | DB | Frontend consumer |
|---|---|---|---|---|---|---|---|---|
| GET | `/indicators` | `indicator:read` | — | `List[IndicatorDefinitionResponse]` — code, name, definition, formula text, threshold, n_min, max severity, enabled | 200, 401, 403 | none | `indicator_definitions` | Indicator Settings |
| GET | `/indicators/{code}` | `indicator:read` | — | `IndicatorDefinitionResponse` | 200, 401, 403, 404 | none | `indicator_definitions` | Indicator Settings detail |
| PATCH | `/indicators/{code}` | `indicator:update_threshold` | `{threshold?, n_min?, enabled?}` | `IndicatorDefinitionResponse` | 200, 401, 403, 404, 422 | **indicator.threshold_changed** (old, new, actor) | `indicator_definitions` (update), `audit_logs` | Indicator Settings edit form |
| GET | `/indicators/{code}/scores` | `indicator:read` | `?subject_type&subject_key&from&to&page&size` | `Page[IndicatorScoreResponse]` | 200, 401, 403, 404 | none | `indicator_scores` | Indicator Settings "last 30 days" panel |
| GET | `/indicators/trends` | `indicator:read` | `?subject_type&subject_key&from&to&codes[]` | `IndicatorTrendResponse` | 200, 401, 403, 422 | none | `indicator_scores` (`ix_scores_trend`) | Dashboard trend charts |

**Threshold-change side effect (documented, not incidental):** takes effect from the next scheduled computation only; historical `indicator_scores` are never recomputed under a new threshold ⟵ FLOW §4.10, so an alert's justification is never silently rewritten by a later policy change.

---

## 8. Alerts

| Method | Path | Permission | Request | Response | Status codes | Audit | DB | Frontend consumer |
|---|---|---|---|---|---|---|---|---|
| GET | `/alerts` | `alert:read` | `?status&severity&indicator&subject_type&subject_key&from&to&assigned_to&page&size&sort` | `Page[AlertListItem]` | 200, 401, 403, 422 | none | `alerts` ⋈ `indicator_definitions` ⋈ `users` | Alert Center, Review Queue, Dashboard |
| GET | `/alerts/{id}` | `alert:read` | — | `AlertDetailResponse` — severity, status, explanation, indicator snapshot, raw value, baseline, threshold, confidence, occurrence count, evidence[], review history | 200, 401, 403, 404 | none | `alerts`, `alert_evidence`, `indicator_scores` | Alert Detail |
| GET | `/alerts/{id}/evidence` | `alert:read` | `?page&size` | `Page[ContentListItem]` | 200, 401, 403, 404 | none | `alert_evidence` ⋈ `processed_content` | Alert Detail evidence list |
| POST | `/alerts/{id}/acknowledge` | `alert:review` | — | `AlertResponse` | 200, 401, 403, 404, 409 | **alert.acknowledged** | `alerts.status/acknowledged_at/acknowledged_by` | Alert Center row action |
| POST | `/alerts/{id}/claim` | `alert:review` | — | `AlertResponse` → `under_review` | 200, 401, 403, 404, 409 | **alert.claimed** | `alerts.claimed_by/claimed_at` | Review Queue "claim next" |
| POST | `/alerts/{id}/release` | `alert:review` | — | `AlertResponse` | 200, 401, 403, 404, 409 | **alert.released** | `alerts.claimed_by=null` | Alert Detail "release claim" |
| POST | `/alerts/{id}/resolve` | `alert:review` | `{decision: confirmed\|rejected\|inconclusive, notes?}` | `AlertResponse` + creates `analyst_reviews` | 200, 401, 403, 404, 409, 422 | **alert.resolved** (same transaction as the review insert) | `alerts.status/resolved_*`, `analyst_reviews` (insert) | Alert Detail decision panel |
| GET | `/alerts/stats` | `alert:read` | `?from&to&group_by=indicator\|severity\|status` | `AlertStatsResponse` (incl. precision per indicator) | 200, 401, 403 | none | `alerts`, `analyst_reviews` aggregate | Dashboard, Review Queue supervisor pane |

**409 semantics:** the alert is not in a valid source state for the requested transition (e.g. resolving an already-resolved alert, or claiming an alert claimed a moment earlier by someone else). **Administrator note:** every action endpoint in this section requires `alert:review`, which Administrator never holds — calling any of them as Administrator returns `403`, by design ⟵ FR-5.7.

---

## 9. Reviews

| Method | Path | Permission | Request | Response | Status codes | Audit | DB | Frontend consumer |
|---|---|---|---|---|---|---|---|---|
| GET | `/reviews` | `review:read_all` (or own) | `?reviewer_id&decision&from&to&page&size` | `Page[ReviewResponse]` | 200, 401, 403 | none | `analyst_reviews` | Review Queue |
| POST | `/reviews` | `review:create` | `{target_type: alert\|content, target_id, decision, notes?}` | `201 ReviewResponse` | 201, 401, 403, 404, 422 | implicit via alert.resolved, or **review.created** for content-level reviews | `analyst_reviews` (insert) | Content Analysis review action [PROPOSED] |
| GET | `/reviews/{id}` | `review:read_all` (or own) | — | `ReviewResponse` | 200, 401, 403, 404 | none | `analyst_reviews` | Decision history |
| GET | `/reviews/history/{target_type}/{target_id}` | `alert:read` | — | `List[ReviewResponse]` newest first | 200, 401, 403, 404 | none | `analyst_reviews` filtered by target, incl. superseded | Alert Detail decision history panel |
| POST | `/reviews/export` | `review:export` | `{from, to, decisions[], min_confidence?}` | `202 {export_id}` | 202, 401, 403, 422 | **review.exported** | `review_exports` (insert), `analyst_reviews.exported_at` (update) | Review Queue export dialog (Supervisor) |

**No `PATCH`/`DELETE` exists on `/reviews`** — deliberately absent. Reviews are append-only; a correction is a new `POST /reviews` with the API layer setting `supersedes_id` server-side, never a client-driven edit ⟵ FR-7.3.

---

## 10. Sources

| Method | Path | Permission | Request | Response | Status codes | Audit | DB | Frontend consumer |
|---|---|---|---|---|---|---|---|---|
| GET | `/sources` | `source:read` | `?type&status&health&region&page&size` | `Page[SourceResponse]` | 200, 401, 403 | none | `sources` | Source Monitoring, Admin Sources |
| POST | `/sources` | `source:create` | `{name, type, url, language, region, poll_minutes, config}` | `201 SourceResponse` | 201, 401, 403, 409, 422 | **source.created** | `sources` (insert) — URL SSRF-checked before insert | Admin Sources "add source" |
| GET | `/sources/{id}` | `source:read` | — | `SourceDetailResponse` (+ last 20 runs) | 200, 401, 403, 404 | none | `sources`, `ingestion_runs` | Source Monitoring detail |
| PATCH | `/sources/{id}` | `source:update` | `SourceUpdateRequest` | `SourceResponse` | 200, 401, 403, 404, 422 | **source.updated** | `sources` (update) | Admin Sources edit |
| POST | `/sources/{id}/disable` | `source:disable` | — | 204 | 204, 401, 403, 404 | **source.disabled** | `sources.status` | Admin Sources disable action |
| POST | `/sources/{id}/fetch-now` | `source:fetch_now` | — | `202 {run_id}` | 202, 401, 403, 404, 409, 429 | **source.fetch_now_triggered** | `ingestion_runs` (insert) | Source Monitoring "fetch now" |
| GET | `/sources/{id}/runs` | `source:read` | `?page&size&status` | `Page[IngestionRunResponse]` | 200, 401, 403, 404 | none | `ingestion_runs` | Source Monitoring run history |
| GET | `/sources/health` | `source:read` | — | `SourceHealthSummary` | 200, 401, 403 | none | `sources` aggregate | Source Monitoring header, Dashboard |

**Rate limit:** `fetch-now` 5/hour per user ⟵ SEC-16 — prevents using POLIS as an egress-abuse vector through repeated manual triggers.

---

## 11. Users, Models, Audit, Health

### 11.1 Users

| Method | Path | Permission | Request | Response | Status codes | Audit |
|---|---|---|---|---|---|---|
| GET | `/users` | `user:read` | `?page&size&role&status` | `Page[UserResponse]` | 200, 401, 403 | none |
| POST | `/users` | `user:create` | `{name, email, role, initial_password}` | `201 UserResponse` | 201, 401, 403, 409, 422 | **user.created** |
| GET | `/users/{id}` | `user:read` | — | `UserResponse` | 200, 401, 403, 404 | none |
| PATCH | `/users/{id}` | `user:update` | `{name?, role?, status?}` | `UserResponse` | 200, 401, 403, 404, 422 | **user.updated** (incl. role_changed if applicable) |
| POST | `/users/{id}/disable` | `user:disable` | — | 204 | 204, 401, 403, 404 | **user.disabled** — revokes all refresh tokens |

`UserResponse` never contains `password_hash` — enforced structurally (DB §9, `PolisBase` + `from_attributes` + undeclared field), not by convention.

### 11.2 Models

| Method | Path | Permission | Request | Response | Status codes | Audit |
|---|---|---|---|---|---|---|
| GET | `/models` | `model:read` | — | `Page[ModelVersionResponse]` | 200, 401, 403 | none |
| GET | `/models/{id}` | `model:read` | — | `ModelVersionDetailResponse` (full metrics incl. per-language) | 200, 401, 403, 404 | none |
| POST | `/models/{id}/activate` | `model:activate` | — | `ModelVersionResponse` | 200, 401, 403, 404 | **model.activated** — atomically deactivates the previous active version |

### 11.3 Audit

| Method | Path | Permission | Request | Response | Status codes |
|---|---|---|---|---|---|
| GET | `/audit` | `audit:read_all` | `?actor_id&action&resource_type&from&to&result&page&size` | `Page[AuditLogResponse]` | 200, 401, 403 |
| GET | `/audit/alerts` | `audit:read_alerts` | same filters, scoped | `Page[AuditLogResponse]` | 200, 401, 403 |

Reading the audit log is not itself an audited event (TRD §12.9 — auditing audit reads would recurse without adding accountability value).

### 11.4 Health

| Method | Path | Permission | Response | Status codes |
|---|---|---|---|---|
| GET | `/health` | none (public) | `{"status": "ok"}` — no internal detail | 200 |
| GET | `/health/detail` | `audit:read_all` | DB connectivity + latency, model load state + active version, scheduler status, last successful ingestion per source, pending-analysis backlog | 200, 401, 403 |

`/health` is intentionally minimal — an uptime pinger needs it, but it must not leak dependency versions or connection state to an unauthenticated caller.

---

## 12. API Contract Matrix (Consolidated)

| Endpoint | Method | Permission | Request | Response | Frontend consumer | Test |
|---|---|---|---|---|---|---|
| `/auth/login` | POST | none | LoginRequest | TokenResponse | Login | `test_login_*` |
| `/auth/refresh` | POST | refresh cookie | — | TokenResponse | Axios interceptor | `test_refresh_rotation`, `test_reuse_detection` |
| `/auth/logout` | POST | bearer | — | 204 | Header | `test_logout_revokes` |
| `/auth/me` | GET | bearer | — | UserResponse | Auth context | `test_me` |
| `/auth/change-password` | POST | bearer | ChangePasswordRequest | 204 | — | `test_change_password` |
| `/users` | GET/POST | user:read/create | — / UserCreateRequest | Page[User] / User | Admin Users | `test_users_rbac` |
| `/users/{id}` | GET/PATCH | user:read/update | — / UserUpdateRequest | User | Admin Users | `test_user_update` |
| `/users/{id}/disable` | POST | user:disable | — | 204 | Admin Users | `test_user_disable_revokes` |
| `/sources` | GET/POST | source:read/create | — / SourceCreateRequest | Page[Source]/Source | Sources | `test_source_ssrf_reject` |
| `/sources/{id}` | GET/PATCH | source:read/update | — | Source | Sources | — |
| `/sources/{id}/disable` | POST | source:disable | — | 204 | Sources | — |
| `/sources/{id}/fetch-now` | POST | source:fetch_now | — | 202 | Sources | `test_fetch_now_rate_limit` |
| `/sources/{id}/runs` | GET | source:read | — | Page[Run] | Sources | — |
| `/sources/health` | GET | source:read | — | HealthSummary | Sources, Dashboard | — |
| `/content` | GET | content:read | ContentQuery | Page[ContentListItem] | Monitoring | `test_content_filters` |
| `/content/{id}` | GET | content:read | — | ContentDetailResponse | Content Analysis | `test_content_detail_one_roundtrip` |
| `/content/{id}/related` | GET | content:read | — | List[ContentListItem] | Content Analysis | — |
| `/content/search` | GET | content:search | q + filters | Page[SearchResult] | Search | `test_search_injection_safe` |
| `/analysis/{id}` | GET | content:read | — | NlpResultResponse | Content Analysis | `test_analysis_schema` |
| `/analysis/rescore/{id}` | POST | model:activate | — | 202 | Admin Models | — |
| `/analysis/stats` | GET | content:read | — | Stats | Dashboard | — |
| `/indicators` | GET | indicator:read | — | List[IndicatorDef] | Indicator Settings | `test_indicators_seeded` |
| `/indicators/{code}` | GET/PATCH | indicator:read/update_threshold | — / IndicatorUpdateRequest | IndicatorDef | Indicator Settings | `test_threshold_audit` |
| `/indicators/{code}/scores` | GET | indicator:read | — | Page[Score] | Indicator Settings | — |
| `/indicators/trends` | GET | indicator:read | — | TrendResponse | Dashboard | — |
| `/alerts` | GET | alert:read | AlertQuery | Page[AlertListItem] | Alert Center | `test_alert_queue_sort` |
| `/alerts/{id}` | GET | alert:read | — | AlertDetailResponse | Alert Detail | `test_alert_detail_evidence_never_empty` |
| `/alerts/{id}/evidence` | GET | alert:read | — | Page[ContentListItem] | Alert Detail | — |
| `/alerts/{id}/acknowledge` | POST | alert:review | — | AlertResponse | Alert Center | — |
| `/alerts/{id}/claim` | POST | alert:review | — | AlertResponse | Review Queue | `test_claim_race` |
| `/alerts/{id}/release` | POST | alert:review | — | AlertResponse | Alert Detail | — |
| `/alerts/{id}/resolve` | POST | alert:review | AlertResolveRequest | AlertResponse | Alert Detail | `test_resolve_ind03_requires_notes` |
| `/alerts/stats` | GET | alert:read | — | AlertStatsResponse | Dashboard | `test_precision_calc` |
| `/reviews` | GET/POST | review:read_all/create | — / ReviewCreateRequest | Page[Review]/Review | Review Queue | `test_review_immutable` |
| `/reviews/{id}` | GET | review:read_all | — | Review | — | — |
| `/reviews/history/{type}/{id}` | GET | alert:read | — | List[Review] | Alert Detail | — |
| `/reviews/export` | POST | review:export | ReviewExportRequest | 202 | Review Queue | `test_export_audited` |
| `/models` | GET | model:read | — | Page[ModelVersion] | Admin Models | — |
| `/models/{id}` | GET | model:read | — | ModelVersionDetail | Admin Models | — |
| `/models/{id}/activate` | POST | model:activate | — | ModelVersion | Admin Models | `test_one_active_model` |
| `/audit` | GET | audit:read_all | AuditQuery | Page[AuditLog] | Admin Audit | `test_audit_immutable` |
| `/audit/alerts` | GET | audit:read_alerts | — | Page[AuditLog] | Supervisor pane | — |
| `/dashboard/summary` | GET | content:read | — | Summary | Dashboard | — |
| `/dashboard/trends` | GET | content:read | — | Trends | Dashboard | — |
| `/health` | GET | none | — | `{"status":"ok"}` | Uptime pinger | — |
| `/health/detail` | GET | audit:read_all | — | HealthDetail | Admin | — |

**Total: 44 endpoints across 12 groups.** All are `SPECIFIED, NOT IMPLEMENTED` at this document's version.

---

## 13. OpenAPI

| Aspect | Plan |
|---|---|
| `/api/docs` | FastAPI's auto-generated Swagger UI — **only enabled when `POLIS_ENV=local`** ⟵ TRD §11.2, SEC-19. Disabled in demo/production to avoid handing an unauthenticated caller a full endpoint map. |
| `/api/openapi.json` | Same local-only gating. Used by the frontend's typed API client generation (`openapi-typescript` or similar) during development — **[PROPOSED]**, not yet wired. |
| Current status | **NOT AVAILABLE** — no FastAPI application exists yet to serve either route |

---

## 14. Code Reconciliation

Per the source instruction: *"If an endpoint exists in code but is missing from the documentation, flag it. If documentation claims an endpoint exists but code does not contain it, flag it. Do not silently reconcile contradictions."*

| Check | Result |
|---|---|
| Endpoints in code but not in this document | **N/A — no code exists.** Nothing to compare. |
| Endpoints in this document but not in code | **All 44.** Every endpoint in §12 is `SPECIFIED, NOT IMPLEMENTED`. This is not a contradiction to silently reconcile — it is the expected, disclosed state of a pre-Phase-1 documentation package. |
| Action required | Re-run this section as a literal `grep` of `backend/routes/*.py` route decorators against §12 once Phase 5 (Backend, Implementation Plan Weeks 5–10) produces code. Any drift found then goes into `DOCUMENT-CONSISTENCY-REPORT.md`, not a silent edit of either side. |

---

*End of Document 10. Re-run §14 reconciliation the first time `backend/` contains route files, and after every subsequent endpoint change.*
