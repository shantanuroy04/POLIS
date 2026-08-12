# POLIS — Data Source & Governance Register

**Political Open Source Language Intelligence System**

---

## 1. Document Control

| Field | Value |
|---|---|
| Document ID | POLIS-DOC-014 |
| Version | 1.0 |
| Date | 11 August 2026 |
| Status | Draft — source **categories** and governance rules are confirmed; specific named source instances are `[TBD]`, owned by Team A per the Implementation Plan |
| Owner | Team A (Data/Ingestion) |
| Derives from | POLIS-PRD-001 §9 FR-1.x (ingestion), §13 (PRIV-1…PRIV-13); POLIS-TRD-002 §5.1–5.2 (source adapters, SSRF guard); POLIS-DB-005 §5.2 (`sources` table) |

This is a live register. As Team A configures real sources (Implementation Plan Phase 2, Weeks 2–5), each row moves from `[TBD]` (category defined, instance not yet chosen) to a concrete entry with a verified `robots.txt`/terms check. **No source is added to the live system before this table records it.**

---

## 2. Source Register

| Source | Type | Public? | Access method | Terms/Licence | robots.txt checked | Rate limit | Data collected | Retention | Risk | Owner |
|---|---|---|---|---|---|---|---|---|---|---|
| International wire service (e.g. Reuters World, AP) | RSS/Atom | Yes | `feedparser` polling | Publisher's public RSS terms — **[TBD]** verify no-scrape clause doesn't apply to RSS itself before adding | **[TBD]** — Team A, Week 2 | 10 min poll interval (config default, PRD FR-1.2) | Headline, body (where feed provides it), publish time, URL | 180 days (raw), per PRD PRIV-4 | Low — designed-for-syndication feed | Team A |
| Regional/language news outlet (e.g. Al Jazeera language editions) | RSS/Atom | Yes | `feedparser` polling | **[TBD]** per-outlet verification | **[TBD]** | 10 min | Same as above | 180 days | Low | Team A |
| Government/official statement page | HTML (no RSS) | Yes | `ingestion/sources/html_page.py`, guarded fetch | Public government communications — generally no restrictive ToS, but **[TBD]** verify per page | **[TBD]** | 15–60 min (slower-changing) | Statement text, publish time (if available), URL | 180 days | Low–Medium — page structure changes break the parser, not a legal risk | Team A |
| Public Telegram channel | Telegram (Telethon, public channel read) | Yes — **public channels only, never groups or private chats** | Telethon user-API, read-only | Telegram ToS — public channel content is intended for open distribution; **[TBD]** confirm the specific channels selected are genuinely public and not access-gated | N/A (not a web crawl) | Telethon's own API rate limits | Message text, author public handle (channel-post attribution only), timestamp | 180 days | Medium — channel could be deleted/go private after being added; content moderation varies by channel operator | Team A |
| Public subreddit | Reddit (PRAW) | Yes | Reddit's official free API via PRAW | Reddit API terms — free tier for research/personal, non-commercial academic use | N/A (official API) | PRAW-managed, Reddit's published limits | Post title/body, public username, timestamp, subreddit | 180 days | Low–Medium — public usernames are collected as they are intrinsic to the post; no cross-referencing performed ⟵ PRIV-2, PRIV-3 | Team A |
| LIAR dataset | Public research dataset | Yes | Direct download, archived locally | **[TBD]** — verify licence permits this specific academic use before training (POLIS-DOC-007 §5) | N/A | N/A (one-time download) | Pre-existing labelled text, not live-collected | Retained for project duration as training data | Low | Team B |
| FakeNewsNet | Public research dataset | Yes | Direct download / re-scrape of linked articles, archived locally | **[TBD]** — components may be link-only, subject-ToS applies to re-scraped articles | N/A | N/A | Pre-existing labelled text/links | Retained for project duration | Low–Medium (re-scraped components inherit the source site's terms) | Team B |
| Kaggle fake-news corpus | Public research dataset | Yes | Direct download | **[TBD]** — per-dataset Kaggle licence, not yet selected | N/A | N/A | Pre-existing labelled text | Retained for project duration | Low | Team B |
| `xlm-roberta-base` | Hugging Face Hub model | Yes | `transformers` library download | MIT | N/A | N/A | N/A — model weights, not data | Permanent (model artefact) | Low | Team B |
| `opus-mt` / NLLB-200-distilled | Hugging Face Hub model | Yes | `transformers` library download | CC-BY-4.0 (opus-mt) / **[TBD]** verify NLLB variant licence before selecting it over opus-mt | N/A | N/A | N/A | Permanent | Low, pending licence confirmation | Team A |

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

| ID | Item | Owner | Due |
|---|---|---|---|
| GOV-1 | Verify LIAR licence permits this academic use | B1 | Week 2 |
| GOV-2 | Verify FakeNewsNet re-scrape components' source-site terms | B1 | Week 2 |
| GOV-3 | Select and verify the specific Kaggle fake-news corpus and its licence | B1 | Week 2 |
| GOV-4 | Verify NLLB-200 licence vs opus-mt before selecting a translation model | A2 | Week 5 |
| GOV-5 | Confirm `robots.txt` status for every RSS/HTML source before first fetch | A1 | Week 2–3 (per source, ongoing) |
| GOV-6 | Confirm selected Telegram channels are genuinely public, not access-gated | A2 | Week 4 |
| GOV-7 | Design a concrete takedown-request handling procedure, even though none has been requested yet | A1 + C1 | Week 5 |
| GOV-8 | Populate §2 with the actual ≥ 8 sources once selected (currently category-level only) | A1 + A2 | Week 5 |

This tracker feeds the consolidated open-items list in `DOCUMENT-CONSISTENCY-REPORT.md` — items are not duplicated with different wording in both places; this table is authoritative for governance-specific items.

---

*End of Document 14. Update §2 with real source rows — not category placeholders — as each is actually configured in Implementation Plan Phase 2.*
