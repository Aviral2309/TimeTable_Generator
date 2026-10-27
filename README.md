# SGSITS Intelligent Academic Timetable System

A constraint-based timetable preparation, optimization, validation, publication, and rescheduling system for the Department of Electrical Engineering at Shri G. S. Institute of Technology & Science (SGSITS), Indore.

The system replaces manual timetable assembly with an administrator-controlled workflow backed by Google OR-Tools CP-SAT. It generates the three active semester timetables together, verifies every saved result independently, preserves previous versions, and provides read-only faculty and student views of published schedules.

## Project status

The complete department workflow is implemented and operational:

- administrator-first setup and SGSITS-branded interface;
- Odd term semesters `3, 5, 7` and Even term semesters `2, 4, 6`;
- one combined cohort per semester rather than section-wise timetables;
- master-data CRUD for faculty, rooms/labs, accounts, semesters, subjects, allocations, and reservations;
- admin-only faculty/room availability and reservation management;
- simultaneous multi-semester generation using CP-SAT with optional hybrid refinement;
- independent validation, quality metrics, diagnostics, history, publication, and archives;
- dynamic faculty/room rescheduling that creates a new immutable version;
- semester and faculty timetable views, CSV export, and portrait A4 print/PDF layout;
- private database backup, reusable starter database, timetable JSON snapshots, and verified SQLite restoration.

Natural-language/LLM assistance is a possible future layer; it is not required by the scheduling engine and is not part of the current release.

## User roles

| Role | Access |
| --- | --- |
| Administrator | Full setup, CRUD, availability, reservations, account management, generation, validation, publication, rescheduling, analytics, backups, and restoration |
| Faculty | Self-register against an existing faculty record, then read-only access to their published faculty timetable, directories, downloads, and password change |
| Student | Self-register by academic year, semester, and batch, then read-only access to the matching published timetable, directories, downloads, and password change |

Faculty and students cannot modify timetable or department data. They create their own `@sgsits.ac.in` accounts from the login page, so the administrator does not enter their passwords. A faculty member must select the matching preloaded faculty record and use its stored email. Students select their academic year, semester, and batch. Additional administrator registrations stay inactive until an existing administrator enables them in **User Access**.

## Scheduling rules

### Hard constraints

A saved timetable must satisfy all applicable hard constraints:

- no faculty, room, laboratory, cohort, batch, or elective collision;
- faculty and room unavailability, including written reasons;
- fixed lectures and room/faculty/student-group reservations;
- room capacity, room type, supported capabilities, and simultaneous-group limits;
- faculty weekly, daily, and consecutive-period workload limits;
- exact weekly theory, lecture/tutorial, and practical session counts;
- separate or shared faculty assignments for theory and lecture/tutorial components;
- consecutive multi-period laboratories that cannot cross lunch;
- laboratories at the start or end of a teaching block where feasible;
- parallel elective alternatives at the same day and time;
- no regular full-cohort class overlapping its batch lab or elective block;
- hard home-room allocation when enabled;
- no delayed first class after lunch when a cohort has no morning class.

### Optimization objectives

Among valid schedules, the engine minimizes or balances:

- student/cohort gaps;
- isolated one-period teaching days;
- delayed and late student periods;
- uneven daily class distribution;
- avoidable room changes between consecutive classes;
- faculty gaps;
- repeated same-subject placement on one day;
- preference penalties and overall resource utilization.

Every solution is checked again by an independent validator before it can be persisted.

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, React Router, TanStack Query |
| API | FastAPI, Pydantic |
| Scheduling | Google OR-Tools CP-SAT and feasibility-preserving Simulated Annealing refinement |
| Persistence | SQLAlchemy, Alembic, SQLite for local/demo use, PostgreSQL for deployment |
| Testing | Pytest and TypeScript/Vite production build |

## Architecture

```text
React administration and read-only portals
                  |
                  v
             FastAPI routes
                  |
       +----------+-----------+
       |                      |
       v                      v
Setup/auth services     Generation/rescheduling services
       |                      |
       v                      v
 SQLAlchemy models      Database problem builder
       |                      |
       v                      v
SQLite/PostgreSQL       Preprocessing -> CP-SAT -> optional refinement
                                      -> independent validation
                                      -> immutable timetable + backup
```

The optimization package is separated from the FastAPI and SQLAlchemy layers, allowing the mathematical model and validator to be tested independently.

## Repository layout

```text
backend/
  app/
    api/              Authentication, setup, master data, generation, backup APIs
    core/             Configuration and security
    db/               SQLAlchemy session setup
    models/           Persistent entities
    scheduling/       Domain model, preprocessing, solver, refinement, validator
    services/         Generation, rescheduling, and backup workflows
  alembic/            Database migrations
  tests/              Backend and solver tests
frontend/
  public/             SGSITS visual assets
  src/                React application, API client, and styles
docs/                  Algorithm, API, phase, benchmark, and handover documentation
scripts/               Optional development/maintenance scripts
```

## Local installation on Windows

### Requirements

- Python 3.11 or newer
- Node.js 20 or newer with npm
- PowerShell

### 1. Install the backend

Run these commands from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
Copy-Item .env.example .env
python -m alembic upgrade head
```

For any non-disposable installation, edit `.env` and replace `SECRET_KEY` with a long random value before creating accounts.

Start the API:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Backend health check: `http://127.0.0.1:8000/api/health`

Interactive API documentation: `http://127.0.0.1:8000/docs`

### 2. Install the frontend

Open a second PowerShell window in the project root:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`.

Vite proxies `/api` requests to `http://127.0.0.1:8000`. Set `VITE_API_TARGET` before running the frontend only when the backend uses another address.

## First-time setup

On an empty database, the application asks for the first administrator account. The administrator should then complete **Start Setup** in this order:

For a normal fresh clone, the repository automatically copies `starter/sgsits-department-starter.db` to `timetable.db` on first backend startup. This supplies the current sanitized SGSITS department records and timetable history while still asking the recipient to create their own first administrator. Set `INSTALL_STARTER_DATABASE=false` before first startup when an entirely blank installation is required.

1. Institute and department.
2. Academic year and Odd/Even term.
3. Working days, periods, and manually selected lunch period.
4. Faculty records and workload limits.
5. Theory rooms and laboratories, including capacities and supported capabilities.
6. The three active semester cohorts and optional home rooms.
7. Every subject and its theory/lecture/tutorial/practical frequency.
8. Faculty, batch, elective, room, and laboratory allocations.
9. Faculty and room unavailability with written reasons.
10. Fixed reservations and external constraints.
11. Configuration cross-check.
12. Generation, validation, review, and publication.

Generation remains disabled until all required categories are complete. The backend accepts configured database records only; it does not silently fall back to fictional demo data.

## Normal operating workflow

1. Activate or create the correct Odd/Even academic term.
2. Review faculty, rooms, subject schemes, availability, and reservations.
3. Run **Cross-check configuration** and resolve every blocker.
4. Generate all three semester timetables together.
5. Review the version's independent validation report and quality metrics.
6. Inspect semester and faculty-specific views.
7. Print or save the semester view as portrait A4; each semester occupies one page.
8. Mark the approved version **Published**.
9. Download a private database backup after approval.

Draft and archived versions remain visible to administrators. Faculty and students see only published versions appropriate to their linked identity/group.

## Timetable history and rescheduling

- A successful generation creates a new timetable version rather than editing an older one.
- Each version stores its generation run, validation report, metrics, sessions, status, and checksummed JSON snapshot.
- Versions can be `draft`, `published`, or `archived`.
- Dynamic rescheduling previews the minimum-disruption response to a faculty or room issue.
- Applying a valid proposal creates another timetable version and preserves the source version.
- The rescheduling history records the reason, affected sessions, moved sessions, actor, and diagnostics.

## Backup types

### Private backup

Contains all operational data, including login accounts and password hashes. Store it securely. It is suitable for restoring the same installation.

### Starter database

Retains department master data, terms, subjects, availability, timetable history, and other reusable records, but removes all login accounts. A receiving department creates its own first administrator. Changing the administrator does not remove the department data.

The repository also carries a sanitized copy at `starter/sgsits-department-starter.db`. It is installed automatically only when the configured local SQLite database does not yet exist. Existing databases are never overwritten.

### Timetable JSON snapshot

Created automatically for every generated or rescheduled version. It protects the exact schedule and validation metrics, but it does not replace a full database backup.

### SQLite restoration

The administrator can upload a private SQLite backup from the dashboard. Before restoration, the server checks file type, size, SQLite integrity, required tables, and the presence of an active administrator. It then creates `backups/pre-restore-<timestamp>.db` as a rollback copy.

The in-app database-file backup and restore endpoints apply only to file-based SQLite installations. PostgreSQL deployments should use managed PostgreSQL backup/restore procedures.

## Verification

Run the backend suite from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Build the frontend:

```powershell
cd frontend
npm run build
```

The repository currently contains automated coverage for authentication, role checks, first-run setup, master-data workflows, availability, database-driven generation, hard constraints, timetable validation reports, backups, and dynamic rescheduling.

## PostgreSQL/Docker deployment

The included Compose file starts PostgreSQL and the FastAPI backend:

```powershell
docker compose up --build
```

It does **not** package or serve the React frontend. Build `frontend/` separately and serve `frontend/dist/` using the institution's chosen web server, or run Vite separately for a development/demo environment.

Before production use:

- change database credentials and `SECRET_KEY`;
- restrict CORS to the deployed frontend origin;
- apply Alembic migrations;
- terminate TLS at the reverse proxy;
- use scheduled encrypted PostgreSQL backups;
- avoid the development `--reload` option;
- review account provisioning and password-sharing procedures with the department.

## Solver status meanings

| Status | Meaning |
| --- | --- |
| `optimal` | CP-SAT found a valid solution and proved optimality for the configured objective |
| `feasible` | A valid solution was found, but optimality was not proven within the limit |
| `infeasible` | CP-SAT proved that no schedule satisfies the current hard constraints |
| `unknown` | The time limit ended without a solution or proof of infeasibility |
| `invalid_input` | Preprocessing detected missing or contradictory configuration |
| `model_invalid` | OR-Tools rejected the generated mathematical model |
| `failed` | An unexpected generation failure was recorded |

The application never reports `unknown` as `infeasible`, and it persists a timetable only after independent validation succeeds.

## Troubleshooting

### Site cannot be reached

Confirm that both processes are running:

- frontend on `http://127.0.0.1:5173`;
- backend health endpoint on `http://127.0.0.1:8000/api/health`.

### “Request failed” or “Failed to fetch”

Check the backend process first, then confirm Vite's proxy target and the configured CORS origin. API validation errors are returned with a specific reason when the backend is reachable.

### Incorrect email or password

Select the workspace matching the account's stored role. An administrator can reset another account from **User Access**. A signed-in user can change their own password from **My Account**.

### Faculty/student sees no timetable

Non-admin accounts see only a timetable version marked **Published**. Confirm that the account is linked to the correct faculty record or semester/batch group and that the administrator published the intended version.

### Generation fails

Read the configuration and solver diagnostics shown in the UI. Common causes are missing faculty, insufficient room capacity/capabilities, incompatible availability, fixed reservation conflicts, or too few consecutive periods for a laboratory.

## Documentation

- [Department handover guide](docs/DEPARTMENT_HANDOVER.md)
- [Algorithm and constraint model](docs/ALGORITHM.md)
- [API notes](docs/API.md)
- [Benchmark notes](docs/BENCHMARK.md)
- [Phase 1 report](docs/PHASE_1.md)
- [Phase 2 report](docs/PHASE_2.md)

## Data safety

Do not commit `.env`, database files, private backups, generated credentials, or password lists. The repository's `.gitignore` excludes common local database, environment, build, dependency, cache, and log artifacts.
