# POLIS

**Political Open Source Language Intelligence System**

An AI-assisted, multilingual political monitoring and early-warning **support** system. It reads publicly available text on a fixed schedule, classifies sentiment / hostility / probable disinformation with a multilingual model, aggregates those into six explicitly defined early-warning indicators, and raises tiered alerts for **human analysts to assess**.

> POLIS is a university Final Year Project prototype. It is **not** affiliated with, endorsed by, or connected to the United Nations or any mission. All data is public. All users are project team members or evaluators.

---

## What POLIS is not

This is not boilerplate — it is an architectural constraint, enforced in code and tests:

- It does **not** predict political events, violence, or crises.
- It does **not** determine whether any claim is true or any source is untrustworthy.
- It does **not** establish coordination or intent behind a posting pattern.
- It does **not** take, recommend, or trigger any action. The pipeline terminates at "visible to a human."
- It does **not** monitor individuals, private communications, or closed groups.

See [`docs/01-PRD.md` §10.6](docs/01-PRD.md) and [ADR-012/ADR-015](docs/15-ARCHITECTURE-DECISIONS.md).

---

## Setup

**Prerequisites:** Python 3.11+, Node 20+, Docker, Git.

```bash
# 1. Database
docker run -d --name polis-db -e POSTGRES_PASSWORD=devonly \
  -e POSTGRES_DB=polis -p 5432:5432 postgres:15

# 2. Backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                # fill in local values
uvicorn backend.main:app --reload --port 8000

# 3. Frontend (separate terminal)
cd frontend && npm install && npm run dev     # http://localhost:5173

# 4. Developer hooks (once)
pre-commit install
```

### Verify your setup (Implementation Plan task 1.14)

```bash
pytest                                        # all tests green
ruff check . && black --check .               # lint clean
curl http://localhost:8000/api/v1/health      # {"status":"ok"}
python -c "from ml.predict import score_text; print(score_text('test text'))"
```

The last command must return a schema-valid dict. If it does, the ML↔backend contract is working and you are unblocked.

---

## Repository layout

Directory ownership prevents merge conflicts. A PR touching another team's directory needs that team's review.

```
ingestion/   Team A — source adapters, cleaning, dedup, scheduling
ml/          Team B — datasets, training, inference.  Backend imports ONLY predict.score_text
alerts/      Team B + C — indicators, severity, alert rules
backend/     Team C — FastAPI, DB, auth, RBAC, audit
frontend/    Team D — React + Vite + Tailwind
tests/       everyone
docs/        16 documents — see docs/README.md
```

---

## The one interface that matters

```python
from ml.predict import score_text
result = score_text("some cleaned text", lang="ar")   # -> dict, PRD §9.1 schema
```

`ml/predict.py::score_text()` is the **only** symbol the backend imports from `ml`. It is currently a **stub** returning deterministic pseudo-scores, so backend and frontend can be built during the ~7 weeks before a real model exists.

Its schema is **frozen**. Changing it after Week 4 requires sign-off from the Team B and Team C leads plus matching updates to PRD §9.1, TRD §5.5, and DOC-007 §3.1 in the same PR. See [ADR-008](docs/15-ARCHITECTURE-DECISIONS.md).

`tests/ml/test_score_text_contract.py` must pass unchanged when the real model lands.

---

## Latency budget

POLIS is **scheduled-batch, near-real-time** — not event-streaming. The four pipeline stages run chained inside one 10-minute scheduler tick, giving a worst case of:

```
poll wait 10.0 + ingest 2.0 + score 2.5 + indicators 1.0 + alerts 0.5 = 16.0 min  ≤ 20 required
```

The poll interval is a *derived* value, not a free knob — `backend/config.py` rejects any value above 10 minutes at startup. Full derivation: [PRD §11.1](docs/01-PRD.md).

---

## Git workflow

```
Issue → feature branch → tests → PR → CI → review (≥1) → squash merge to develop
```

Branch naming: `ingest/rss-parser`, `ml/xlmr-baseline`, `be/alert-routes`, `fe/alert-detail`.

No direct pushes to `main` or `develop`. CI (lint, format, tests, `pip-audit`, `npm audit`, `gitleaks`) must pass before merge. Keep PRs under ~400 changed lines — a bigger one gets rubber-stamped, not reviewed.

**Never commit:** `.env`, model weights, datasets, database dumps, `node_modules/`.

---

## Documentation

16 documents in [`docs/`](docs/README.md). Start with the PRD; it is the product source of truth.

| | |
|---|---|
| [01 PRD](docs/01-PRD.md) | Requirements, the 6 indicators, latency budget, MVP scope |
| [02 TRD](docs/02-TRD.md) | Architecture, `score_text()` contract, API spec |
| [06 Implementation Plan](docs/06-IMPLEMENTATION-PLAN.md) | 16-week schedule, phases, risks |
| [15 ADRs](docs/15-ARCHITECTURE-DECISIONS.md) | Why the architecture is what it is |
| [Consistency report](docs/DOCUMENT-CONSISTENCY-REPORT.md) | Cross-document audit, open items |

---

## Known gaps (Week 1)

Honest status. Nothing here is hidden in a backlog.

| Gap | Impact | Owner / due |
|---|---|---|
| Local Python is **3.10**; TRD §4.2 specifies **3.11+** | Ruff/black target `py310`. CI runs 3.11. Resolve before Week 3: either install 3.11 team-wide, or amend TRD §4.2. | C1, Week 2 |
| No GitHub remote or branch protection yet | Task 1.1 is only half done — `git init` ran locally; the remote, protected `main`, and required-reviewer rule still need creating. | C1, Week 1 |
| `frontend/package-lock.json` absent | `npm ci` in CI will fail until someone runs `npm install` and commits the lockfile. | D1, Week 1 |
| Model is a stub | Every classification is deterministic pseudo-random. Not a model. Real one lands Week 8. | B1, Week 8 |
| No database schema yet | Alembic migrations 0001–0009 land Weeks 3–4 (Phase 5). | C1, Week 3 |
| 21 open `[TBD]` items | Tracked with owners and due weeks in the [consistency report §7](docs/DOCUMENT-CONSISTENCY-REPORT.md). | various |
