# Intelligent Academic Timetable Management & Optimization System

Phase 2 delivers an integrated web application and independently validated scheduling backend for the SGSITS-style department demonstration. It schedules EE Semesters III, V, and VII together while treating faculty, rooms, laboratories, student groups, electives, and imported first-year commitments as shared resources.

## What works now

- FastAPI backend with OpenAPI documentation
- Normalized SQLAlchemy schema and Alembic migration
- SQLite zero-setup development mode and PostgreSQL production configuration
- Actual Google OR-Tools CP-SAT model (not random allocation)
- Candidate elimination before Boolean variable creation
- Simultaneous multi-semester generation
- Faculty, room, lab, and student-group collision constraints
- Configurable periods and blocked lunch
- Consecutive two-period laboratories with equipment and capacity checks
- Fixed resource reservations and fixed external lectures
- Hard home rooms for ordinary theory sessions
- Parallel electives with enrollment-sized rooms
- Faculty availability and hard daily/weekly workload checks
- Weighted preference, late-period, and same-subject/day penalties
- Feasibility-preserving direct-move Simulated Annealing refinement
- Independent schedule validator and quality metrics
- Persisted generation runs, schedules, diagnostics, and validation reports
- Realistic fictional 15-faculty seed master data
- Automated solver and API-service workflow tests
- React 19 and TypeScript responsive administration interface
- Secure role-based admin, faculty, and student workspaces
- Guided 12-step timetable preparation experience
- Browser-based master data forms for faculty, rooms, labs, and reservations
- Generation controls, hybrid result metrics, weekly timetable filtering, analytics, and CSV download

## Architecture

```text
FastAPI routes
    -> generation service -> persisted run / timetable / report
                           -> scheduling domain model
                              -> preprocessing + actionable checks
                              -> CP-SAT candidate assignment model
                              -> optional feasible annealing refinement
                              -> independent validator + metrics

SQLAlchemy models -> SQLite (local) / PostgreSQL (deployment)
                 -> Alembic migrations
```

The optimization package does not import FastAPI or SQLAlchemy. This keeps the mathematical engine testable and allows later workers or CLI tools to call it directly.

## Quick start

Requires Python 3.11+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
Copy-Item .env.example .env
python -m alembic upgrade head
$env:PYTHONPATH = "backend"
python scripts/seed.py
uvicorn app.main:app --reload
```

Start the frontend in another PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. API documentation remains at `http://localhost:8000/docs`.

Demo accounts all use password `Demo@123`:

- `admin@example.edu`
- `faculty@example.edu`
- `student@example.edu`

Run verification:

```powershell
python -m pytest
```

PostgreSQL-backed startup is available through:

```powershell
docker compose up --build
```

## Demonstration data

The solver demonstration contains:

- three EE semesters with separate hard home rooms;
- 15 global faculty identities, including an externally taught fixed ECE lecture;
- four 15-student Semester V lab batches;
- 20- and 40-student parallel Semester VII electives;
- a shared Power Electronics laboratory reserved by first year on Monday 10:00–12:00;
- configurable Monday–Friday periods with 1:00–2:00 blocked for lunch.

The seed command writes permanent master data. The `/generation/demo` endpoint currently maps the equivalent deterministic demonstration dataset into the standalone scheduling model. Database-to-domain configuration CRUD and wizard support belong to Phase 2.

## Solver status semantics

- `optimal`: CP-SAT proved optimality for the configured objective.
- `feasible`: a valid solution was found, but optimality was not proven.
- `infeasible`: CP-SAT proved no hard-constraint solution exists.
- `unknown`: the time limit ended without a solution or proof of infeasibility.
- `invalid_input`: sound preprocessing found missing or contradictory inputs.
- `model_invalid`: OR-Tools rejected the mathematical model.

The API never labels `unknown` as infeasible. A timetable is persisted only after the independent validator confirms every implemented hard constraint.

## Phase 2 checkpoint

Implemented: the Phase 1 optimization foundation plus signed authentication, password hashing, backend role enforcement, master-data APIs and browser forms, a guided preparation flow, real generation integration, timetable filtering by role/group, analytics, responsive dashboards, and CSV export.

Known limitations for the next phases:

- Generation can use selected database-backed semester configurations. The demo fallback remains available only when no semester IDs are supplied.
- Direct-move annealing is implemented; CP-SAT neighborhood repair is not yet implemented.
- Student/faculty gap metrics are measured after solving, but full gap linearization in the CP-SAT objective is deferred to Phase 2.
- Dynamic rescheduling, immutable publication versions, exports, and change requests are Phase 3.
- The data model is the Phase 1 operational subset, rather than every final entity listed in the master specification.

See [algorithm documentation](docs/ALGORITHM.md), [Phase 1 report](docs/PHASE_1.md), [Phase 2 report](docs/PHASE_2.md), and [API notes](docs/API.md).

