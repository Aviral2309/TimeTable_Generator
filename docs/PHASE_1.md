# Phase 1 implementation report

## Implemented features

The empty repository was initialized as a Python monorepo backend. Phase 1 includes the normalized operational schema, generated Alembic migration, local/production database settings, seed script, real CP-SAT engine, direct Simulated Annealing refinement, independent validation, generation persistence service, FastAPI routes, Docker configuration, and technical documentation.

The demonstration jointly schedules EE III, V, and VII, including shared faculty, hard home classrooms, a shared first-year lab reservation, four two-hour lab batches, enrollment-aware parallel electives, and a fixed external lecture.

## Verification

Run `python -m pytest`. The tests cover simultaneous semester scheduling, collision absence, fixed reservations, consecutive laboratories/lunch, elective parallelism and capacities, home rooms, fixed external teaching, inadequate capacity, faculty unavailability/overload, absent lab windows, reservation contradictions, injected validator conflicts, annealing feasibility/non-regression, health behavior, and persisted generation workflow.

## Decisions and assumptions

- Period indices are configuration data; the solver contains no clock-time constants.
- Student participation is represented by explicit group identifiers. A lab batch also claims its parent section in this Phase 1 demo, conservatively preventing full-section theory overlap.
- Labs default to exclusive occupancy. A room can permit more simultaneous sessions only through explicit `concurrent_capacity`.
- SQLite is the functional local fallback. PostgreSQL remains the deployment target.
- All people and institutional data are fictional.

## Remaining work

Phase 2 should add authentication/RBAC, master-data CRUD, arbitrary database-to-solver mapping, the preparation wizard, async job progress, React/TypeScript views, imports/exports, and fuller CP-SAT soft-cost modeling. Phase 3 should add requests, local/global minimum-disruption rescheduling, immutable publication versions, manual edit validation, comparisons, completed exports, analytics, and deployment hardening.

