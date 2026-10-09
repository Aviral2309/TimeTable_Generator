# Phase 2 implementation report

> Historical checkpoint: the current application supersedes the seeded sign-in flow below with first-admin bootstrap and empty, admin-entered academic data.

## Delivered

Phase 2 adds a responsive React/TypeScript application backed exclusively by the FastAPI service. The interface includes login, grouped navigation, role-specific dashboards, a 12-step preparation workflow, faculty/room/lab/reservation management, CP-SAT versus hybrid selection, visible generation results, timetable filters, weekly grid, analytics, and authenticated CSV download.

Security is implemented server-side with salted PBKDF2 password hashes, signed expiring bearer tokens, active-user checks, and endpoint-level role dependencies. Demo users represent administrator, faculty, and student access. Faculty and student timetable queries are filtered by their linked faculty/group identity.

## Verification

- `python -m pytest`: 18 tests passed.
- `npm run build`: TypeScript compilation and Vite production build succeeded (1,637 modules).
- Alembic migration `e02d1fb10af5` upgraded the Phase 1 database.
- Seed upgrade added all three demonstration accounts.

## Demonstration workflow

1. Sign in as `admin@example.edu` with `Demo@123`.
2. Review the preparation workflow.
3. Add or inspect faculty, rooms/labs, and fixed reservations.
4. Choose CP-SAT or hybrid mode and generate.
5. Confirm the independent validator status and view the master timetable.
6. Filter by participant group and download CSV.
7. Sign in as faculty/student to observe role-filtered navigation and schedule access.

## Real semester configuration extension

The preparation workflow now reads and writes real semester offerings. There is one combined cohort—no sections—for each selected semester. Subjects capture weekly frequency, duration, enrollment, activity type, faculty and eligible room/lab using reusable master-data dropdowns. Exactly three distinct cohorts are jointly prevalidated and converted from database records into the solver domain. Generation takes a configuration snapshot through the selected semester IDs and the independent validator checks the result. Student gaps carry the dominant refinement penalty; the seeded configuration reaches zero student gaps with deterministic seed 42.

## Boundaries carried into Phase 3

PDF/Excel export, immutable publication workflow, change requests, minimum-disruption rescheduling, manual drag-and-drop edits, and broader end-to-end browser automation belong to Phase 3.

