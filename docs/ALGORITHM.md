# Scheduling algorithm

Timetabling is a constraint optimization problem because each required teaching session must receive one assignment while globally sharing scarce people, rooms, equipment, and time. Feasibility and preference quality are distinct: hard rules cannot be traded for a better-looking timetable.

## CP-SAT formulation

For required session `s`, eligible room `r`, day `d`, and valid starting period `t`, preprocessing creates a Boolean variable:

`x[s,r,d,t] in {0,1}`

A candidate is omitted if its room is too small or the wrong type, required equipment is missing, any occupied period is blocked/outside the day, the room is unavailable, or a faculty member is unavailable. A laboratory is exactly two consecutive periods and its only eligible starts are the first period or the final valid two-period block of the working day. It therefore cannot cross lunch or sit between theory classes.

Each session is assigned exactly once:

`sum(r,d,t) x[s,r,d,t] = 1`

For every occupied period, room capacity (normally one), global faculty identity, and explicit participant group receive at-most-one constraints. Fixed reservations remove conflicting candidates. Daily limits constrain the duration-weighted sum for a faculty/day; a sound preprocessing check rejects weekly demand above a hard weekly limit. Fixed sessions have only their declared time/room candidates. Parallel elective alternatives share day and start-period indicator equations while retaining separate rooms and participant groups.

The initial objective minimizes weighted faculty avoidance, unsuitable lab time preferences, late periods, and repeated occurrences of one offering on the same day. Status values are reported without reinterpretation.

## Independent validation

The validator reconstructs occupancy from returned assignments without accessing CP-SAT variables. It checks assignment completeness, room eligibility/capacity/equipment, valid consecutive periods, lab boundary placement, fixed sessions, availability, faculty/room/group collisions, fixed reservations, and daily workload. It calculates student and faculty gaps over teaching periods only, so a configured lunch break is not incorrectly counted as an idle gap. Persistence occurs only when this pass succeeds.

## Hybrid refinement

The direct Simulated Annealing stage starts with a validated CP-SAT solution. It proposes an eligible room/time move, independently validates the complete candidate, and rejects every hard-constraint violation. A worse feasible candidate of cost increase `delta` is accepted with:

`P = exp(-delta / temperature)`

Temperature cools geometrically. Best-solution tracking guarantees the returned timetable is no worse than the initial timetable according to the refinement cost. If no improvement exists, the original solution remains intact. The random seed and move statistics are returned for reproducibility.

## Diagnostics

Preprocessing returns verified errors for missing faculty, invalid enrollment, absent room/capacity/equipment/consecutive windows, hard weekly overload, and reservations that remove every remaining candidate. Solver-proven infeasibility and time-limit `unknown` are distinct. More advanced assumption-core diagnostics and relaxation suggestions remain a future enhancement.

