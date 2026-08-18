# POLIS — Data Source & Governance Register

**Political Open Source Language Intelligence System**

---

## 1. Document Control

| Field | Value |
|---|---|
| Document ID | POLIS-DOC-014 |
| Version | 1.0 |
| Date | 11 August 2026 |
| Status | **Live — eight named feeds recorded in §2**, each probed 2026-08-13. Two terms checks remain open (GOV-9/TBD-21) and block first ingest |
| Owner | Team A (Data/Ingestion) |
| Derives from | POLIS-PRD-001 §9 FR-1.x (ingestion), §13 (PRIV-1…PRIV-13); POLIS-TRD-002 §5.1–5.2 (source adapters, SSRF guard); POLIS-DB-005 §5.2 (`sources` table) |

This is a live register. As Team A configures real sources (Implementation Plan Phase 2, Weeks 2–5), each row moves from `[TBD]` (category defined, instance not yet chosen) to a concrete entry with a verified `robots.txt`/terms check. **No source is added to the live system before this table records it.**

---

## 2. Source Register

**Demo languages: Arabic, English, French** ⟵ TBD-1, DOC-007 §4.1.

Every feed below was probed on **2026-08-13** with POLIS's own User-Agent. All eight returned **HTTP 200** with an RSS content type. That is evidence of *availability*, and nothing more — it is not a terms check, and the two are recorded separately on purpose.

| # | Source | Lang | Feed URL | Reachable 2026-08-13 | robots.txt | Terms status |
|---|---|---|---|---|---|---|
| S-01 | UN News | `en` | `https://news.un.org/feed/subscribe/en/news/all/rss.xml` | 200 `application/rss+xml` | No directives returned for the host | **Read.** UN permits reuse of news material with credit given and the UN advised; general site terms grant personal, non-commercial use without redistribution |
| S-02 | UN News | `ar` | `https://news.un.org/feed/subscribe/ar/news/all/rss.xml` | 200 `application/rss+xml` | as S-01 | as S-01 |
| S-03 | UN News | `fr` | `https://news.un.org/feed/subscribe/fr/news/all/rss.xml` | 200 `application/rss+xml` | as S-01 | as S-01 |
| S-04 | France 24 | `en` | `https://www.france24.com/en/rss` | 200 `application/rss+xml` | **Read.** `User-agent: *` → `Disallow:` (nothing disallowed). Named AI-training crawlers are blocked individually | **[TBD-21]** — ToS not read |
| S-05 | France 24 | `fr` | `https://www.france24.com/fr/rss` | 200 `application/rss+xml` | as S-04 | **[TBD-21]** |
| S-06 | France 24 | `ar` | `https://www.france24.com/ar/rss` | 200 `application/rss+xml` | as S-04 | **[TBD-21]** |
| S-07 | BBC Arabic | `ar` | `https://feeds.bbci.co.uk/arabic/rss.xml` | 200 `text/xml` | **Read.** Disallow list does not cover the feed path | **[TBD-21]** — ToS not read |
| S-08 | ReliefWeb (OCHA) | `en` | `https://reliefweb.int/updates/rss.xml` | 200 `application/rss+xml` | **Read.** No rule blocking the feed path | **Partially read.** The public API is free but requires a pre-approved `appname` since 1 Nov 2025 (1,000 calls/day). **POLIS uses the RSS feed, not the API**, so the appname requirement does not currently apply — if that changes, registration is mandatory before the switch |

Balance: Arabic ×3, English ×3, French ×2. No single publisher exceeds three feeds, so one outlet's editorial line cannot dominate a language.

### 2.0 What is collected, and why that bounds the licence question

**Only what the feed itself syndicates** — title, summary/description, publish time, link. POLIS does **not** follow the link and scrape the full article body for these sources.

This is a governance decision, not a technical shortcut. An RSS summary is content the publisher deliberately syndicated for machine consumption; a scraped article body is not. Restricting collection to the feed payload keeps POLIS inside the narrow, defensible use every one of these publishers already invites, and removes the "no systematic reproduction" clause that a full-text scrape would run straight into.

Retention stays 180 days for raw content (PRIV-4). Nothing collected is republished — the UI is private to project members and evaluators, and the corpus is never committed to the public repository.

### 2.0.1 France 24 and the AI-crawler question

France 24's `robots.txt` permits `User-agent: *` but individually blocks a long list of named AI-training crawlers (`AI2Bot`, `AlibabaBot`, and others). POLIS's User-Agent is not on that list, and the generic rule permits access.

The signal is still worth reading honestly: that publisher does not want its content used to train models. **POLIS does not train on it.** Training data is the Cardiff NLP corpus (DOC-007 §5); France 24 content is inference input and is never written into a training set. The distinction is real, and it is recorded here rather than left to be assumed.

If that ever stops being true — if any ingested content is used for training — these sources must be re-evaluated first.

### 2.1 What Is Deliberately Absent From This Table

| Excluded category | Reason |
|---|---|
| Private Telegram groups | PRIV-1 — public-source-only collection is architectural, not a filter applied after the fact |
| Authenticated/paywalled news sites | PRIV-1; also outside the ₹0 budget (PRD C-1) |
| Direct/private messages of any kind | PRIV-3 — no individual surveillance capability exists |
| X/Twitter | **[FUTURE]** per PRD FR-1.8 — no free, terms-compliant, technically stable access path was confirmed at design time; the MVP does not depend on it (PRD TBD-5) |
| Any source requiring login | PRIV-1 |

---

## 3. Governance

### 3.1 Collection Principles ⟵ PRD PRIV-1…PRIV-13

| Principle | How it is enforced, not just stated |
|---|---|
| Public-only collection | Source `source_type` is restricted by schema CHECK to `rss`, `telegram`, `reddit`, `html_page` — no adapter for an authenticated source type exists in the codebase to misuse |
| No private groups | Telegram adapter is scoped to public-channel read access only; there is no code path for joining or reading a private group |
| No authenticated/private communications | Architectural — POLIS has no credential-based access to any individual's account or inbox |
| No individual surveillance | No feature builds a per-person profile, links identities across platforms, or scores an individual (PRD PRIV-3); entity extraction is for topical aggregation only |
| Data minimisation | Only text, language, source, timestamps, URL, and derived NLP outputs are stored; author handles only where intrinsic to a public post (DB §5.3) |
| Retention | 180 days raw/processed content, 365 days derived results and audit, alerts/reviews retained for project duration — a documented project decision (PRD PRIV-4), not a legal claim |
| Source attribution | Every content item retains its `source_id` and original `url` permanently — POLIS never presents collected text without its provenance |
| Takedown/deletion handling | **[TBD]** — no formal takedown process has been needed or designed yet, since POLIS collects only content its sources already publish openly; if a source requests removal of their content from POLIS's demonstration corpus, the response is manual deletion via the retention purge mechanism (DB §12), owned by Team A/C. This is flagged as an open item, not assumed unnecessary. |
| Dataset licensing | Tracked per-dataset in §2 above; unresolved `[TBD]` licence checks are release-blocking for that dataset's use in training (POLIS-DOC-007 §5) |
| Model licensing | `xlm-roberta-base` (MIT) and translation model licence (per §2) tracked the same way |
| Acceptable use | POLIS's own use of collected data is scoped to the FYP demonstration; no data collected is resold, redistributed, or used outside the academic project |

### 3.2 Robots.txt and Rate-Limit Policy

Every HTTP-fetched source (RSS and HTML page types) is subject to: (1) a `robots.txt` check before the first fetch and periodically thereafter, (2) a descriptive `User-Agent` identifying POLIS as an academic project with a contact reference, (3) per-domain rate limiting, (4) a maximum response size (2 MB) and timeout (10s) ⟵ TRD §5.2, FR-1.4. This is implemented once, centrally, in `ingestion/http_client.py` — no adapter can bypass it, because no adapter fetches directly.

---

## 4. Political / Ethical Safeguards

These are restated here, verbatim in spirit, from PRD §10.6 and §13 — not weakened or reinterpreted for this document. This register is where a source's *availability* is governed; the safeguards below govern what POLIS is permitted to *claim* about the data it collects, and they apply regardless of source.

| Safeguard | Statement |
|---|---|
| No predictive framing | POLIS never states or implies that any indicator predicts a future political event ⟵ PRD §10.6, FR-4.9 |
| Human-in-the-loop | No output from any source, however collected, triggers an automated action ⟵ PRIV-5 |
| No autonomous action | The pipeline terminates at "visible to a human analyst" — architecturally, not by policy alone ⟵ FR-5.10 |
| No claim of truth determination | A disinformation-signal label describes statistical features of the text, never a determination that a claim is true or false ⟵ FR-3.3, §10.6 |
| No claim of intent or coordination | Narrative Amplification (IND-03) measures text-similarity and timing, and explicitly states in its own alert text that this is common for legitimate wire-service syndication — it never asserts coordination or bad intent ⟵ PRD §10.4 IND-03 |
| Uncertainty stays visible | Every classification carries its confidence; every indicator carries its measurement confidence; nothing is displayed as a bare fact ⟵ NFR-6.2 |
| Source reliability is qualitative | Sources are shown in three qualitative bands (Established / Mixed / Limited history) with the reasoning visible on request — never a numeric "trust score" that could be mistaken for a precise, defensible measurement ⟵ PRIV-10 |

Any new source category proposed after this document's baseline must be checked against every row in this table before being added to §2 — a source that cannot satisfy "public," "no individual surveillance," and "attributable" is out of scope regardless of how useful its content would be.

---

## 5. Open Items

| ID | Item | Status / Resolution | Owner + due |
|---|---|---|---|
| ~~GOV-1~~ | Verify LIAR licence | **CLOSED — descoped, not verified.** The disinfo head is cut in DOC-016 §3.2, so the dataset is unused and no licence check is owed. Recorded as descoped rather than passed, because "verified" would be a false claim | 2026-08-13 |
| ~~GOV-2~~ | Verify FakeNewsNet re-scrape terms | **CLOSED — descoped, not verified.** Same reason | 2026-08-13 |
| ~~GOV-3~~ | Select and verify a Kaggle fake-news corpus | **CLOSED — descoped, not verified.** Same reason | 2026-08-13 |
| ~~GOV-4~~ | Verify NLLB-200 vs opus-mt licence | **CLOSED — descoped.** The translation layer is cut in DOC-016 §3.2; language is detected, never translated | 2026-08-13 |
| GOV-5 | Confirm `robots.txt` before first fetch | **PARTIAL.** Read and recorded for france24.com, feeds.bbci.co.uk, reliefweb.int. news.un.org returned no directives — re-check whether the file is absent or the request was refused | You, Week 3 |
| ~~GOV-6~~ | Confirm Telegram channels genuinely public | **CLOSED — descoped.** No Telegram adapter in the solo scope | 2026-08-13 |
| GOV-7 | Design a takedown-request handling procedure | **OPEN.** Cheaper now than under pressure. A source asking for removal must have a documented path even though none has asked | You, Week 5 |
| ~~GOV-8~~ | Populate §2 with ≥ 8 real sources | **CLOSED.** Eight named feeds in §2, each probed and recorded | 2026-08-13 |
| **GOV-9** | Read the France 24 and BBC terms of service ⟵ **TBD-21** | **OPEN.** `robots.txt` is a crawling rule, not a licence, and treating one as the other is the error GOV exists to catch | You, **before first ingest — Week 3** |
| **GOV-10** | Re-verify all eight feeds before the demo | **OPEN.** A feed URL that worked in Week 2 is not evidence it works in Week 15 | You, Week 15 |

This tracker feeds the consolidated open-items list in `DOCUMENT-CONSISTENCY-REPORT.md` — items are not duplicated with different wording in both places; this table is authoritative for governance-specific items.

---

*End of Document 14. Update §2 with real source rows — not category placeholders — as each is actually configured in Implementation Plan Phase 2.*
