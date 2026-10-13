# Intelligent Academic Timetable Management & Optimization System

The application now uses an admin-first workflow. A fresh installation contains no institute, department, academic year, faculty, rooms, semester cohorts, subjects, reservations, or timetable. The first administrator creates an account and enters the institution's real records before generation is enabled.

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
- Written faculty and room availability constraints plus hard daily/weekly/consecutive workload checks
- Weighted preference, late-period, and same-subject/day penalties
- Feasibility-preserving direct-move Simulated Annealing refinement
- Independent schedule validator and quality metrics
- Immutable timetable versions, generation runs, diagnostics, validation reports, publication status, archives, and rescheduling history
- Empty production database with an optional, explicit development-only seed script
- Automated solver and API-service workflow tests
- React 19 and TypeScript responsive administration interface
- Secure role-based admin, faculty, and student workspaces
- SGSITS-domain role accounts, admin-only master-data CRUD, faculty self-availability, and read-only student/faculty directories
- Odd/Even term switching without deleting the other term or its timetable history
- Minimum-disruption faculty/room rescheduling with before/after approval
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

## Data durability and timetable backups

- Academic terms, master data, availability rules, generation runs, validation reports, and every timetable session are stored transactionally in the database.
- A generation or approved reschedule always creates a new immutable timetable version; it never edits an older version in place.
- Administrators can mark a version `draft`, `published`, or `archived`. A published version is the achieved timetable backup for that term, while all earlier versions remain available in history.
- Odd and Even terms use separate academic-term records and can be activated from the header without deleting either dataset.
- SQLite is suitable for the local demonstration. PostgreSQL is the intended multi-user departmental deployment database, with scheduled encrypted database backups handled by deployment infrastructure.

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
uvicorn app.main:app --reload
```

Start the frontend in another PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. On the first visit, create the first administrator account. Then follow **Start Setup** to add academic foundation data, faculty, rooms/labs, three semester cohorts, subjects, allocations, and reservations. API documentation remains at `http://localhost:8000/docs`.

Do not run the seed command for a real installation. Developers who deliberately want fictional demonstration data may run `python scripts/seed.py` against a disposable database.

Run verification:

```powershell
python -m pytest
```

PostgreSQL-backed startup is available through:

```powershell
docker compose up --build
```

## Admin-first data entry

Generation is locked until the administrator has entered:

- institute, department, active academic year, working days and periods;
- faculty workload records;
- theory rooms and laboratories with capacity/features;
- exactly three combined semester cohorts (no sections);
- every subject, weekly frequency, assigned faculty, eligible room/lab, batch, and elective group;
- any fixed room/resource reservations.

`POST /api/generation` requires selected database-backed semester IDs. There is no automatic demonstration fallback.

## Solver status semantics

- `optimal`: CP-SAT proved optimality for the configured objective.
- `feasible`: a valid solution was found, but optimality was not proven.
- `infeasible`: CP-SAT proved no hard-constraint solution exists.
- `unknown`: the time limit ended without a solution or proof of infeasibility.
- `invalid_input`: sound preprocessing found missing or contradictory inputs.
- `model_invalid`: OR-Tools rejected the mathematical model.

The API never labels `unknown` as infeasible. A timetable is persisted only after the independent validator confirms every implemented hard constraint.

## Current checkpoint

Implemented: optimization, independent validation, role security, admin master-data management, written faculty/room availability, Odd/Even term switching, immutable timetable history, published/archived backups, role-filtered views, minimum-disruption rescheduling, analytics, print layout, and CSV export.

The next planned layer is the natural-language assistant for searching records and translating solver diagnostics into conversational explanations. It will call the existing permission-checked APIs and will not bypass scheduling validation.

See [algorithm documentation](docs/ALGORITHM.md), [Phase 1 report](docs/PHASE_1.md), [Phase 2 report](docs/PHASE_2.md), and [API notes](docs/API.md).

