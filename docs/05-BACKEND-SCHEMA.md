# POLIS — Backend Schema and Database Design

**Political Open Source Language Intelligence System**

---

## 1. Document Control

| Field | Value |
|---|---|
| Document ID | POLIS-DB-005 |
| Version | 1.0 |
| Date | 11 August 2026 |
| Status | Draft for Review — **schema freezes Week 3** ⟵ PRD §21.2 |
| Derives from | POLIS-PRD-001, POLIS-TRD-002, POLIS-FLOW-003 |
| Owner | Team C (Backend/Database) |
| Technology | PostgreSQL 15 · SQLAlchemy 2.0 · Alembic 1.13 · Pydantic 2.9 · FastAPI 0.115 |

### 1.1 Freeze Notice

This schema is one of the three interfaces that must freeze early ⟵ PRD §21.2, because Teams A, B, C, and D all write against it. After **Week 3**, changes require agreement from Team C plus any affected team, and an Alembic migration with a documented rollback.

---

## 2. Design Principles

| # | Principle | Consequence in this schema |
|---|---|---|
| 1 | **Raw is immutable** | `raw_content` is insert-only. Cleaning, translation, and analysis write elsewhere. An analyst can always see exactly what was collected. |
| 2 | **Every derived value names its producer** | `nlp_results.model_version_id` is `NOT NULL`. A score with no attributable model is worthless as evidence ⟵ FR-3.8. |
| 3 | **Nothing that fed a decision is ever deleted** | Reviews, alerts, and audit records survive user disablement and content purge. Retention purges *content*, not *judgments* ⟵ PRIV-4, FR-8.4. |
| 4 | **Audit is append-only at the database level** | Enforced by role grants, not by application discipline ⟵ SEC-21, AC-19. |
| 5 | **Store computations that did not fire** | `indicator_scores` records below-threshold and below-`n_min` results. Without them, "what would this threshold change have done?" is unanswerable ⟵ FLOW §4.10. |
| 6 | **Duplicates are linked, not discarded** | `cluster_id` retains near-duplicates because cluster size *is* IND-03's input ⟵ FR-2.7. |
| 7 | **Data minimisation** | No personal fields beyond a public author handle where it is intrinsic to the item. No profile, no cross-linking ⟵ PRIV-2, PRIV-3. |
| 8 | **Constraints in the database, not only in Python** | The database is the last line of defence and outlives any one service. |

---

## 3. Entity Inventory

| # | Table | Group | Purpose | Rows (demo est.) | Write path |
|---|---|---|---|---|---|
| 1 | `users` | Identity | Accounts | ~10 | Admin |
| 2 | `roles` | Identity | analyst / supervisor / admin | 3 | Seed |
| 3 | `permissions` | Identity | Atomic permission strings | ~25 | Seed |
| 4 | `role_permissions` | Identity | RBAC mapping | ~45 | Seed |
| 5 | `refresh_tokens` | Identity | Session lifecycle, revocation | ~100 | Auth |
| 6 | `sources` | Ingestion | Configured public sources | ~50 | Admin |
| 7 | `ingestion_runs` | Ingestion | Per-fetch outcome | ~50k | Scheduler |
| 8 | `raw_content` | Content | Immutable collected items | ~50k | Scheduler |
| 9 | `processed_content` | Content | Cleaned, language, cluster, translation | ~50k | Scheduler |
| 10 | `model_versions` | ML | Model registry | ~10 | Admin/ML |
| 11 | `nlp_results` | ML | Classifier output per (content, model) | ~60k | Scheduler |
| 12 | `entities` | ML | Deduplicated entity register | ~5k | Scheduler |
| 13 | `content_entities` | ML | Entity mentions with offsets | ~200k | Scheduler |
| 14 | `topics` | ML | Fixed taxonomy | ~20 | Seed |
| 15 | `content_topics` | ML | Topic assignment with confidence | ~100k | Scheduler |
| 16 | `subjects` | Signal | Analysis scopes (region × topic/entity) | ~200 | Seed + derived |
| 17 | `indicator_definitions` | Signal | IND-01…06 config and formula text | 6 | Seed |
| 18 | `indicator_scores` | Signal | Every computation, fired or not | ~500k | Scheduler |
| 19 | `alerts` | Signal | Persisted, reviewable alerts | ~500 | Scheduler |
| 20 | `alert_evidence` | Signal | Alert → contributing content | ~10k | Scheduler |
| 21 | `analyst_reviews` | Human | Immutable decisions | ~500 | Analyst |
| 22 | `review_exports` | Human | Audited dataset exports | ~5 | Supervisor |
| 23 | `audit_logs` | Audit | Append-only action record | ~50k | All |

**23 tables.** Every one is referenced by a functional requirement; none exists speculatively.

---

## 4. Entity Relationship Diagram

```mermaid
erDiagram
    ROLES ||--o{ USERS : "assigned to"
    ROLES ||--o{ ROLE_PERMISSIONS : has
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : "granted by"
    USERS ||--o{ REFRESH_TOKENS : owns
    USERS ||--o{ ANALYST_REVIEWS : records
    USERS ||--o{ AUDIT_LOGS : "acts in"
    USERS ||--o{ ALERTS : "claims/resolves"
    USERS ||--o{ REVIEW_EXPORTS : requests

    SOURCES ||--o{ RAW_CONTENT : produces
    SOURCES ||--o{ INGESTION_RUNS : "fetched by"

    RAW_CONTENT ||--|| PROCESSED_CONTENT : "cleaned into"
    PROCESSED_CONTENT ||--o{ NLP_RESULTS : "analysed as"
    PROCESSED_CONTENT ||--o{ CONTENT_ENTITIES : mentions
    PROCESSED_CONTENT ||--o{ CONTENT_TOPICS : "tagged with"
    PROCESSED_CONTENT ||--o{ ALERT_EVIDENCE : "is evidence in"

    MODEL_VERSIONS ||--o{ NLP_RESULTS : produced
    MODEL_VERSIONS ||--o{ CONTENT_ENTITIES : produced
    MODEL_VERSIONS ||--o{ CONTENT_TOPICS : produced

    ENTITIES ||--o{ CONTENT_ENTITIES : "mentioned in"
    TOPICS ||--o{ CONTENT_TOPICS : "assigned in"

    SUBJECTS ||--o{ INDICATOR_SCORES : "scoped by"
    SUBJECTS ||--o{ ALERTS : "scoped by"
    TOPICS ||--o{ SUBJECTS : "may define"
    ENTITIES ||--o{ SUBJECTS : "may define"

    INDICATOR_DEFINITIONS ||--o{ INDICATOR_SCORES : computes
    INDICATOR_DEFINITIONS ||--o{ ALERTS : triggers
    INDICATOR_SCORES ||--o{ ALERTS : "raises candidate"

    ALERTS ||--o{ ALERT_EVIDENCE : "supported by"
    ALERTS ||--o{ ANALYST_REVIEWS : "reviewed in"
    ANALYST_REVIEWS ||--o| ANALYST_REVIEWS : supersedes

    USERS {
        uuid id PK
        text full_name
        citext email UK
        text password_hash "argon2id — never plaintext"
        uuid role_id FK
        text status "active|disabled"
        timestamptz last_login_at
        timestamptz created_at
        timestamptz updated_at
    }
    ROLES {
        uuid id PK
        text code UK "analyst|supervisor|admin"
        text name
        text description
    }
    PERMISSIONS {
        uuid id PK
        text code UK "alert:review"
        text description
    }
    ROLE_PERMISSIONS {
        uuid role_id PK_FK
        uuid permission_id PK_FK
    }
    REFRESH_TOKENS {
        uuid id PK
        uuid user_id FK
        text token_hash UK "sha256 — never the token"
        timestamptz expires_at
        timestamptz revoked_at
        uuid replaced_by FK
        inet created_ip
    }
    SOURCES {
        uuid id PK
        text name UK
        text source_type "rss|telegram|reddit|html_page"
        text url
        text language
        text region
        int poll_minutes
        text status "enabled|disabled"
        text health_status "healthy|degraded|unhealthy|config_error"
        int consecutive_failures
        text reliability_band "established|mixed|limited"
        jsonb config
        text last_cursor
        timestamptz last_success_at
        timestamptz created_at
    }
    INGESTION_RUNS {
        uuid id PK
        uuid source_id FK
        timestamptz started_at
        timestamptz finished_at
        text status "running|success|failed|partial"
        int items_seen
        int items_new
        int items_duplicate
        text error_class
        text error_detail
    }
    RAW_CONTENT {
        uuid id PK
        uuid source_id FK
        text external_id
        text url
        text title
        text body "immutable as collected"
        text author_handle "public handle only — PRIV-2"
        timestamptz published_at
        timestamptz collected_at
        char content_hash UK "sha256 of normalised text"
        jsonb source_metadata
    }
    PROCESSED_CONTENT {
        uuid id PK
        uuid raw_content_id FK_UK
        text cleaned_text
        text normalized_text
        text language_code
        numeric language_confidence
        bool language_uncertain
        text translated_text
        text translation_model
        bigint simhash
        uuid cluster_id
        bool is_canonical
        bool truncated
        text status "pending_analysis|analyzed|scoring_failed|clean_degraded"
        timestamptz processed_at
    }
    MODEL_VERSIONS {
        uuid id PK
        text version_tag UK "polis-xlmr-v0.3.1"
        text base_model
        text tasks "array"
        text dataset_ref
        jsonb metrics "pooled + per-language"
        text artifact_uri
        bool is_active "one only — partial unique index"
        timestamptz trained_at
        timestamptz created_at
    }
    NLP_RESULTS {
        uuid id PK
        uuid processed_content_id FK
        uuid model_version_id FK
        text schema_version
        text sentiment_label
        numeric sentiment_confidence
        jsonb sentiment_scores
        text hostility_label
        numeric hostility_confidence
        jsonb hostility_scores
        text disinfo_label
        numeric disinfo_confidence
        jsonb disinfo_scores
        text stance_label
        numeric stance_confidence
        jsonb stance_scores
        int inference_ms
        timestamptz created_at
    }
    ENTITIES {
        uuid id PK
        text canonical_name
        text entity_type "PERSON|ORG|GPE|LOC|EVENT"
        text normalized_key UK
        bool is_watchlisted
        timestamptz created_at
    }
    CONTENT_ENTITIES {
        uuid id PK
        uuid processed_content_id FK
        uuid entity_id FK
        uuid model_version_id FK
        text surface_form
        int char_start
        int char_end
        numeric confidence
    }
    TOPICS {
        uuid id PK
        text code UK
        text name
        text description
        bool is_active
    }
    CONTENT_TOPICS {
        uuid id PK
        uuid processed_content_id FK
        uuid topic_id FK
        uuid model_version_id FK
        numeric confidence
    }
    SUBJECTS {
        uuid id PK
        text subject_type "region_topic|region_entity"
        text region
        uuid topic_id FK
        uuid entity_id FK
        text subject_key UK
        text label
        bool is_active
    }
    INDICATOR_DEFINITIONS {
        uuid id PK
        text code UK "IND-01"
        text name
        text definition
        text formula_text
        text family "language|tone|structure|reliability|volume|composite"
        numeric threshold
        int n_min
        text max_severity
        text false_positive_note
        bool requires_notes_on_confirm
        bool is_enabled
        timestamptz updated_at
        uuid updated_by FK
    }
    INDICATOR_SCORES {
        uuid id PK
        uuid indicator_id FK
        uuid subject_id FK
        timestamptz window_start
        timestamptz window_end
        bool computed
        text not_computed_reason
        numeric raw_value
        numeric baseline_mean
        numeric baseline_stddev
        numeric z_score
        numeric threshold_applied
        text severity
        numeric confidence
        int n_current
        int n_sources
        uuid[] evidence_content_ids
        jsonb component_scores "IND-06 only"
        bool alert_evaluated
        timestamptz created_at
    }
    ALERTS {
        uuid id PK
        uuid indicator_id FK
        uuid subject_id FK
        uuid triggering_score_id FK
        text severity
        text status "new|acknowledged|under_review|resolved_confirmed|resolved_rejected|resolved_inconclusive"
        text explanation
        numeric raw_value
        numeric baseline_mean
        numeric baseline_stddev
        numeric z_score
        numeric threshold_applied
        numeric confidence
        int n_items
        int n_sources
        int occurrence_count
        uuid claimed_by FK
        timestamptz claimed_at
        timestamptz acknowledged_at
        uuid acknowledged_by FK
        timestamptz resolved_at
        uuid resolved_by FK
        timestamptz first_seen_at
        timestamptz last_seen_at
        timestamptz created_at
    }
    ALERT_EVIDENCE {
        uuid alert_id PK_FK
        uuid processed_content_id PK_FK
        numeric contribution
        timestamptz added_at
    }
    ANALYST_REVIEWS {
        uuid id PK
        text target_type "alert|content"
        uuid alert_id FK
        uuid processed_content_id FK
        uuid reviewer_id FK
        text decision "confirmed|rejected|inconclusive"
        text notes
        uuid model_version_id FK
        uuid supersedes_id FK
        bool is_current
        timestamptz exported_at
        timestamptz created_at
    }
    REVIEW_EXPORTS {
        uuid id PK
        uuid requested_by FK
        timestamptz period_start
        timestamptz period_end
        int record_count
        char content_hash
        text artifact_uri
        timestamptz created_at
    }
    AUDIT_LOGS {
        bigint id PK
        uuid actor_id FK "null for system"
        text actor_type "user|system"
        text action
        text resource_type
        text resource_id
        text result "success|denied|failure"
        jsonb detail "old/new values — never secrets"
        uuid request_id
        inet source_ip
        timestamptz created_at
    }
```

---

## 5. Data Dictionary

Only non-obvious columns are annotated. `created_at`/`updated_at` are `timestamptz NOT NULL DEFAULT now()` throughout.

### 5.1 Identity

**`users`** ⟵ FR-8.1, FR-8.4

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `uuid` | no | `gen_random_uuid()` | PK |
| `full_name` | `text` | no | | 1–200 chars (CHECK) |
| `email` | `citext` | no | | **UNIQUE**, case-insensitive |
| `password_hash` | `text` | no | | Argon2id ⟵ SEC-1. Never selected into any response schema. |
| `role_id` | `uuid` | no | | FK `roles`, `ON DELETE RESTRICT` |
| `status` | `text` | no | `'active'` | CHECK in (`active`,`disabled`) |
| `last_login_at` | `timestamptz` | yes | | |
| `failed_login_count` | `int` | no | `0` | Lockout counter ⟵ SEC-4 |
| `locked_until` | `timestamptz` | yes | | |

Users are **never deleted** ⟵ FR-8.4 — `status='disabled'` preserves referential integrity for reviews and audit.

**`refresh_tokens`** ⟵ SEC-5, SEC-6, SEC-27

| Column | Type | Null | Notes |
|---|---|---|---|
| `token_hash` | `char(64)` | no | SHA-256 of the opaque token. **The token itself is never stored** — a database read must not yield a usable credential. |
| `expires_at` | `timestamptz` | no | |
| `revoked_at` | `timestamptz` | yes | Set on logout, rotation, password change, role change, disable |
| `replaced_by` | `uuid` | yes | Rotation chain; reuse of a revoked token with a successor = theft signal → revoke family |
| `created_ip` | `inet` | yes | ⟵ SEC-21 |

### 5.2 Ingestion

**`sources`** ⟵ FR-1.1–1.15, FR-4.10

| Column | Type | Null | Notes |
|---|---|---|---|
| `source_type` | `text` | no | CHECK in (`rss`,`telegram`,`reddit`,`html_page`) |
| `url` | `text` | no | Validated by `assert_url_allowed` at insert ⟵ SEC-12 |
| `language` | `text` | yes | Expected ISO 639-1; `NULL` = mixed |
| `region` | `text` | yes | ⟵ TBD-14 taxonomy |
| `poll_minutes` | `int` | no | Default 15, CHECK 5–1440 ⟵ FR-1.2 |
| `health_status` | `text` | no | CHECK in (`healthy`,`degraded`,`unhealthy`,`config_error`) ⟵ FR-1.11 |
| `consecutive_failures` | `int` | no | ≥3 → `unhealthy` |
| `reliability_band` | `text` | no | CHECK in (`established`,`mixed`,`limited`) — qualitative only ⟵ PRIV-10 |
| `config` | `jsonb` | no | Type-specific settings. **Never credentials** — those live in env ⟵ SEC-17 |
| `last_cursor` | `text` | yes | Incremental fetch position |

**`ingestion_runs`** ⟵ FR-1.9

`error_class` is a bounded enum-like string (`timeout`,`http_error`,`parse_error`,`blocked_url`,`auth_error`,`rate_limited`,`unknown`) so failures are aggregatable; `error_detail` holds the free-text message, truncated to 2000 chars.

### 5.3 Content

**`raw_content`** ⟵ FR-1.14, PRIV-2

| Column | Type | Null | Notes |
|---|---|---|---|
| `external_id` | `text` | yes | Source-native ID; UNIQUE with `source_id` where present |
| `body` | `text` | no | **Immutable.** As collected, after tag-stripping only ⟵ SEC-13 |
| `author_handle` | `text` | yes | Public handle only, where intrinsic to the item. Never enriched or cross-referenced ⟵ PRIV-2, PRIV-3 |
| `published_at` | `timestamptz` | yes | Source-declared; may be absent or wrong |
| `collected_at` | `timestamptz` | no | POLIS clock — the trustworthy timestamp |
| `content_hash` | `char(64)` | no | **UNIQUE.** SHA-256 of `normalized_text` ⟵ FR-2.5 |

> **Two timestamps, deliberately.** Sources lie about publication time, backdate, or omit it. Indicator windows use `COALESCE(published_at, collected_at)`, and the fallback is visible in the UI.

**`processed_content`** ⟵ FR-2.1–2.10

| Column | Type | Null | Notes |
|---|---|---|---|
| `raw_content_id` | `uuid` | no | **UNIQUE** — strict 1:1 with raw |
| `cleaned_text` | `text` | no | ML input. Casing and diacritics **preserved** ⟵ TRD §5.3 |
| `normalized_text` | `text` | no | NFKC, folded — hashing and dedup only, never ML input |
| `language_confidence` | `numeric(4,3)` | yes | CHECK 0–1 |
| `language_uncertain` | `bool` | no | `true` when confidence < 0.60 ⟵ FR-2.4 |
| `translated_text` | `text` | yes | Display only ⟵ FR-2.8 |
| `simhash` | `bigint` | yes | 64-bit; banded index for candidate retrieval |
| `cluster_id` | `uuid` | no | Near-duplicate group; a singleton is its own cluster ⟵ FR-2.6 |
| `is_canonical` | `bool` | no | First member of the cluster; the feed shows canonical only ⟵ FR-2.7 |
| `status` | `text` | no | CHECK in (`pending_analysis`,`analyzed`,`scoring_failed`,`clean_degraded`) |

### 5.4 ML

**`model_versions`** ⟵ FR-3.8, NFR-12.2

`metrics` (JSONB) has a required shape — validated by Pydantic on write:

```jsonc
{
  "pooled": {"accuracy":0.79,"macro_f1":0.72,
             "per_class":{"negative":{"precision":0.81,"recall":0.77,"f1":0.79}}},
  "per_language": {"en":{"macro_f1":0.78,"n_test":420},
                   "ar":{"macro_f1":0.66,"n_test":180},
                   "fr":{"macro_f1":0.71,"n_test":150}},
  "confusion_matrix": {"labels":["negative","neutral","positive"],
                       "matrix":[[210,30,8],[25,180,20],[6,22,140]]},
  "baseline": {"tfidf_logreg_macro_f1": 0.61},
  "notes": "Split by cluster_id to prevent near-duplicate leakage."
}
```

`per_language` is **mandatory** ⟵ NFR-12.2 — pooled-only metrics hide exactly the bias the project committed to measuring ⟵ PRIV-7.

**`nlp_results`** ⟵ FR-3.1–3.9

One row per `(processed_content_id, model_version_id)` — **UNIQUE**. Re-scoring under a new model inserts, never updates ⟵ FR-3.10. `*_scores` JSONB holds the full per-class distribution ⟵ FR-3.9; the label and confidence columns are denormalised from it for indexable filtering.

**`entities` / `content_entities`** ⟵ FR-3.6

`entities.normalized_key` is `lower(unaccent(canonical_name)) || ':' || entity_type`, **UNIQUE** — the pragmatic deduplication key. It will not merge transliteration variants across scripts (`محمد` vs `Mohammed`); that limitation is documented ⟵ PRD IND-05 false-positive note, not silently ignored.

### 5.5 Signal

**`subjects`** ⟵ FR-4.2

A first-class table rather than a `(region, topic)` string pair, because indicator scores, alerts, and baselines all reference it, and a materialised baseline needs a stable key.

`subject_key` is generated and **UNIQUE**: `region_topic:NORTH:border_security` or `region_entity:NORTH:<entity_uuid>`. Exactly one of `topic_id`/`entity_id` is set — enforced by a CHECK.

**`indicator_definitions`** ⟵ FR-4.7, FLOW §4.10

Seeded with the six PRD §10 indicators. `formula_text` and `false_positive_note` are displayed **in the product** ⟵ NFR-6.3, PRIV-6. `requires_notes_on_confirm` is `true` for IND-03 only ⟵ PRD IND-03.

**`indicator_scores`** ⟵ FR-4.3

| Column | Notes |
|---|---|
| `computed` | `false` when suppressed; `not_computed_reason` in (`below_n_min`,`insufficient_baseline`,`no_data`,`gate_not_met`) ⟵ AC-8 |
| `raw_value`…`confidence` | The full computation, stored so an alert is reproducible without re-querying content ⟵ NFR-6.1 |
| `evidence_content_ids` | `uuid[]` — capped at 50 by the writer ⟵ FR-5.4. An array, not a join table, because it is written once and read whole. |
| `component_scores` | JSONB, IND-06 only: the five contributing z-scores ⟵ PRD IND-06 |
| `alert_evaluated` | Idempotency flag for the chained alert job |

**UNIQUE** on `(indicator_id, subject_id, window_end)` — makes the scheduled job idempotent under retry.

**`alerts`** ⟵ FR-5.1–5.11

The indicator computation is **denormalised onto the alert** (`raw_value`, `baseline_mean`, `baseline_stddev`, `z_score`, `threshold_applied`, `confidence`). This is intentional duplication: an alert is evidence of what was true when a human acted on it, and a later threshold edit or baseline shift must not silently rewrite the justification an analyst saw ⟵ FLOW §4.10.

`occurrence_count` and `first_seen_at`/`last_seen_at` implement deduplication ⟵ FR-5.2. Severity may be raised on absorption, never lowered.

**`alert_evidence`** — composite PK `(alert_id, processed_content_id)`; a content item cannot be listed twice for one alert.

### 5.6 Human and Audit

**`analyst_reviews`** ⟵ FR-7.1–7.7

| Column | Notes |
|---|---|
| `target_type` | CHECK in (`alert`,`content`); exactly one of `alert_id`/`processed_content_id` set (CHECK) |
| `decision` | CHECK in (`confirmed`,`rejected`,`inconclusive`) ⟵ FLOW §6.1 |
| `notes` | ≤ 2000 chars ⟵ FR-7.2 |
| `model_version_id` | The model that produced the flag being judged — needed to attribute precision to a model ⟵ FR-7.7 |
| `supersedes_id` | Self-FK; a correction is a new row ⟵ FR-7.3, AC-13 |
| `is_current` | `false` on a superseded row; a partial unique index enforces one current review per target |
| `exported_at` | Set only by an explicit Supervisor export ⟵ FR-7.6. `NULL` means this decision has never fed any dataset — enforcing FR-3.11 at the data layer. |

**No `UPDATE` path exists in the application** except setting `is_current=false` and `exported_at` — both audited.

**`audit_logs`** ⟵ FR-8.5, SEC-21

`bigint` identity PK (append-only, high volume, no need for UUID). `detail` JSONB carries old/new values for changes — passed through the same redaction filter as logs ⟵ SEC-20; a CHECK rejects any object containing a key matching `password|secret|token|hash`.

Append-only is enforced by **role grant**, not by a trigger or by application code ⟵ AC-19.

---

## 6. SQL Schema

Abridged to the load-bearing definitions. Full DDL is generated by Alembic from the SQLAlchemy models.

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;     -- case-insensitive email
CREATE EXTENSION IF NOT EXISTS unaccent;   -- entity normalisation
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- fuzzy source/entity search

-- ─────────────── Identity ───────────────
CREATE TABLE roles (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code        text NOT NULL UNIQUE CHECK (code IN ('analyst','supervisor','admin')),
    name        text NOT NULL,
    description text
);

CREATE TABLE permissions (
    id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE,             -- 'alert:review'
    description text NOT NULL
);

CREATE TABLE role_permissions (
    role_id       uuid NOT NULL REFERENCES roles(id)       ON DELETE CASCADE,
    permission_id uuid NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name     text NOT NULL CHECK (length(full_name) BETWEEN 1 AND 200),
    email         citext NOT NULL UNIQUE CHECK (email ~ '^[^@]+@[^@]+\.[^@]+$'),
    password_hash text NOT NULL,
    role_id       uuid NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    status        text NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
    last_login_at timestamptz,
    failed_login_count int NOT NULL DEFAULT 0,
    locked_until  timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_users_role_status ON users(role_id, status);

CREATE TABLE refresh_tokens (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  char(64) NOT NULL UNIQUE,
    expires_at  timestamptz NOT NULL,
    revoked_at  timestamptz,
    replaced_by uuid REFERENCES refresh_tokens(id) ON DELETE SET NULL,
    created_ip  inet,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_refresh_active ON refresh_tokens(user_id)
    WHERE revoked_at IS NULL;              -- the only rows auth ever scans

-- ─────────────── Ingestion ───────────────
CREATE TABLE sources (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name          text NOT NULL UNIQUE,
    source_type   text NOT NULL CHECK (source_type IN ('rss','telegram','reddit','html_page')),
    url           text NOT NULL,
    language      text CHECK (language ~ '^[a-z]{2}$'),
    region        text,
    poll_minutes  int  NOT NULL DEFAULT 15 CHECK (poll_minutes BETWEEN 5 AND 1440),
    status        text NOT NULL DEFAULT 'enabled' CHECK (status IN ('enabled','disabled')),
    health_status text NOT NULL DEFAULT 'healthy'
                  CHECK (health_status IN ('healthy','degraded','unhealthy','config_error')),
    consecutive_failures int NOT NULL DEFAULT 0 CHECK (consecutive_failures >= 0),
    reliability_band text NOT NULL DEFAULT 'limited'
                  CHECK (reliability_band IN ('established','mixed','limited')),
    config        jsonb NOT NULL DEFAULT '{}'::jsonb,
    last_cursor   text,
    last_success_at timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_sources_due ON sources(status, health_status, last_success_at)
    WHERE status = 'enabled';              -- the scheduler's hot path

CREATE TABLE ingestion_runs (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id   uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    started_at  timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status      text NOT NULL CHECK (status IN ('running','success','failed','partial')),
    items_seen  int NOT NULL DEFAULT 0,
    items_new   int NOT NULL DEFAULT 0,
    items_duplicate int NOT NULL DEFAULT 0,
    error_class text CHECK (error_class IN
        ('timeout','http_error','parse_error','blocked_url','auth_error','rate_limited','unknown')),
    error_detail text CHECK (length(error_detail) <= 2000),
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);
CREATE INDEX ix_runs_source_time ON ingestion_runs(source_id, started_at DESC);

-- ─────────────── Content ───────────────
CREATE TABLE raw_content (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id     uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    external_id   text,
    url           text,
    title         text,
    body          text NOT NULL CHECK (length(body) > 0),
    author_handle text,                    -- public handle only — PRIV-2
    published_at  timestamptz,
    collected_at  timestamptz NOT NULL DEFAULT now(),
    content_hash  char(64) NOT NULL UNIQUE,
    source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE UNIQUE INDEX ux_raw_source_external ON raw_content(source_id, external_id)
    WHERE external_id IS NOT NULL;
CREATE INDEX ix_raw_source_pub ON raw_content(source_id, published_at DESC NULLS LAST);
CREATE INDEX ix_raw_effective_time
    ON raw_content(COALESCE(published_at, collected_at) DESC);   -- indicator windows

CREATE TABLE processed_content (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_content_id  uuid NOT NULL UNIQUE REFERENCES raw_content(id) ON DELETE CASCADE,
    cleaned_text    text NOT NULL,
    normalized_text text NOT NULL,
    language_code   text CHECK (language_code ~ '^[a-z]{2}$'),
    language_confidence numeric(4,3) CHECK (language_confidence BETWEEN 0 AND 1),
    language_uncertain  bool NOT NULL DEFAULT false,
    translated_text text,
    translation_model text,
    simhash         bigint,
    cluster_id      uuid NOT NULL,
    is_canonical    bool NOT NULL DEFAULT true,
    truncated       bool NOT NULL DEFAULT false,
    status          text NOT NULL DEFAULT 'pending_analysis'
        CHECK (status IN ('pending_analysis','analyzed','scoring_failed','clean_degraded')),
    processed_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_pc_pending ON processed_content(processed_at)
    WHERE status = 'pending_analysis';     -- the scoring job's queue
CREATE INDEX ix_pc_cluster  ON processed_content(cluster_id);
CREATE INDEX ix_pc_lang     ON processed_content(language_code, processed_at DESC);
CREATE INDEX ix_pc_simhash  ON processed_content(simhash) WHERE simhash IS NOT NULL;

-- Full-text over original AND translation — FR-6.4
ALTER TABLE processed_content ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(cleaned_text,'')),    'A') ||
        setweight(to_tsvector('english', coalesce(translated_text,'')),'B')
    ) STORED;
CREATE INDEX ix_pc_search ON processed_content USING GIN(search_vector);

-- ─────────────── ML ───────────────
CREATE TABLE model_versions (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_tag  text NOT NULL UNIQUE,
    base_model   text NOT NULL,
    tasks        text[] NOT NULL,
    dataset_ref  text,
    metrics      jsonb NOT NULL DEFAULT '{}'::jsonb,
    artifact_uri text,
    is_active    bool NOT NULL DEFAULT false,
    trained_at   timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_model_one_active ON model_versions((is_active)) WHERE is_active;
-- ^ Exactly one active version, enforced by the database — TRD 7.4

CREATE TABLE nlp_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    processed_content_id uuid NOT NULL REFERENCES processed_content(id) ON DELETE CASCADE,
    model_version_id     uuid NOT NULL REFERENCES model_versions(id)   ON DELETE RESTRICT,
    schema_version text NOT NULL DEFAULT '1.0',
    sentiment_label      text NOT NULL CHECK (sentiment_label IN ('negative','neutral','positive','not_applicable')),
    sentiment_confidence numeric(4,3) NOT NULL CHECK (sentiment_confidence BETWEEN 0 AND 1),
    sentiment_scores     jsonb NOT NULL,
    hostility_label      text NOT NULL CHECK (hostility_label IN ('none','hostile_rhetoric','threatening_language','not_applicable')),
    hostility_confidence numeric(4,3) NOT NULL CHECK (hostility_confidence BETWEEN 0 AND 1),
    hostility_scores     jsonb NOT NULL,
    disinfo_label        text NOT NULL CHECK (disinfo_label IN ('likely_reliable','uncertain','likely_unreliable','not_applicable')),
    disinfo_confidence   numeric(4,3) NOT NULL CHECK (disinfo_confidence BETWEEN 0 AND 1),
    disinfo_scores       jsonb NOT NULL,
    stance_label         text NOT NULL DEFAULT 'not_applicable'
        CHECK (stance_label IN ('supportive','neutral','opposed','not_applicable')),
    stance_confidence    numeric(4,3) NOT NULL DEFAULT 0,
    stance_scores        jsonb NOT NULL DEFAULT '{}'::jsonb,
    inference_ms int,
    created_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ux_nlp_content_model UNIQUE (processed_content_id, model_version_id)
);
CREATE INDEX ix_nlp_hostility ON nlp_results(hostility_label, created_at DESC)
    WHERE hostility_label <> 'none';       -- IND-01's aggregate
CREATE INDEX ix_nlp_disinfo   ON nlp_results(disinfo_label, created_at DESC)
    WHERE disinfo_label = 'likely_unreliable';   -- IND-04's aggregate
CREATE INDEX ix_nlp_content   ON nlp_results(processed_content_id);

CREATE TABLE entities (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name text NOT NULL,
    entity_type    text NOT NULL CHECK (entity_type IN ('PERSON','ORG','GPE','LOC','EVENT')),
    normalized_key text NOT NULL UNIQUE,
    is_watchlisted bool NOT NULL DEFAULT false,
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_entities_trgm ON entities USING GIN(canonical_name gin_trgm_ops);

CREATE TABLE content_entities (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    processed_content_id uuid NOT NULL REFERENCES processed_content(id) ON DELETE CASCADE,
    entity_id            uuid NOT NULL REFERENCES entities(id)          ON DELETE CASCADE,
    model_version_id     uuid NOT NULL REFERENCES model_versions(id)    ON DELETE RESTRICT,
    surface_form text NOT NULL,
    char_start   int  NOT NULL CHECK (char_start >= 0),
    char_end     int  NOT NULL,
    confidence   numeric(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    CHECK (char_end > char_start)
);
CREATE INDEX ix_ce_entity_content ON content_entities(entity_id, processed_content_id);
CREATE INDEX ix_ce_content        ON content_entities(processed_content_id);

CREATE TABLE topics (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE,
    name text NOT NULL,
    description text,
    is_active bool NOT NULL DEFAULT true
);

CREATE TABLE content_topics (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    processed_content_id uuid NOT NULL REFERENCES processed_content(id) ON DELETE CASCADE,
    topic_id             uuid NOT NULL REFERENCES topics(id)            ON DELETE RESTRICT,
    model_version_id     uuid NOT NULL REFERENCES model_versions(id)    ON DELETE RESTRICT,
    confidence numeric(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    CONSTRAINT ux_content_topic UNIQUE (processed_content_id, topic_id, model_version_id)
);
CREATE INDEX ix_ct_topic ON content_topics(topic_id, processed_content_id);

-- ─────────────── Signal ───────────────
CREATE TABLE subjects (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_type text NOT NULL CHECK (subject_type IN ('region_topic','region_entity')),
    region    text NOT NULL,
    topic_id  uuid REFERENCES topics(id)   ON DELETE CASCADE,
    entity_id uuid REFERENCES entities(id) ON DELETE CASCADE,
    subject_key text NOT NULL UNIQUE,
    label     text NOT NULL,
    is_active bool NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((subject_type='region_topic'  AND topic_id  IS NOT NULL AND entity_id IS NULL)
        OR (subject_type='region_entity' AND entity_id IS NOT NULL AND topic_id  IS NULL))
);

CREATE TABLE indicator_definitions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE CHECK (code ~ '^IND-[0-9]{2}$'),
    name text NOT NULL,
    definition   text NOT NULL,
    formula_text text NOT NULL,            -- displayed in-product — NFR-6.3
    family text NOT NULL CHECK (family IN
        ('language','tone','structure','reliability','volume','composite')),
    threshold numeric(6,3) NOT NULL CHECK (threshold > 0),
    n_min     int NOT NULL CHECK (n_min > 0),
    max_severity text NOT NULL DEFAULT 'critical'
        CHECK (max_severity IN ('informational','low','medium','high','critical')),
    false_positive_note text NOT NULL,     -- displayed in-product — PRIV-6
    requires_notes_on_confirm bool NOT NULL DEFAULT false,
    is_enabled bool NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE indicator_scores (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    indicator_id uuid NOT NULL REFERENCES indicator_definitions(id) ON DELETE RESTRICT,
    subject_id   uuid NOT NULL REFERENCES subjects(id)              ON DELETE CASCADE,
    window_start timestamptz NOT NULL,
    window_end   timestamptz NOT NULL,
    computed     bool NOT NULL DEFAULT true,
    not_computed_reason text CHECK (not_computed_reason IN
        ('below_n_min','insufficient_baseline','no_data','gate_not_met')),
    raw_value       numeric(10,5),
    baseline_mean   numeric(10,5),
    baseline_stddev numeric(10,5),
    z_score         numeric(8,3),
    threshold_applied numeric(6,3),
    severity        text CHECK (severity IN
        ('normal','informational','low','medium','high','critical')),
    confidence      numeric(4,3) CHECK (confidence BETWEEN 0 AND 1),
    n_current int NOT NULL DEFAULT 0,
    n_sources int NOT NULL DEFAULT 0,
    evidence_content_ids uuid[] NOT NULL DEFAULT '{}',
    component_scores jsonb,                -- IND-06 only
    alert_evaluated  bool NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (window_end > window_start),
    CHECK (computed = true OR not_computed_reason IS NOT NULL),
    CHECK (cardinality(evidence_content_ids) <= 50),      -- FR-5.4
    CONSTRAINT ux_score_window UNIQUE (indicator_id, subject_id, window_end)
);
CREATE INDEX ix_scores_pending_alert ON indicator_scores(created_at)
    WHERE computed AND NOT alert_evaluated
      AND severity IN ('low','medium','high','critical');  -- alert job's queue
CREATE INDEX ix_scores_trend ON indicator_scores(subject_id, indicator_id, window_end DESC);

CREATE TABLE alerts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    indicator_id uuid NOT NULL REFERENCES indicator_definitions(id) ON DELETE RESTRICT,
    subject_id   uuid NOT NULL REFERENCES subjects(id)              ON DELETE RESTRICT,
    triggering_score_id uuid NOT NULL REFERENCES indicator_scores(id) ON DELETE RESTRICT,
    severity text NOT NULL CHECK (severity IN ('low','medium','high','critical')),
    status   text NOT NULL DEFAULT 'new' CHECK (status IN
        ('new','acknowledged','under_review',
         'resolved_confirmed','resolved_rejected','resolved_inconclusive')),
    explanation text NOT NULL,             -- includes the mandatory non-prediction clause
    raw_value numeric(10,5) NOT NULL,
    baseline_mean numeric(10,5) NOT NULL,
    baseline_stddev numeric(10,5) NOT NULL,
    z_score numeric(8,3) NOT NULL,
    threshold_applied numeric(6,3) NOT NULL,
    confidence numeric(4,3) NOT NULL,
    n_items   int NOT NULL,
    n_sources int NOT NULL,
    occurrence_count int NOT NULL DEFAULT 1 CHECK (occurrence_count >= 1),
    claimed_by uuid REFERENCES users(id) ON DELETE SET NULL,
    claimed_at timestamptz,
    acknowledged_by uuid REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at timestamptz,
    resolved_by uuid REFERENCES users(id) ON DELETE SET NULL,
    resolved_at timestamptz,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at  timestamptz NOT NULL DEFAULT now(),
    created_at    timestamptz NOT NULL DEFAULT now(),
    CHECK (status NOT LIKE 'resolved%' OR (resolved_at IS NOT NULL AND resolved_by IS NOT NULL))
);
-- At most ONE open alert per (indicator, subject) — makes FR-5.2 dedup race-proof
CREATE UNIQUE INDEX ux_alert_open ON alerts(indicator_id, subject_id)
    WHERE status IN ('new','acknowledged','under_review');
CREATE INDEX ix_alerts_queue ON alerts(status, severity DESC, created_at DESC);
CREATE INDEX ix_alerts_claimed ON alerts(claimed_by) WHERE claimed_by IS NOT NULL;

CREATE TABLE alert_evidence (
    alert_id uuid NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    processed_content_id uuid NOT NULL REFERENCES processed_content(id) ON DELETE CASCADE,
    contribution numeric(6,4),
    added_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (alert_id, processed_content_id)
);
CREATE INDEX ix_evidence_content ON alert_evidence(processed_content_id);

-- ─────────────── Human ───────────────
CREATE TABLE analyst_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    target_type text NOT NULL CHECK (target_type IN ('alert','content')),
    alert_id uuid REFERENCES alerts(id) ON DELETE RESTRICT,
    processed_content_id uuid REFERENCES processed_content(id) ON DELETE RESTRICT,
    reviewer_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    decision text NOT NULL CHECK (decision IN ('confirmed','rejected','inconclusive')),
    notes text CHECK (length(notes) <= 2000),
    model_version_id uuid REFERENCES model_versions(id) ON DELETE SET NULL,
    supersedes_id uuid REFERENCES analyst_reviews(id) ON DELETE RESTRICT,
    is_current  bool NOT NULL DEFAULT true,
    exported_at timestamptz,               -- NULL = has never fed a dataset (FR-3.11)
    created_at  timestamptz NOT NULL DEFAULT now(),
    CHECK ((target_type='alert'   AND alert_id IS NOT NULL AND processed_content_id IS NULL)
        OR (target_type='content' AND processed_content_id IS NOT NULL AND alert_id IS NULL))
);
CREATE UNIQUE INDEX ux_review_current_alert   ON analyst_reviews(alert_id)
    WHERE is_current AND target_type='alert';
CREATE UNIQUE INDEX ux_review_current_content ON analyst_reviews(processed_content_id)
    WHERE is_current AND target_type='content';
CREATE INDEX ix_reviews_reviewer ON analyst_reviews(reviewer_id, created_at DESC);
CREATE INDEX ix_reviews_precision ON analyst_reviews(decision, created_at DESC)
    WHERE is_current;                      -- FR-7.5 precision aggregate

CREATE TABLE review_exports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    requested_by uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    period_start timestamptz NOT NULL,
    period_end   timestamptz NOT NULL,
    record_count int NOT NULL,
    content_hash char(64) NOT NULL,        -- reproducibility of the artefact
    artifact_uri text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- ─────────────── Audit ───────────────
CREATE TABLE audit_logs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id uuid REFERENCES users(id) ON DELETE SET NULL,   -- NULL for system
    actor_type text NOT NULL DEFAULT 'user' CHECK (actor_type IN ('user','system')),
    action text NOT NULL,                  -- 'alert.resolved', 'indicator.threshold_changed'
    resource_type text NOT NULL,
    resource_id   text,
    result text NOT NULL CHECK (result IN ('success','denied','failure')),
    detail jsonb NOT NULL DEFAULT '{}'::jsonb,
    request_id uuid,
    source_ip  inet,
    created_at timestamptz NOT NULL DEFAULT now(),
    -- Defence in depth: reject any attempt to persist secret-shaped keys — SEC-20
    CHECK (NOT (detail::text ~* '"(password|secret|token|api_key|password_hash)"'))
);
CREATE INDEX ix_audit_actor    ON audit_logs(actor_id, created_at DESC);
CREATE INDEX ix_audit_action   ON audit_logs(action, created_at DESC);
CREATE INDEX ix_audit_resource ON audit_logs(resource_type, resource_id, created_at DESC);
CREATE INDEX ix_audit_denied   ON audit_logs(created_at DESC) WHERE result = 'denied';
```

### 6.1 Cascade Behaviour Rationale

| Relationship | Behaviour | Why |
|---|---|---|
| `raw_content` → `processed_content` | `CASCADE` | Processed data is meaningless without its raw source; retention purge removes both together |
| `processed_content` → `nlp_results`, `content_entities`, `content_topics` | `CASCADE` | Derived from content; no independent meaning |
| `sources` → `raw_content` | **`RESTRICT`** | A source with collected content cannot be deleted — it would orphan evidence. Sources are disabled, never deleted. |
| `model_versions` → `nlp_results` | **`RESTRICT`** | A model that produced results is permanently referenced. Deleting it would destroy attribution ⟵ Principle 2. |
| `users` → `analyst_reviews`, `audit_logs` | **`RESTRICT`** / `SET NULL` | Decisions and audit records outlive accounts ⟵ FR-8.4 |
| `alerts` → `analyst_reviews` | **`RESTRICT`** | A reviewed alert cannot be deleted |
| `alerts` → `alert_evidence` | `CASCADE` | Link table only |
| `indicator_definitions` → anything | **`RESTRICT`** | Six seeded definitions are permanent; disabled via `is_enabled` |

**The pattern:** anything a human acted on, or that attributes a machine output, is `RESTRICT`. Only pure derivations cascade.

---

## 7. Index Strategy

Indexes are justified by a specific query, not added speculatively.

| Index | Serves | Query pattern |
|---|---|---|
| `ix_sources_due` (partial) | Scheduler ⟵ TRD §6.2 | `WHERE status='enabled' AND due` — the most frequent query in the system |
| `ix_pc_pending` (partial) | Scoring job | `WHERE status='pending_analysis'` — indexes only the queue, not 50k analysed rows |
| `ix_pc_search` (GIN) | Search ⟵ FR-6.4 | `search_vector @@ plainto_tsquery(:q)` |
| `ix_pc_simhash` | Dedup ⟵ FR-2.6 | Candidate retrieval within the 7-day window |
| `ix_raw_effective_time` (expression) | Indicator windows | `COALESCE(published_at, collected_at)` — without the expression index this is a sequential scan |
| `ix_nlp_hostility` (partial) | IND-01 | Only non-`none` rows; ~15% of the table |
| `ix_nlp_disinfo` (partial) | IND-04 | Only `likely_unreliable` rows |
| `ux_nlp_content_model` | Idempotency ⟵ FR-3.10 | Prevents double-scoring under retry |
| `ix_scores_pending_alert` (partial) | Alert job | Only unevaluated, alert-worthy scores |
| `ix_scores_trend` | Trend charts ⟵ FR-4.6 | `(subject, indicator, window_end DESC)` |
| `ux_alert_open` (partial unique) | Dedup ⟵ FR-5.2 | **Race-proof at the database level** — the app catches the violation and absorbs |
| `ix_alerts_queue` | Alert Center ⟵ FR-6.7 | `(status, severity DESC, created_at DESC)` matches the default sort exactly |
| `ix_reviews_precision` (partial) | Precision ⟵ FR-7.5 | Only current decisions |
| `ix_audit_denied` (partial) | Security review ⟵ Phase 8 | Denials are a small fraction of a large table |
| `ix_entities_trgm` (GIN) | Entity autocomplete | Fuzzy prefix matching |

**Nine of these are partial indexes.** On free-tier storage this matters: indexing only the rows a query actually touches keeps the index resident in cache and the write cost low.

### 7.1 Query Patterns and Targets

| Query | Endpoint | Index | Target ⟵ NFR-1.2 |
|---|---|---|---|
| Due sources | scheduler | `ix_sources_due` | < 5 ms |
| Content feed page | `GET /content` | `ix_pc_lang` + FK | < 200 ms |
| Full-text search | `GET /content/search` | `ix_pc_search` | < 500 ms |
| Content detail (single round trip) | `GET /content/{id}` | PK + FK indexes | < 150 ms |
| Alert queue | `GET /alerts` | `ix_alerts_queue` | < 150 ms |
| Alert detail + evidence | `GET /alerts/{id}` | PK + `alert_evidence` PK | < 200 ms |
| Indicator trend (30d) | `GET /indicators/trends` | `ix_scores_trend` | < 300 ms |
| Dashboard summary | `GET /dashboard/summary` | several partials | < 400 ms |
| Precision by indicator | `GET /alerts/stats` | `ix_reviews_precision` | < 300 ms |

Pagination is **keyset by `(created_at, id)`** on the high-volume list endpoints (`/content`, `/alerts`) — `OFFSET 5000` degrades linearly and is exactly what a bored analyst does at 4pm. Page numbers remain in the API surface; the driver underneath is a cursor.

### 7.2 Materialised Baseline

Recomputing 14-day baselines per subject per indicator on every 30-minute run is the schema's one genuine performance risk.

```sql
CREATE MATERIALIZED VIEW mv_subject_daily_stats AS
SELECT s.id AS subject_id,
       date_trunc('day', COALESCE(rc.published_at, rc.collected_at)) AS day,
       count(*) AS n_items,
       count(DISTINCT rc.source_id) AS n_sources,
       avg((nr.sentiment_scores->>'positive')::numeric
         - (nr.sentiment_scores->>'negative')::numeric) AS mean_polarity,
       avg(CASE WHEN nr.hostility_label IN ('hostile_rhetoric','threatening_language')
                THEN 1 ELSE 0 END)::numeric AS hostile_rate,
       avg(CASE WHEN nr.disinfo_label = 'likely_unreliable'
                THEN 1 ELSE 0 END)::numeric AS unreliable_rate
FROM subjects s
JOIN content_topics ct ON ct.topic_id = s.topic_id
JOIN processed_content pc ON pc.id = ct.processed_content_id
JOIN raw_content rc ON rc.id = pc.raw_content_id
JOIN nlp_results nr ON nr.processed_content_id = pc.id
JOIN model_versions mv ON mv.id = nr.model_version_id AND mv.is_active
WHERE pc.is_canonical                       -- duplicates counted once — IND-01 mitigation
GROUP BY s.id, 2;

CREATE UNIQUE INDEX ux_mv_subject_day ON mv_subject_daily_stats(subject_id, day);
-- REFRESH MATERIALIZED VIEW CONCURRENTLY hourly — TRD 6.2 refresh_baselines
```

`WHERE pc.is_canonical` implements the PRD IND-01 mitigation ("counting duplicate clusters once") at the data layer, so every indicator inherits it rather than each reimplementing it.

---

## 8. SQLAlchemy Model Structure

```python
# backend/models/base.py
class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False)
```

```python
# backend/models/content.py — relationship shape (abridged)
class RawContent(Base):
    __tablename__ = "raw_content"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"))
    body: Mapped[str]
    content_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    published_at: Mapped[datetime | None]
    collected_at: Mapped[datetime] = mapped_column(server_default=func.now())

    source: Mapped["Source"] = relationship(back_populates="raw_items", lazy="joined")
    processed: Mapped["ProcessedContent | None"] = relationship(
        back_populates="raw", cascade="all, delete-orphan", uselist=False)

class ProcessedContent(Base):
    __tablename__ = "processed_content"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    raw_content_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_content.id", ondelete="CASCADE"), unique=True)
    cluster_id: Mapped[UUID]
    is_canonical: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(default="pending_analysis")

    raw: Mapped["RawContent"] = relationship(back_populates="processed")
    # selectin, not lazy: the content-detail endpoint loads these together in one
    # round trip (TRD 12.4). Default lazy loading here is the classic N+1 on the feed.
    nlp_results:  Mapped[list["NlpResult"]]      = relationship(lazy="selectin")
    entity_links: Mapped[list["ContentEntity"]]  = relationship(lazy="selectin")
    topic_links:  Mapped[list["ContentTopic"]]   = relationship(lazy="selectin")
```

### 8.1 Loading Strategy

| Relationship | Strategy | Why |
|---|---|---|
| `RawContent.source` | `joined` | Always displayed with the item; one extra join beats a second query |
| `ProcessedContent.nlp_results` | `selectin` | Feed of 25 items → 2 queries, not 26 |
| `ProcessedContent.entity_links` | `selectin` | Same |
| `Alert.evidence` | `selectin` + explicit `limit` | Evidence is paginated ⟵ FR-5.4 |
| `Alert.reviews` | `lazy="raise"` | Loading review history on a **list** page is always a bug — `raise` turns it into a test failure instead of a slow endpoint |
| `User.role` | `joined` | Needed on every authenticated request |

`lazy="raise"` on the expensive relationships is a deliberate guard: an accidental N+1 fails loudly in tests rather than quietly in the demo.

---

## 9. Pydantic Schema Structure

```
backend/schemas/
├── common.py     Page[T], ErrorResponse, TimestampedBase
├── auth.py       LoginRequest, TokenResponse, ChangePasswordRequest
├── user.py       UserCreateRequest, UserUpdateRequest, UserResponse
├── source.py     SourceCreateRequest, SourceUpdateRequest, SourceResponse,
│                 SourceDetailResponse, SourceHealthSummary, IngestionRunResponse
├── content.py    ContentQuery, ContentListItem, ContentDetailResponse,
│                 ContentSearchResult
├── analysis.py   NlpResultResponse, ClassificationBlock, EntityMention,
│                 TopicAssignment, AnalysisStatsResponse
├── indicator.py  IndicatorDefinitionResponse, IndicatorUpdateRequest,
│                 IndicatorScoreResponse, IndicatorTrendResponse
├── alert.py      AlertListItem, AlertDetailResponse, AlertResolveRequest,
│                 AlertStatsResponse
├── review.py     ReviewCreateRequest, ReviewResponse, ReviewExportRequest
├── model.py      ModelVersionResponse, ModelVersionDetailResponse, ModelMetrics
└── audit.py      AuditLogResponse, AuditQuery
```

```python
# backend/schemas/common.py
class PolisBase(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)  # SEC-10

T = TypeVar("T")
class Page(PolisBase, Generic[T]):
    items: list[T]
    page: int; size: int; total: int; pages: int
    has_next: bool; has_prev: bool
```

```python
# backend/schemas/analysis.py — mirrors the score_text contract (PRD 9.1)
class ClassificationBlock(PolisBase):
    label: str
    confidence: float = Field(ge=0, le=1)
    scores: dict[str, float]
    is_low_confidence: bool          # computed: confidence < MODEL_CONFIDENCE_FLOOR (FR-3.12)

class NlpResultResponse(PolisBase):
    id: UUID
    model_version: str               # ALWAYS present — FR-6.9, AC-24
    model_version_id: UUID
    sentiment: ClassificationBlock
    hostility: ClassificationBlock
    disinfo:   ClassificationBlock
    stance:    ClassificationBlock
    entities: list[EntityMention]
    topics:   list[TopicAssignment]
    created_at: datetime
```

```python
# backend/schemas/user.py — the response model CANNOT leak the hash:
class UserResponse(PolisBase):
    id: UUID
    full_name: str
    email: EmailStr
    role: str
    status: str
    last_login_at: datetime | None
    created_at: datetime
    # password_hash is absent. With extra="forbid" and from_attributes,
    # a field not declared here can never appear in a response. A test asserts
    # that "password" appears in no serialised response body anywhere.
```

### 9.1 Request/Response Naming Convention

| Suffix | Meaning |
|---|---|
| `…Request` | Inbound body |
| `…Query` | Inbound query parameters |
| `…Response` | Outbound single object |
| `…ListItem` | Outbound list row — deliberately lighter than `…Response` |
| `…DetailResponse` | Outbound single object with relations expanded |
| `Page[T]` | Paginated envelope |

`ListItem` and `DetailResponse` are separate types on purpose: the feed does not need per-class score distributions, and shipping them would multiply the payload for 25 rows.

---

## 10. API ↔ Entity Mapping

| Endpoint group | Primary tables | Writes | Audited |
|---|---|---|---|
| `/auth` | `users`, `refresh_tokens` | `refresh_tokens`, `users.last_login_at` | ✅ all outcomes |
| `/users` | `users`, `roles` | `users`, `refresh_tokens` (revoke) | ✅ |
| `/sources` | `sources`, `ingestion_runs` | `sources`, `ingestion_runs` | ✅ create/update/disable/fetch-now |
| `/content` | `processed_content`, `raw_content`, `sources`, `nlp_results` | — | ❌ (read) |
| `/content/search` | `processed_content.search_vector` | — | ❌ |
| `/analysis` | `nlp_results`, `entities`, `topics`, `model_versions` | `nlp_results` (rescore) | ✅ rescore |
| `/indicators` | `indicator_definitions`, `indicator_scores`, `subjects` | `indicator_definitions` | ✅ threshold change (old + new) |
| `/alerts` | `alerts`, `alert_evidence`, `indicator_definitions`, `subjects` | `alerts` | ✅ every transition |
| `/reviews` | `analyst_reviews`, `review_exports` | `analyst_reviews`, `review_exports` | ✅ |
| `/models` | `model_versions` | `model_versions.is_active` | ✅ activation |
| `/audit` | `audit_logs` | — | ❌ (reading audit is not itself audited — that recurses) |
| `/dashboard` | aggregates | — | ❌ |
| `/health` | connectivity checks | — | ❌ |

Every table in §3 is reachable through at least one endpoint, and every endpoint in TRD §12 maps to tables here. No orphans in either direction.

---

## 11. Database Security

### 11.1 Role Separation ⟵ SEC-9, SEC-21

```sql
-- Owner role: migrations only. Credentials live outside the application env.
CREATE ROLE polis_owner LOGIN;

-- Application role: DML only, no DDL, and no mutation of audit_logs.
CREATE ROLE polis_app LOGIN;
GRANT CONNECT ON DATABASE polis TO polis_app;
GRANT USAGE  ON SCHEMA public   TO polis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO polis_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO polis_app;

REVOKE UPDATE, DELETE ON audit_logs FROM polis_app;   -- append-only — AC-19
REVOKE UPDATE, DELETE ON raw_content FROM polis_app;  -- immutable — Principle 1
-- (retention purge runs as polis_owner in a scheduled maintenance job)

ALTER DEFAULT PRIVILEGES FOR ROLE polis_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO polis_app;

-- Read-only role for evaluation/marking access.
CREATE ROLE polis_readonly LOGIN;
GRANT CONNECT ON DATABASE polis TO polis_readonly;
GRANT USAGE ON SCHEMA public TO polis_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO polis_readonly;
REVOKE SELECT ON users FROM polis_readonly;   -- password hashes not exposed
```

> **`AC-19` is satisfied by the grant, not by a trigger.** An application bug, a compromised session, or a careless migration cannot delete audit history, because the role it connects as has no such privilege.

### 11.2 Row-Level Security **[PROPOSED — evaluate Week 10]**

Application-level RBAC (TRD §5.9) is the primary control and is sufficient for a single-tenant FYP. RLS is designed for but not enabled at MVP, because it adds a second policy surface that can silently disagree with the first — a real risk with one backend developer.

```sql
-- Prepared, not enabled at MVP. Enable if a read-only external role gains DB access.
ALTER TABLE analyst_reviews ENABLE ROW LEVEL SECURITY;
CREATE POLICY reviews_own_or_privileged ON analyst_reviews FOR SELECT
    USING (reviewer_id = current_setting('polis.user_id', true)::uuid
           OR current_setting('polis.can_read_all_reviews', true) = 'true');
```

**[TBD-15 — Team C, Week 10:** enable RLS, or document why application-layer RBAC alone is the deliberate choice.**]**

### 11.3 Controls Summary

| Control | Implementation |
|---|---|
| SQL injection ⟵ SEC-11 | ORM / bound parameters only; CI grep against string-built SQL; `plainto_tsquery(:q)` never interpolated |
| Credential protection ⟵ SEC-17 | `DATABASE_URL` from env; never logged; never in a response; `.env` git-ignored |
| Least privilege ⟵ SEC-9 | Three roles above; app role has no DDL |
| Encryption at rest ⟵ SEC-23 | Provided by Supabase/host. No application-level encryption: no sensitive personal data is stored ⟵ PRIV-2, and the justification is documented rather than assumed |
| Encryption in transit | `sslmode=require` in the connection string |
| Password storage ⟵ SEC-1 | Argon2id hash only; never selected into a response schema |
| Token storage ⟵ SEC-5 | SHA-256 hash only; the token itself never persists |
| Audit integrity ⟵ SEC-21 | Append-only by grant |
| Raw-content integrity | `UPDATE`/`DELETE` revoked from the app role |
| Input constraints | CHECK constraints mirror Pydantic validators — the database is the last line of defence |
| Backup security | Supabase automated backups; local `pg_dump` encrypted at rest and **never committed** — `.gitignore` covers `*.sql`, `*.dump` |
| Connection pooling | SQLAlchemy pool sized 5 + 5 overflow ⟵ free-tier connection limit |

---

## 12. Data Retention

**[PROPOSED — project decision, not a legal requirement]** ⟵ PRD PRIV-4. The FYP report must state this explicitly: these periods are chosen by the team for a demonstration system, and POLIS makes no claim about statutory retention obligations in any jurisdiction.

| Data | Retain | Then | Rationale |
|---|---|---|---|
| `raw_content` + `processed_content` | 180 days | Hard delete (cascades) | Beyond the demo horizon; minimises stored public content ⟵ PRIV-2 |
| `nlp_results` | 365 days | Delete | Kept longer than content for evaluation reproducibility |
| `indicator_scores` | 365 days | Delete | Needed for threshold-change impact analysis ⟵ FLOW §4.10 |
| `alerts` | **Project duration** | Retain | Academic evidence of system behaviour |
| `analyst_reviews` | **Project duration** | Retain | The human decisions are the record ⟵ Principle 3 |
| `audit_logs` | 365 days | Delete | Security evidence |
| `ingestion_runs` | 90 days | Delete | Operational only |
| `refresh_tokens` | 30 days past expiry | Delete | Revocation history no longer useful |
| `model_versions` | **Permanent** | Retain | Attribution must survive ⟵ Principle 2 |

```sql
-- Runs daily 03:00 as polis_owner — TRD 6.2 purge_expired
DELETE FROM raw_content
 WHERE collected_at < now() - (SELECT (value||' days')::interval
                                 FROM app_settings WHERE key='retain_raw_days');
-- processed_content, nlp_results, content_entities, content_topics cascade.
-- alerts, analyst_reviews, audit_logs are NOT touched: their FKs to content are
-- RESTRICT-protected, and evidence links to purged content render in the UI as
-- "source content retained until <date>, since removed under the retention policy" —
-- honest about the gap rather than showing a broken link.
```

> **The retention/evidence tension, stated plainly.** Purging content after 180 days means an alert older than that loses the text behind it. The alternative — retaining everything forever — contradicts data minimisation ⟵ PRIV-2. POLIS resolves it by retaining the *alert, its computation, and the decision* permanently while letting the underlying public content expire, and by showing the gap in the UI instead of hiding it. This trade-off belongs in the FYP report.

---

## 13. Migration Strategy

| Aspect | Approach |
|---|---|
| Tool | Alembic 1.13 |
| Naming | `NNNN_short_description.py` — sequential, reviewable in a PR diff |
| Generation | `alembic revision --autogenerate` then **hand-edited** — autogenerate misses CHECK constraints, partial indexes, generated columns, and grants, all of which POLIS relies on |
| Review | Every migration is reviewed by a second person ⟵ SEC-28 |
| Downgrade | Every migration implements `downgrade()`. A migration that cannot be reversed must say so in a comment with a reason. |
| Execution role | `polis_owner`. The application role has no DDL ⟵ SEC-9 |
| Data migrations | Separate revisions from schema migrations — never mixed, so a schema rollback does not strand data |
| CI | `alembic upgrade head` then `alembic downgrade -1` then `upgrade head` runs against an ephemeral database on every PR |

### 13.1 Planned Migrations

| # | Migration | Week |
|---|---|---|
| 0001 | Extensions, roles, permissions, role_permissions, users, refresh_tokens | 3 |
| 0002 | sources, ingestion_runs | 3 |
| 0003 | raw_content, processed_content (+ search_vector, GIN) | 3 |
| 0004 | model_versions, nlp_results, entities, content_entities, topics, content_topics | 3 |
| 0005 | subjects, indicator_definitions, indicator_scores | 4 |
| 0006 | alerts, alert_evidence | 4 |
| 0007 | analyst_reviews, review_exports | 4 |
| 0008 | audit_logs + grants (append-only) | 4 |
| 0009 | Seed: roles, permissions, role_permissions, topics, 6 indicator definitions | 4 |
| 0010 | `mv_subject_daily_stats` + refresh function | 8 |
| 0011 | Post-measurement index tuning **[reserved]** | 12 |

### 13.2 Environments

| Env | Database | Migration path | Seed |
|---|---|---|---|
| Local | Docker Postgres 15 | `alembic upgrade head` | Full demo seed |
| Test (CI) | Ephemeral service container | Applied per test session | Minimal fixtures |
| Demo/Staging | Supabase free | Applied manually after PR merge | Demo seed + real ingestion |
| Presentation | Local Postgres | Restored from a rehearsed dump | Curated corpus ⟵ TRD §10.3 |

---

## 14. Test Data Strategy

| Layer | Approach |
|---|---|
| Unit | Factory functions (`tests/factories.py`), no database — pure objects |
| Integration | Ephemeral Postgres per session; each test in a transaction rolled back at teardown — no cross-test leakage |
| Seed (`python -m backend.seed`) | 3 roles, ~25 permissions, mappings, 3 demo users (one per role), ~20 topics, 6 indicator definitions, 8 sources, 1 stub model version |
| Demo seed (`--demo`) | The above plus ~500 synthetic content items across 4 languages spanning 21 days, with a **deliberately planted spike** in one subject so every indicator can be demonstrated firing |
| Fixture corpus | ~200 real ingested items, anonymised where needed, committed as JSONL for reproducible tests. Its provenance and licence status are documented ⟵ PRD dataset docs |
| Security fixtures | Items containing XSS payloads, oversized bodies, malformed Unicode, bidi-override characters, and sources pointing at internal addresses ⟵ TRD §14.9 |
| Indicator fixtures | Hand-computed statistics matching the PRD §10 worked examples exactly, so a formula regression fails a test rather than shipping ⟵ TRD §16.1 |

```python
# tests/factories.py — deterministic, no faker dependency for core paths
def make_content(session, *, subject: Subject, hostile: bool = False,
                 published_at: datetime | None = None, source: Source | None = None):
    """Create raw + processed + nlp rows in one call. The workhorse of every
    integration test — building these by hand in each test is how fixtures rot."""
```

### 14.1 The Planted Spike

The demo seed constructs one subject whose 14-day baseline is quiet and whose final 24 hours contain a hostility spike that exceeds `n_min` and crosses the IND-01 threshold, plus a near-duplicate cluster across 5 sources within 3 hours to fire IND-03. This is **labelled in the seed script and in the demo narration as synthetic** — presenting generated data as observed activity would misrepresent the system's performance ⟵ PRD R-17.

---

## 15. Schema Acceptance Criteria

| ID | Criterion | Verified by |
|---|---|---|
| DBAC-1 | Every FK has an explicit `ON DELETE` behaviour, justified in §6.1 | Schema review |
| DBAC-2 | Every enum-like column has a CHECK constraint matching its Pydantic `Literal` | Test comparing both sets |
| DBAC-3 | `audit_logs` rejects `UPDATE` and `DELETE` as `polis_app` | Security test ⟵ AC-19 |
| DBAC-4 | `raw_content` rejects `UPDATE` and `DELETE` as `polis_app` | Security test |
| DBAC-5 | At most one `is_active` model version, enforced by index | Constraint test |
| DBAC-6 | At most one open alert per (indicator, subject), enforced by index | Concurrency test ⟵ FR-5.2 |
| DBAC-7 | At most one current review per target, enforced by index | Constraint test |
| DBAC-8 | Re-running the scoring job produces no duplicate `nlp_results` | Idempotency test ⟵ FR-3.10 |
| DBAC-9 | Re-running the indicator job produces no duplicate `indicator_scores` | Idempotency test |
| DBAC-10 | No response schema anywhere serialises `password_hash` or `token_hash` | Test grepping all serialised responses |
| DBAC-11 | Every migration upgrades and downgrades cleanly | CI |
| DBAC-12 | Feed query on 50k rows returns page 1 in < 200 ms | Load test ⟵ NFR-1.2 |
| DBAC-13 | Search on 50k rows returns in < 500 ms | Load test |
| DBAC-14 | Retention purge deletes content without touching alerts, reviews, or audit | Integration test |
| DBAC-15 | Every table in §3 is reachable through at least one API endpoint | Traceability review |
| DBAC-16 | Seeded indicator definitions match PRD §10 exactly (threshold, `n_min`, cap, FP note) | Test comparing seed to a PRD-derived fixture |

---

*End of Document 5 — Backend Schema. Next: Implementation Plan (POLIS-IMPL-006).*
