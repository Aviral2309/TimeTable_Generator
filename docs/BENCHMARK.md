# Phase 1 benchmark

Measured on 2026-10-09 using the checked-in three-semester demonstration problem, OR-Tools 9.15, a 15-second limit, one CP-SAT worker, random seed 42, and 300 direct annealing iterations.

| Measure | CP-SAT | Hybrid returned solution |
|---|---:|---:|
| Solver status | OPTIMAL | starts from CP-SAT result |
| CP-SAT runtime | 0.1333 s | same initial solve |
| Sessions scheduled | 31 | 31 |
| Independent validation | valid | valid |
| CP-SAT model objective | 0 | not recomputed by CP-SAT |
| Separate gap-based refinement cost | 76 | 41 |
| Accepted annealing moves | — | 139 |
| Best-cost improvements | — | 8 |

The two objectives are intentionally reported separately: the Phase 1 CP-SAT objective contains candidate-local preferences and same-offering/day distribution, while the refinement cost measures student and faculty gaps. Therefore the CP-SAT objective of zero does not mean the timetable has zero gaps. This is one reproducible local observation, not a promise that hybrid refinement always improves every dataset or that runtime is fixed.

Reproduce from the repository root:

```powershell
python -c "from app.scheduling.demo import build_demo_problem; from app.scheduling.solver import solve; from app.scheduling.annealing import refine,soft_cost; from app.scheduling.validator import validate_schedule; p=build_demo_problem(); r=solve(p,15,42); h,m=refine(p,r.assignments,300,42); print({'cp_status':r.status,'cp_runtime_seconds':r.runtime_seconds,'cp_objective':r.objective,'cp_soft_cost':soft_cost(p,r.assignments),'hybrid_soft_cost':soft_cost(p,h),'hybrid_metrics':m,'valid':validate_schedule(p,h)[0],'sessions':len(h)})"
```

