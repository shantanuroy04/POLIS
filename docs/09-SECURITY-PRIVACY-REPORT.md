# POLIS — Security & Privacy Report

**Political Open Source Language Intelligence System**

---

## 1. Document Control

| Field | Value |
|---|---|
| Document ID | POLIS-DOC-009 |
| Version | 0.1 — **design-stage report; no code exists to test yet** |
| Date | 11 August 2026 |
| Status | Draft. Converts PRD §12/§13 and TRD §14 requirements into an auditable checklist. All test-evidence fields are `NOT TESTED` pending Phase 8 (Implementation Plan, Week 13). |
| Owner | Team C (Backend/DB) + A2 (security testing lead) |
| Derives from | POLIS-PRD-001 §12 (SEC-1…SEC-28), §13 (PRIV-1…PRIV-13); POLIS-TRD-002 §14; POLIS-DB-005 §11 |

### 1.1 Reading This Document

This is the auditable counterpart to PRD §12/§13 and TRD §14, which state requirements and planned implementation. This document exists to be **checked off with evidence**, not to restate design a third time. Every row in §11 (ASVS checklist) and §13 (test results) carries a status of `PASS / PARTIAL / FAIL / NOT TESTED` — never a bare assertion. As of this version, the repository contains no application code (only the `docs/` package), so every evidence field is honestly `NOT TESTED`.

---

## 2. Security Scope

In scope: the FastAPI backend, the React frontend, the PostgreSQL database, the ingestion pipeline (as the primary untrusted-input boundary), the ML inference path, and the CI pipeline. Out of scope: the security posture of third-party free-tier hosts themselves (Render/Vercel/Supabase infrastructure) beyond POLIS's configuration of them, and any claim of protection against a well-resourced nation-state actor — POLIS is an academic prototype with a proportionate, not maximal, security posture ⟵ PRD C-10.

---

## 3. Threat Model

### 3.1 Assets

| Asset | Sensitivity | Where |
|---|---|---|
| User accounts (email, role) | Medium — not sensitive data itself, but the gateway to everything else | `users` |
| Password hashes | High — must never be recoverable | `users.password_hash`, Argon2id |
| Refresh tokens | High — session takeover if stolen | `refresh_tokens`, hashed at rest |
| Database contents overall | Medium — public content + internal judgments | PostgreSQL |
| Source configuration | Medium — misuse could turn POLIS into an SSRF/egress tool | `sources` |
| Model artefacts | Low — not secret, but integrity matters (a swapped model silently changes every downstream judgment) | Hugging Face Hub reference |
| Audit logs | High — the accountability record itself | `audit_logs`, append-only by grant |
| Public content (ingested) | Low sensitivity, high volume — the attack surface, not the target | `raw_content`, `processed_content` |
| Analyst decisions | Medium — the human judgment record; tampering would corrupt the system's actual output | `analyst_reviews` |

### 3.2 Threat Categories

Authentication attacks · authorization bypass · SQL injection · XSS (via ingested content or user input) · SSRF (via source URLs) · malicious scraped content · credential/secret leakage · dependency vulnerabilities · abuse/rate-limit evasion · data tampering · audit-log manipulation.

### 3.3 Threat Model Table

| Asset | Threat | Attack vector | Impact | Likelihood | Mitigation | Verification |
|---|---|---|---|---|---|---|
| Password hashes | Offline cracking if the DB leaks | DB compromise, backup exposure | Account takeover | Low (single deployment, limited attack surface) | Argon2id, memory-hard ⟵ SEC-1 | Phase 8.3, NOT TESTED |
| Refresh tokens | Session hijack | XSS exfiltration, DB leak of raw token | Persistent account access | Low–Med | `HttpOnly` cookie (unreachable from JS), SHA-256 hashed at rest (DB never holds a usable token) ⟵ SEC-5, SEC-6 | Phase 8.15, NOT TESTED |
| Any endpoint | Authorization bypass | Forged/omitted role check, IDOR | Unauthorised read/write, privilege escalation | Med (most common real-world API flaw class) | `require(permission)` on every route, default-deny, object-level checks ⟵ SEC-7, SEC-8 | Phase 8.4/8.5, NOT TESTED |
| Database | SQL injection | Unsanitised query construction | Data exfiltration/corruption | Low (ORM-only policy + CI grep) | Parameterised queries only, `plainto_tsquery(:q)` bound ⟵ SEC-11 | Phase 8.8, NOT TESTED |
| Any rendered surface | Stored XSS | Malicious content in an ingested public source | Session/token theft, UI manipulation | Med–High (ingestion reads attacker-influenceable text by design) | HTML stripped at ingest, React text-node rendering, `dangerouslySetInnerHTML` banned + lint-enforced, CSP ⟵ SEC-13, SEC-14 | Phase 8.9, NOT TESTED |
| Internal network / cloud metadata | SSRF | Malicious source URL, redirect chain | Internal service access, credential theft (cloud metadata endpoint) | Med (feeds and HTML sources point at attacker-influenceable URLs by design) | DNS-resolved allowlist check at every hop, scheme/port restriction, size/timeout caps ⟵ SEC-12 | Phase 8.10, NOT TESTED |
| Secrets (`.env`, JWT secret, API credentials) | Leakage | Committed to Git, logged, exposed in frontend bundle, error message | Full system compromise | Low (CI-enforced scanning) if controls hold; High impact if they fail | `gitleaks` in CI + pre-commit, `.env` git-ignored, redaction filter on all logs ⟵ SEC-17, SEC-18, SEC-20 | Phase 8.2, NOT TESTED |
| Dependencies | Known-vulnerable package | Outdated `pip`/`npm` packages | Varies by CVE | Med (ambient risk of any project) | `pip-audit` + `npm audit` in CI, blocking on high/critical ⟵ SEC-24 | Phase 8.1, NOT TESTED |
| Login endpoint | Credential stuffing / brute force | Automated login attempts | Account takeover at scale | Med | Per-account+IP rate limit, generic failure message, no enumeration ⟵ SEC-2, SEC-3, SEC-4 | Phase 8.7, NOT TESTED |
| `audit_logs` | Tampering to hide an action | Compromised app-role credentials, application bug | Loss of accountability, undermines the entire human-in-the-loop evidentiary model | Low (grant-level enforcement, not app-logic) | `UPDATE`/`DELETE` revoked from `polis_app` at the database role level ⟵ SEC-21, DB §11.1 | Phase 8.14, NOT TESTED |
| `analyst_reviews` | Tampering with a recorded decision | Compromised session, application bug | Corrupts the accountability record the whole system's legitimacy rests on | Low | No `UPDATE`/`DELETE` code path exists; corrections are new superseding rows, both retained ⟵ FR-7.3 | Design-level; Phase 9 integration test |
| Any endpoint | Rate-limit evasion / DoS via `fetch-now` | Abuse of the manual-fetch trigger as an egress amplifier | Resource exhaustion, POLIS used as a proxy | Low–Med | 5/hour per user on `fetch-now`; SSRF guard applies to every fetch regardless of trigger source ⟵ SEC-16 | Phase 8.7, NOT TESTED |

---

## 4. Authentication ⟵ PRD SEC-1…SEC-4, TRD §14.1, §9.1

| Requirement | Planned implementation | Status |
|---|---|---|
| Password hashing | Argon2id, `time_cost=2, memory_cost=64MB, parallelism=2` | Specified, NOT IMPLEMENTED |
| Minimum password length | 12 characters, common-password check, no composition rules | Specified, NOT IMPLEMENTED |
| No user enumeration | Identical error for unknown user and wrong password; dummy Argon2 verify runs even for a non-existent user (constant time) | Specified, NOT IMPLEMENTED |
| Login rate limiting | 5 failed/15 min per (account, IP), then temporary lockout, audited | Specified, NOT IMPLEMENTED |
| Access token | JWT, HS256, 15 min lifetime, in-memory client storage only (never `localStorage`) | Specified, NOT IMPLEMENTED |
| Refresh token | Opaque 256-bit, SHA-256 hashed at rest, 8 h lifetime, `HttpOnly; Secure; SameSite=Strict` cookie, rotated on every use, reuse detection revokes the family | Specified, NOT IMPLEMENTED |
| Revocation on disable/role-change | All refresh tokens revoked immediately | Specified, NOT IMPLEMENTED |

---

## 5. Authorization / RBAC ⟵ PRD SEC-7, SEC-8, TRD §9.2, §14.2

| Element | Detail |
|---|---|
| Roles | `analyst`, `supervisor`, `admin` — exactly three, no implicit superuser bypass |
| Permissions | ~25 atomic strings (`alert:review`, `source:create`, …), stored as data in `permissions`/`role_permissions`, not hard-coded enums — adding the [FUTURE] Observer role is a data change |
| Default deny | Every route requires an explicit `Depends(require("permission"))`; a route-enumeration test (planned) asserts no protected route lacks this dependency |
| Object-level checks | An Analyst may read all alerts but modify only their own reviews unless `review:read_all` is held |
| Administrator separation of duties | Administrator explicitly **cannot** hold `alert:review` — the role that controls thresholds/sources/model activation is deliberately barred from recording analytical judgments, so the audit trail of "who decided X" and "who configured the system that produced X" never overlaps in one person's authority ⟵ PRD §6, TRD §2.1 |
| Enforcement point | Database-role-checked on every request (permission lookup, not JWT role claim alone) — a role change takes effect on the very next request, not at next login |

**Full permission matrix:** TRD §9.2 (authoritative — not restated here to avoid drift).

---

## 6. Input Security ⟵ PRD SEC-10…SEC-15, TRD §14.3, §14.4

| Control | Mechanism |
|---|---|
| Pydantic validation | Every request body/query/path param is a typed model with `extra="forbid"` — unknown fields rejected, not ignored |
| SQL injection prevention | SQLAlchemy ORM / bound `text()` only; CI grep rejects string-built SQL adjacent to SQL keywords; full-text search binds `q` into `plainto_tsquery(:q)`, never interpolates operator syntax |
| XSS prevention | React's default escaping; `dangerouslySetInnerHTML` banned repo-wide via ESLint rule, CI-enforced |
| HTML sanitisation | `bleach` allowlist-stripping on all ingested content at ingest time — content is stored and rendered as text, never as HTML |
| URL validation / SSRF protection | `url_guard.assert_url_allowed()` — scheme restricted to http/https, every resolved IP checked against a private/loopback/link-local/metadata blocklist, redirects re-validated at every hop (max 3), applied both at source-creation time and at every fetch |
| File/response size limits | 2 MB response cap enforced by streaming (not trusting `Content-Length`); 10 s timeout |

---

## 7. Scraped-Content Security ⟵ PRD SEC-13, TRD §14.6

POLIS's central security property: **ingestion reads attacker-influenceable text by design** — any public feed operator can put arbitrary content in a POLIS-monitored source. Controls:

| Vector | Control |
|---|---|
| Stored XSS via article body | HTML stripped to plain text before storage; never stored or rendered as markup |
| Decompression/nesting bombs | Streamed size cap; parser depth limit; wall-clock parse timeout |
| Prompt-injection-style content | Architecturally inapplicable — POLIS uses fixed classifiers, not an instruction-following LLM, so ingested text cannot alter system behaviour by containing instructions. This is a structural property, documented as such, not a control that could fail. |
| Unicode spoofing / bidi override | NFKC normalisation; bidirectional-override characters stripped from display text |
| Oversized single item | Truncated at ingest with a visible flag, not silently dropped |
| Malicious embedded link | Rendered with `rel="noopener noreferrer nofollow"`, hostname shown before click, never auto-fetched client-side |

---

## 8. Secrets Management ⟵ PRD SEC-17, SEC-18, TRD §10.4

| Control | Detail |
|---|---|
| `.env` | Git-ignored; never committed |
| `.env.example` | Committed with empty values for every key, so the required configuration surface is visible without exposing any value |
| Secret scanning | `gitleaks` in CI on every push (fails the build on any finding) and as a local pre-commit hook |
| Git history scanning | `gitleaks detect --log-opts="--all"` run as a Phase 8 task — scans full history, not just HEAD |
| No secrets in frontend | Vite env vars require a `VITE_` prefix to reach the bundle — flagged explicitly as a footgun in TRD §17 (a developer could accidentally prefix a secret); CI asserts no `VITE_`-prefixed variable matches a secret-shaped name |
| No credentials in database | Source-type credentials (Telegram API hash, Reddit client secret) live in environment configuration only; the `sources.config` JSONB column is documented as **never** holding credentials ⟵ DB §5.2 |

---

## 9. Logging & Audit ⟵ PRD SEC-20, SEC-21, TRD §14.8, §15

Three distinct, non-overlapping record types:

| Type | Purpose | Retention | Contains secrets? | Mutable? |
|---|---|---|---|---|
| **Application logs** | Operational debugging — request timings, errors, correlation IDs | 30 days | Never — central redaction filter strips password/token/secret-shaped keys before any line is written | Yes (ordinary log rotation) |
| **Security logs** | A subset of application logs specifically covering auth outcomes, rate limits, blocked URLs, validation rejections | 365 days (folded into `audit_logs` where the event is a privileged action; otherwise application log retention) | Never | Yes for pure security logs; the audited subset is append-only |
| **Audit records** | The accountability record — who did what, when, to what, with what result | 365 days (content-linked evidence may expire per retention policy while the audit record itself persists) | Never — CHECK constraint on `audit_logs.detail` rejects any key matching `password\|secret\|token\|api_key\|password_hash` | **No** — `UPDATE`/`DELETE` revoked from the application database role; enforced by grant, not by application code (DB §11.1) |

The distinction matters: application/security logs are operational and can rotate; audit records are the evidentiary trail behind every alert decision and every privileged action, and their immutability is a database-enforced guarantee, not a convention.

---

## 10. Dependency Security ⟵ PRD SEC-24, TRD §16, §17

| Tool | Scope | Policy |
|---|---|---|
| `pip-audit` | Python dependencies | Run in CI on every PR; high/critical findings block merge |
| `npm audit --production` | Frontend dependencies | Same policy |
| Version pinning | `requirements.txt` (exact `==` pins per TRD §4.2), `package-lock.json` committed | Unpinned dependency additions rejected in review |
| Remediation process | A finding is triaged within the sprint it is found: patch if a fix exists, pin to the last safe version if not, or document an accepted-risk exception with the supervisor's sign-off if no fix exists and the dependency is essential — never silently ignored |

**Status: NOT RUN** — no `requirements.txt`/`package-lock.json` exists yet to audit (pre-Phase 1).

---

## 11. OWASP ASVS Checklist

Target: **ASVS Level 1, with selected Level 2 controls** ⟵ PRD NFR-8.1, SM-23 (≥ 90% of checklist items passed at MVP release).

| Control | Requirement | POLIS Implementation | Status | Evidence |
|---|---|---|---|---|
| V2.1 | Password length/strength policy | 12-char minimum, common-password check | NOT TESTED | — |
| V2.2 | Anti-automation (rate limiting, generic errors) | 5/15min lockout, identical error message | NOT TESTED | — |
| V2.4 | Credential storage (Argon2id/bcrypt) | Argon2id, tuned memory cost | NOT TESTED | — |
| V3.2 | Session token generation | JWT signed HS256, 15 min | NOT TESTED | — |
| V3.3 | Session termination | Refresh revocation on logout/disable/role-change | NOT TESTED | — |
| V3.4 | Cookie-based session token | `HttpOnly; Secure; SameSite=Strict`, path-scoped | NOT TESTED | — |
| V4.1 | General access control (default deny) | `require(permission)` on every route | NOT TESTED | — |
| V4.2 | Operation-level access control (IDOR) | Object-level review-ownership check | NOT TESTED | — |
| V5.1 | Input validation | Pydantic `extra="forbid"`, typed bounds | NOT TESTED | — |
| V5.2 | Sanitization / sandboxing | `bleach` stripping on ingest | NOT TESTED | — |
| V5.3 | Output encoding / injection prevention | ORM-only DB access, bound FTS query | NOT TESTED | — |
| V6.2 | Data classification / encryption at rest | Host-provided (Supabase); no additional app-layer encryption, justified by no sensitive-PII storage | NOT TESTED | — |
| V6.4 | Secrets management | `.env`, `pydantic-settings`, `gitleaks` | NOT TESTED | — |
| V7.1 | Log content | Redaction filter, no secrets/emails logged | NOT TESTED | — |
| V7.2 | Log protection | Append-only `audit_logs` via DB grant | NOT TESTED | — |
| V7.4 | Error handling | Generic client error + server-side detail by request ID | NOT TESTED | — |
| V9.1 | Transport security | HTTPS enforced by host, HSTS header | NOT TESTED | — |
| V12.1 | File upload | Not applicable — no upload feature in MVP | N/A | — |
| V12.6 | SSRF prevention | `url_guard`, DNS-resolved allowlist, redirect re-validation | NOT TESTED | — |
| V13.1 | Rate limiting | `slowapi`, per-endpoint limits | NOT TESTED | — |
| V14.4 | HTTP security headers / CSP | CSP, `X-Content-Type-Options`, `Referrer-Policy` | NOT TESTED | — |
| V14.5 | CORS configuration | Explicit origin allowlist, no wildcard | NOT TESTED | — |

**Current pass rate: 0/21 — because no code exists to test.** This is the expected and honest state at this stage of the project (post-Phase-0 documentation, pre-Phase-1 implementation). The ≥ 90% target applies at MVP release (Implementation Plan Phase 8, Week 13), not now.

---

## 12. Privacy ⟵ PRD §13 (PRIV-1…PRIV-13)

| Principle | Implementation |
|---|---|
| Public-source-only data | Only content accessible without authentication and without circumventing access controls is ingested; enforced by source-type restriction (RSS, public Telegram, public Reddit, government pages) — see POLIS-DOC-014 for the per-source register |
| Data minimisation | Only fields required for monitoring are stored (text, language, source, timestamps, URL, derived NLP outputs); no enrichment beyond what a source publishes |
| Author handles | Stored only where intrinsic to the public item, never cross-referenced or used to build a profile |
| Retention | Raw/processed content 180 days, NLP results/indicator scores 365 days, audit logs 365 days, alerts/reviews retained for project duration — all **[PROPOSED]** project decisions, not claimed legal requirements ⟵ PRIV-4, DB §12 |
| Deletion/purge | Daily scheduled job; cascades from `raw_content` through derived tables; alerts/reviews/audit are `RESTRICT`-protected and survive content purge, with the UI showing an honest "source content since removed under retention policy" message rather than a broken link |
| Analyst decisions | Immutable, retained for project duration as academic evidence, never auto-fed into training (FR-3.11) |
| Audit retention | 365 days |
| Translation | Machine-generated, always labelled unverified, never the classification input, no third-party translation API used (self-hosted opus-mt/NLLB) so translated text never leaves the system |
| Data exports | Review-decision exports (FR-7.6) are explicit, Supervisor/Admin-only, audited, and produce a versioned artefact — never an automatic feed into retraining |

---

## 13. Security Test Results

Per the source prompt's explicit instruction: **never mark a control PASS without evidence.** As no application code exists yet, every row is `NOT TESTED`. This table will be updated in place (not duplicated) as Phase 8 (Implementation Plan, Week 13) executes.

| Test area | Test | Status | Evidence |
|---|---|---|---|
| Authentication | No-token / expired / malformed / tampered access | NOT TESTED | — |
| Authorization | Every role × every endpoint matrix | NOT TESTED | — |
| IDOR | Cross-user review modification attempt | NOT TESTED | — |
| SQL injection | `sqlmap` + manual payloads on list/search/filter endpoints | NOT TESTED | — |
| XSS | Script payloads through ingestion to every render surface | NOT TESTED | — |
| SSRF | 5 vectors: loopback, link-local, metadata endpoint, DNS-rebind, public→internal redirect | NOT TESTED | — |
| Rate limiting | Burst against login, search, fetch-now | NOT TESTED | — |
| Secret scan | `gitleaks` full-history scan | NOT TESTED | — |
| Dependency audit | `pip-audit`, `npm audit --production` | NOT TESTED | — |
| Error leakage | Forced-500 fault injection | NOT TESTED | — |
| Audit immutability | `UPDATE`/`DELETE` on `audit_logs` as `polis_app` | NOT TESTED | — |
| Session lifecycle | Expiry, rotation, reuse detection, revoke-on-disable | NOT TESTED | — |
| Security headers | CSP, HSTS, nosniff, Referrer-Policy presence | NOT TESTED | — |
| CORS | Request from non-allowlisted origin | NOT TESTED | — |

**Release gate:** per PRD §23 criterion 9, MVP release requires ASVS ≥ 90% passed with every gap documented, and per criterion 10, zero secrets and zero high/critical CVEs. Neither condition is currently evaluable — this document will carry a `RELEASE READY / BLOCKED / CONDITIONAL` verdict for the security dimension once Phase 8 executes, mirroring POLIS-DOC-013's overall release gate.

---

*End of Document 9. This is a living document — re-run §11 and §13 after every Phase 8 test cycle and update statuses in place with dated evidence, never retroactively mark a prior version's NOT TESTED as PASS.*
