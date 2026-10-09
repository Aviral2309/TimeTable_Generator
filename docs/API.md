# API notes

Interactive OpenAPI documentation is served at `/docs`.

Authenticated endpoints expect `Authorization: Bearer <token>`. Obtain the token from `POST /api/auth/login`. Authorization is enforced in backend dependencies; the UI is not the security boundary.

## Authentication and roles

- `POST /api/auth/login`
- `GET /api/auth/me`
- Admin: generation, analytics, and master-data writes
- Faculty: own timetable plus permitted master-data reads
- Student: published timetable filtered to their participant group

## Master data

- `GET/POST /api/faculty`
- `GET/POST /api/rooms`
- `GET/POST /api/reservations`

List endpoints are paginated. Writes require the administrator role.

## `GET /api/health`

Returns service readiness.

## `POST /api/generation/demo`

Example body:

```json
{
  "academic_year_id": 1,
  "solver_mode": "hybrid",
  "time_limit_seconds": 15,
  "random_seed": 42
}
```

The response includes the exact solver status, assignments, diagnostics, independent validation result, quality metrics, and optional refinement statistics. A database generation run and validation report are always recorded; a timetable is recorded only for a validated solution.

## `GET /api/generation/runs/{run_id}`

Returns persisted solver metadata and diagnostics for reproducibility.

## Timetable, export, and analytics

- `GET /api/timetables/latest` returns the authoritative scheduled sessions, filtered for faculty and students.
- `GET /api/export/latest.csv` produces a downloadable schedule from those same records.
- `GET /api/analytics/summary` returns recent generation statuses and metrics for administrators.

