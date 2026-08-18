# POLIS

**Political Open Source Language Intelligence System**

An AI-assisted, multilingual political monitoring and early-warning **support** system. It reads publicly available text on a fixed schedule, classifies it with a multilingual model, aggregates the results into explicitly defined early-warning indicators, and raises tiered alerts for **a human analyst to assess**.

> **Working on this? Open [`STATUS.md`](STATUS.md).** It is the only file kept current — where the project is, what to do next, what is still undecided. Everything in `docs/` is frozen design reference.

> POLIS is a university Final Year Project prototype. It is **not** affiliated with, endorsed by, or connected to the United Nations or any mission. All data is public.

---

## What POLIS is not

Not boilerplate — an architectural constraint, enforced in code and tests:

- It does **not** predict political events, violence, or crises.
- It does **not** determine whether any claim is true or any source untrustworthy.
- It does **not** establish coordination or intent behind a posting pattern.
- It does **not** take, recommend, or trigger any action. The pipeline terminates at "visible to a human."
- It does **not** monitor individuals, private communications, or closed groups.

⟵ [PRD §10.6](docs/01-PRD.md), [ADR-012/ADR-015](docs/15-ARCHITECTURE-DECISIONS.md)

---

## Setup

```bash
python -m venv venv
venv\Scripts\activate                 # Windows;  source venv/bin/activate elsewhere
pip install -r requirements-dev.txt
cp .env.example .env

pytest                                # 86 tests
python -m ingestion.check_sources     # are the 4 feeds still alive?
uvicorn backend.main:app --reload     # http://localhost:8000/api/v1/health
```

Postgres arrives in Week 5 and is not needed before then.

---

## The one interface that matters

```python
from ml.predict import score_text
result = score_text("some cleaned text", lang="ar")   # -> dict, PRD §9.1 schema
```

The **only** symbol the backend imports from `ml`. Currently a **stub** returning deterministic pseudo-scores, so the backend and frontend can be built during the weeks before a real model exists.

Its schema is **frozen**. `tests/ml/test_score_text_contract.py` must pass unchanged when the real model lands ⟵ [ADR-008](docs/15-ARCHITECTURE-DECISIONS.md).

---

## Layout

```
ingestion/   source adapters, guarded fetch, cleaning, dedup
ml/          inference.  Backend imports ONLY predict.score_text
alerts/      indicators, severity, alert rules
backend/     FastAPI, DB, auth, audit
frontend/    React + Vite + Tailwind
docs/        frozen design reference — see docs/README.md
```

---

## Latency budget

Scheduled-batch, near-real-time — **not** event-streaming. Four stages chained inside one 10-minute tick:

```
poll 10.0 + ingest 2.0 + score 2.5 + indicators 1.0 + alerts 0.5 = 16.0 min  ≤ 20 required
```

The poll interval is *derived*, not a free knob — `backend/config.py` rejects anything above 10 minutes at startup ⟵ [PRD §11.1](docs/01-PRD.md).

---

## Working rules

`main` and `develop` are protected: no direct pushes, no force pushes, linear history, and three CI gates green (secret scan, Python lint/test/audit, frontend lint/test/audit). Solo, so PRs are self-merged — **CI is the reviewer**.

**Never commit:** `.env`, model weights, datasets, database dumps, `node_modules/`.

Current state, open questions, and the schedule all live in [`STATUS.md`](STATUS.md).
