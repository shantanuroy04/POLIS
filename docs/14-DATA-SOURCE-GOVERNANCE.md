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

**Demo languages: Arabic, English, French** ⟵ TBD-1, DOC-007 §4.1. Balance across the register: English ×2, Arabic ×1, French ×1.

Every feed below was probed on **2026-08-13** with POLIS's own User-Agent. All eight returned **HTTP 200** with an RSS content type. That is evidence of *availability*, and nothing more — it is not a terms check, and the two are recorded separately on purpose.

| # | Source | Lang | Feed URL | Verified 2026-08-18 | Terms |
|---|---|---|---|---|---|
| S-01 | UN News — all news | `en` | `https://news.un.org/feed/subscribe/en/news/all/rss.xml` | **30 items parsed** | **Read.** Reuse of news material permitted with credit given and the UN advised |
| S-02 | UN News — all news | `ar` | `https://news.un.org/feed/subscribe/ar/news/all/rss.xml` | **30 items parsed** | as S-01 |
| S-03 | UN News — all news | `fr` | `https://news.un.org/feed/subscribe/fr/news/all/rss.xml` | **30 items parsed** | as S-01 |
| S-04 | ReliefWeb (OCHA) — updates | `en` | `https://reliefweb.int/updates/rss.xml` | **20 items parsed** | **Partially read.** The API needs a pre-approved `appname` since 1 Nov 2025; **POLIS uses the RSS feed, not the API**, so it does not apply. Registration is mandatory before any switch |

**110 items per poll across 3 languages.** Verified by an actual parse, not a status code — `python -m ingestion.check_sources`.

### 2.0.4 Four feeds were removed because HTTP 200 is not evidence of content

The register briefly held eight feeds. Four were UN News topic and region feeds — peace-and-security in English and Arabic, Afrique in French, Middle East in English — added after a probe showed each returning **200 with an `application/rss+xml` content type**.

The first live run through the adapter showed all four return **an empty body**. Every alternate URL pattern tried returns the same. UN News appears to publish only its `.../news/all/...` feeds with content.

This is the same mistake as trusting `robots.txt` for a licence, one layer down: **a status code is evidence that a server answered, not that it answered with anything.** The probe checked the cheap thing and the register recorded it as if it were the expensive thing.

`ingestion/check_sources.py` exists so this cannot recur silently. It fetches every registered source through the real adapter and reports item counts. It is deliberately **not** a CI test — it needs the network, and a security-and-governance check that fails on a flaky connection is a check that gets muted. Run it when adding a source, and before the demo ⟵ GOV-10.

### 2.0.5 Consequence: item volume is now a live risk

Four sources instead of eight, and UN News publishes roughly 30 items per feed per poll with substantial overlap between polls. Realistic yield is on the order of **50–100 genuinely new items per day across all three languages.**

The indicators divide that further — by language, by region, by 24-hour window — before comparing against a 14-day baseline. **The `n_min` gates in PRD §10 were sized for a corpus with eight sources.** They may now suppress every indicator, which would be a correct refusal by the system and a useless demo.

This is recorded now rather than discovered in Week 17:

- Measure real daily volume per language and per region during Weeks 5–8, when the pipeline is running unattended ⟵ **TBD-11** already owns the `n_min` values
- If volume is too thin, the honest responses are to widen the window from 24 h to 72 h, or to compute at macro-region rather than subregion granularity — **not** to lower `n_min` until something fires
- GOV-11 (a non-UN publisher) is now a volume issue as well as a bias issue

### 2.0.0 France 24 was removed after its terms were read

France 24's three feeds (all three languages) were listed in the first draft of this register on the strength of a `robots.txt` that permits `User-agent: *`. **Reading the actual terms reversed that decision.** France Médias Monde's legal notice states:

> "It is also strictly forbidden to collect, store, use, extract, reproduce, directly or indirectly, permanently or temporarily, all or part of the content without authorization, by any means and for any purpose, automatically or manually, particularly for training, development, and operation of any software, system, and artificial intelligence device."

It further asserts the Text and Data Mining opt-out under Article L122-5-3 of the French Intellectual Property Code, and grants **no exception for research, academic or private use**.

POLIS collects, stores for 180 days, and operates a software system over that content. Every verb in that sentence describes POLIS. There is no reading under which this is permitted, and "it is only an FYP" is not one.

**This is exactly why GOV-9 existed.** `robots.txt` said yes; the licence said no. A crawling rule is not a licence, and a register that had trusted the first would have shipped a violation into a public repository.

### 2.0.2 Known limitation: publisher concentration

Three of the four feeds are UN News. That is a **real weakness in the corpus and it is declared, not hidden**: an early-warning system reading mainly the UN's own reporting inherits the UN's framing, its story selection, and its silences. Sentiment measured across those feeds says something narrower than "sentiment in the region".

It is the honest consequence of the constraint, and the constraint is itself a finding worth reporting: **most commercial news publishers explicitly prohibit the automated collection and storage that any monitoring system requires.** That is why real systems in this space license content or use aggregators such as GDELT rather than reading feeds directly. A ₹0 budget removes both options.

Mitigations actually applied:

- ReliefWeb brings a second organisation, and an operational rather than editorial voice
- DOC-008 and the FYP report must state this limitation next to any per-region or per-language finding
- **GOV-11** tracks finding at least one non-UN publisher with compatible terms

### 2.0.3 BBC Arabic is not ingested, because its terms could not be read

`bbc.co.uk` refuses automated fetches, so the BBC terms of use were **not** read. Secondhand summaries exist and were deliberately not relied on — a 2007 news article about BBC licensing policy is not evidence of what the terms say in 2026.

Under the DOC-016 §6.2 slip rule, a source whose terms have not been read is not fetched. BBC Arabic therefore stays out of the register until someone opens the page in a browser and records what it says. **TBD-21 remains open for BBC only; the France 24 half is closed by removal.**


### 2.0 What is collected, and why that bounds the licence question

**Only what the feed itself syndicates** — title, summary/description, publish time, link. POLIS does **not** follow the link and scrape the full article body for these sources.

This is a governance decision, not a technical shortcut. An RSS summary is content the publisher deliberately syndicated for machine consumption; a scraped article body is not. Restricting collection to the feed payload keeps POLIS inside the narrow, defensible use every one of these publishers already invites, and removes the "no systematic reproduction" clause that a full-text scrape would run straight into.

Retention stays 180 days for raw content (PRIV-4). Nothing collected is republished — the UI is private to project members and evaluators, and the corpus is never committed to the public repository.

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
| GOV-8 | Populate §2 with ≥ 8 real sources | **REOPENED 2026-08-18.** Eight were listed; four proved empty (§2.0.4) and three more were removed on terms (§2.0.0). **Four sources are live.** PRD's ≥ 8 target is not met and will not be met from UN-family sources alone | You, with GOV-11 |
| GOV-9 | Read the France 24 and BBC terms of service ⟵ TBD-21 | **HALF CLOSED 2026-08-13. France 24: read, and it forbids exactly what POLIS does — all three feeds removed (§2.0.0). BBC: `bbc.co.uk` refuses automated fetch, terms unread, so BBC Arabic is not ingested (§2.0.3).** `robots.txt` said yes and the licence said no, which is the whole reason this item existed | BBC half open — You, before adding it |
| **GOV-11** | Find at least one non-UN publisher with terms compatible with automated collection and 180-day storage | **OPEN.** Seven of eight feeds are UN News (§2.0.2). Candidates worth checking: VOA (US federal material is public domain, but AFP/AP/Reuters content is mixed in and is not), other UN-family agencies, and openly licensed outlets. Do not add any of them on the strength of `robots.txt` | You, **before Week 20** |
| **GOV-10** | Re-verify all eight feeds before the demo | **OPEN.** A feed URL that worked in Week 2 is not evidence it works in Week 15 | You, Week 15 |

This tracker feeds the consolidated open-items list in `DOCUMENT-CONSISTENCY-REPORT.md` — items are not duplicated with different wording in both places; this table is authoritative for governance-specific items.

---

*End of Document 14. Update §2 with real source rows — not category placeholders — as each is actually configured in Implementation Plan Phase 2.*
