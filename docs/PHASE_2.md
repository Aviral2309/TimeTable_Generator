# Phase 2 implementation report

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

## Boundaries carried into Phase 3

The browser preparation flow currently operates on the seeded, internally consistent demonstration configuration. General database-to-domain mapping for every possible scheme/offering configuration needs expansion before institute-wide deployment. PDF/Excel export, immutable publication workflow, change requests, minimum-disruption rescheduling, manual drag-and-drop edits, and full end-to-end browser automation belong to Phase 3.

