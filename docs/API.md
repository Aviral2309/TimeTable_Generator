# API notes

Interactive OpenAPI documentation is served at `/docs`.

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

