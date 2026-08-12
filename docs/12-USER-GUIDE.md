# POLIS — User Guide

**Political Open Source Language Intelligence System**

---

## 1. Document Control

| Field | Value |
|---|---|
| Document ID | POLIS-DOC-012 |
| Version | 1.0 |
| Date | 11 August 2026 |
| Status | Draft — **written against the specified UI (POLIS-UX-004, POLIS-FLOW-003); no running application exists yet to screenshot or verify against** |
| Owner | D1 (Frontend) |
| Derives from | POLIS-FLOW-003 (pages, flows), POLIS-UX-004 (terminology, copy, wireframes), POLIS-PRD-001 §6 (roles), §10.6 (prohibited interpretations) |

This guide uses the exact terminology already established in the PRD and UX spec — it does not introduce new names for anything. Where a term appears here (e.g. "measurement confidence," "evidence," "coverage tone"), it is the same term the interface itself uses.

---

## 2. Before You Start — What POLIS Is and Is Not

> POLIS is a university Final Year Project prototype. It is not affiliated with, endorsed by, or connected to the United Nations. This statement appears in the footer of every page.

Read this section before the role-specific sections below. It applies to every role.

| POLIS **does** | POLIS **does not** |
|---|---|
| Read public sources on a repeating schedule (roughly every 10 minutes) and flag statistical signals against a subject's own historical baseline | Predict political events, violence, protest, or crises |
| Surface a newly published item within about 20 minutes of it appearing | Deliver anything instantly — POLIS is near-real-time, not live streaming |
| Show you the evidence behind every flag | Determine that any claim is true or false |
| Report a confidence value for every model output | Present confidence as certainty |
| Translate non-English text for your convenience | Guarantee translation accuracy — every translation is machine-generated and unverified |
| Measure text-similarity and timing patterns across sources | Establish coordination or intent behind a posting pattern |
| Record your decision permanently | Make the decision for you, or act on your behalf |

**Model output is not ground truth.** A sentiment, hostility, or disinformation label is the model's classification, shown with its confidence and its model version, always traceable to the original text. **Disinformation output is probabilistic** — the label means "this text has statistical features associated with unreliable content in the training data," not "this claim is false." **Alerts are monitoring prompts, not conclusions** — every alert requires your assessment before it means anything. **You, the human analyst, retain decision authority** at every step; POLIS's role ends at showing you a signal and its evidence.

---

## 3. Analyst Guide

### 3.1 Logging In

Go to the POLIS login page, enter your email and password. If your credentials are wrong, POLIS shows the same generic message whether the account exists or not — this is a deliberate security measure, not a bug. If you're locked out after repeated attempts, wait for the stated cooldown; contact an Administrator if you believe this is an error, not a real lockout.

### 3.2 The Dashboard

Your entry point after login. Six regions, each independently loaded:

1. **Active alerts by severity** — click any severity count to jump to the filtered Alert Center.
2. **Indicator activity** — six small charts, one per indicator, showing the last 14 days against a threshold line.
3. **Coverage tone** — how the tone of reporting about tracked subjects has shifted, not public opinion.
4. **Top topics** — what's being covered most in the last 24 hours.
5. **Recent flagged content** — the newest items that triggered something.
6. **System** — source health, pending analysis backlog, review backlog, and alert precision.

Every number on the dashboard is clickable and leads to the data behind it. If a number can't be drilled into, that's a defect — report it.

### 3.3 Live Monitoring

The rolling feed of ingested and classified content, refreshed each time the scheduled pipeline runs (about every 10 minutes) — not a live stream. Use the filter row (date, language, source, topic, entity, classification labels, review status) to narrow it. By default you see **canonical items only** — near-duplicate wire copy is folded under a "+N similar" badge on the original rather than flooding the feed.

An item still awaiting classification shows an "analysis pending" badge rather than being hidden — POLIS never pretends ingestion is instantaneous.

### 3.4 Opening a Content Item

Every content item you open (from Monitoring, Search, or an alert's evidence list) shows, in one view:

- **Original text** — exactly as collected, in its original language.
- **Machine translation** — permanently labelled *"Machine translation, unverified. Analysis was performed on the original text."* This label is not dismissible, because the underlying uncertainty doesn't go away because you closed a banner.
- **Classifications** — sentiment, hostility, disinformation signal (and stance, where applicable), each with a **confidence meter**.
- **Entities and topics** — click any entity or topic to jump to a filtered view of related content.
- **Contributing indicators** — if this item fed an alert, it's linked here.
- **Related content** — the near-duplicate cluster this item belongs to, if any.

### 3.5 Understanding Confidence

Every classification shows a confidence meter and a number, e.g. `▮▮▮▯ 0.74`. Hover it for the exact meaning: **"Confidence that the model assigned this label. It is not a probability that the underlying claim is true, and not a prediction about future events."** Below 0.55, POLIS shows the label de-emphasised and marks it "low confidence" — read that as "the model is not sure," not as a weaker version of the same fact.

### 3.6 Understanding the Model Version

Every classification is stamped with the exact model version that produced it (e.g. `polis-xlmr-v0.3.1`), shown as a clickable link. Following it takes you to that model's evaluation metrics — including its per-language performance, which is reported separately, not hidden behind a single averaged number. Two items scored by different model versions may legitimately disagree; the version tag is how you'd notice that.

### 3.7 Alert Review

This is the core of your work. From the Alert Center or your Review Queue:

1. **Claim** the alert (or it's already assigned to you).
2. **Read "Why this was flagged"** — a plain-language sentence naming the indicator, the observed value, the 14-day baseline, the threshold that was crossed, the sample size, and the measurement confidence. It always ends with: *"This is a monitoring signal requiring analyst assessment; it is not a prediction of any future event."*
3. **Expand the formula** if you want the literal computation, not just the summary.
4. **Open the evidence** — every content item that contributed. You are expected to actually read the original text, not just the aggregate number.
5. **Record your decision:**
   - **Confirmed** — the signal reflects something meaningful.
   - **Rejected** — false positive; the measurement doesn't reflect anything meaningful.
   - **Inconclusive** — you can't assess it from the available evidence.
6. **Add notes.** Optional in general, but **required** for a `confirmed` decision on a Hostile Rhetoric Surge / Narrative Amplification alert (IND-01/IND-03) where the wire-copy-syndication risk is highest — the Save button stays disabled with the reason shown until you write something.
7. **Save.** Your decision is permanent. If you need to change your mind later, you record a new decision that supersedes the old one — both remain visible in the history, nobody's earlier judgment silently disappears.

**No option is pre-selected.** POLIS does not nudge you toward a judgment.

### 3.8 Evidence

Every alert links to the specific content items behind it — never fewer than one. If you ever open an alert with no evidence, that's a system defect, not something for you to work around; report it. Evidence items are paginated if there are many; you're not required to read all of them, but you are expected to read enough to justify your decision, especially on `confirmed`.

### 3.9 Search

Full-text search across original and translated text. Minimum 2 characters, and it's rate-limited (20/min) so if you're search-heavy in a short burst, expect an occasional "try again in a few seconds." All your filters and the query itself live in the page URL, so you can bookmark or share a search.

### 3.10 Your Review Queue

Two panes: **My queue** (alerts you've claimed) and **Unclaimed** (sorted by severity, oldest first within a severity tier). Claim the highest-severity item you can act on next. If you claim something and then need to step away, **release** it rather than leaving it — an abandoned claim auto-releases after a few hours anyway, but releasing explicitly is faster for your team.

---

## 4. Supervisor Guide

Everything in §3 applies to you as well — you have every Analyst capability, plus the following.

### 4.1 Team Review Statistics

The Review Queue's third pane, visible only to you, shows every analyst's review counts and their individual precision. **Precision** = confirmed ÷ (confirmed + rejected) for that analyst or that indicator — `inconclusive` decisions are deliberately excluded from the calculation, so an analyst can't inflate their apparent precision by declining to judge.

### 4.2 Precision by Indicator

Shown as a horizontal bar chart with a reference line at the informal target (0.60). **A weak indicator is shown at its real value, not hidden** — if IND-03 (Narrative Amplification) is sitting at 0.38, you'll see 0.38, because a system that conceals its own error rate can't be calibrated by anyone, including you.

### 4.3 Review Backlog

How many alerts are unclaimed, and how long the oldest one has been waiting. This is your signal for whether your team is keeping pace.

### 4.4 Indicator Thresholds

On the Indicator Settings page, you can adjust an indicator's **threshold**, **minimum sample size (n_min)**, or **enabled** state. Each indicator card shows its plain-language definition, its literal formula, and its documented **false-positive risk** — read that before changing anything. Saving a threshold change shows you a projection ("this would have produced approximately N more/fewer alerts over the last 30 days," computed from real historical scores) before you confirm. The change takes effect from the **next** scheduled computation — it never rewrites the justification behind an alert that already fired and that an analyst already acted on.

### 4.5 Audit Scope

You can read audit records scoped to alerts and reviews — not the full system audit log (that's Administrator-only). This lets you see, for instance, every threshold change and who made it, without giving you visibility into user-management or source-configuration actions that aren't your concern.

### 4.6 Exports

You can export a set of reviewed decisions (filtered by date, decision, confidence) as a versioned dataset artefact — for instance, to hand to the ML team for evaluation purposes. The export dialog states plainly: *"This export may be used to build an evaluation dataset. It will not automatically retrain any model."* Exporting is an audited action.

### 4.7 What You Cannot Do

You cannot manage user accounts, create or disable sources, or activate a model version — those are Administrator actions. This separation is deliberate: the person who calibrates indicator thresholds and reviews analyst work is kept apart from the person who controls system configuration, so no single account holds both "sets the rules" and "judges the output" authority.

---

## 5. Administrator Guide

You have system-configuration authority. You **cannot** acknowledge, claim, or resolve alerts — if you try, POLIS tells you plainly that alert review is restricted to Analysts and Supervisors. This is not a bug to work around by asking someone to give you the Analyst role too; it's the intended separation of duties.

### 5.1 Users

Create accounts (name, email, role, initial password), change roles, and disable accounts. **Disabling requires typing the user's name to confirm** — this is a destructive-feeling action (it immediately ends their sessions), so POLIS makes you deliberate about it. Disabled users are never deleted; their past reviews and audit history remain intact, because that history belongs to the system's record, not to the account.

### 5.2 Sources

Add, edit, and disable ingestion sources (RSS feeds, public Telegram channels, public Reddit, government pages). When you enter a URL, POLIS checks it immediately against a private/internal-address blocklist — if you enter something that resolves to an internal address, you'll get a specific rejection message, not a generic error. Credentials for Telegram/Reddit are **never entered through this form** — they live in server-side environment configuration, and the form only shows you whether the required credential is set, never its value.

### 5.3 Source Health

Four states: **Healthy**, **Degraded** (1–2 consecutive failures), **Unhealthy** (3+), and **Config error** (something needs a human, not a retry — e.g. a blocked URL or bad credentials). A failing source explains itself inline; you shouldn't need to dig through logs to understand why a source is red.

### 5.4 Model Registry

View every trained model version with its full evaluation metrics, including per-language breakdowns. **Activating** a version makes it the one used for all new classifications going forward — existing results stay attributed to whichever version actually produced them, so activating a new model never rewrites history.

### 5.5 Audit Log

The complete record of privileged and decision-recording actions across the system: logins, permission denials, user/source/threshold/model changes, alert transitions, review decisions, exports. Filter by actor, action, resource, date, or result. This log is append-only at the database level — there is no edit or delete affordance anywhere in POLIS, because there is no such capability underneath it.

### 5.6 System Health

The same health information the uptime monitor sees, presented for you: database connectivity, active model version, scheduler status, per-source last-successful-fetch time, and the pending-analysis backlog depth.

---

## 6. Quick Reference — Terminology

| Term | Meaning |
|---|---|
| **Indicator** | A defined, computed measurement over a time window and a subject — never a prediction |
| **Subject** | The specific (region + topic) or (region + entity) scope an indicator is computed for |
| **Alert** | A persisted, reviewable record created when an indicator crosses its threshold |
| **Evidence** | The specific content items that produced an indicator's score |
| **Severity** | Normal / Informational / Low / Medium / High / Critical — always shown as icon + word + colour, never colour alone |
| **Confidence** | How sure the model is of its own label — not how likely the underlying claim is to be true |
| **Measurement confidence** | The indicator engine's confidence in its own computation (sample size, model confidence, source diversity) — a different number from a single item's classification confidence |
| **Cluster** | A group of near-duplicate items; the first-seen is canonical, the rest are linked, not deleted |
| **Model version** | The exact, immutable identifier of the trained model that produced a given result |
| **Reviewer decision** | Confirmed / Rejected / Inconclusive — your permanent, immutable judgment on an alert |

---

*End of Document 12. Screenshots and exact copy will be added once the frontend (Implementation Plan Phase 6) exists to capture them — this version documents behaviour, not pixels.*
