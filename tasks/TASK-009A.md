# TASK-009A - V5.1 Factory Dispatch & Robot Utilization Tuning

Status: IMPLEMENTED / AUTOMATED VERIFICATION PASS / HUMAN FACTORY UTILIZATION VERIFICATION REQUIRED

## Root Cause

V5 reserved both task source and destination for the entire lifecycle. With only eight capacity-1 service points and overlapping flow links, this limited the 300-second run to three active tasks while six tasks remained queued and eleven robots were idle. Every completed robot also returned to parking before it could receive more work. The legacy utilization metric counted RETURNING as productive-looking busy time.

## Implementation

- Phase-aware station use: source during `MOVING_TO_SOURCE/PICKING`; destination during `MOVING_TO_DESTINATION/DROPPING`.
- Destination capacity is acquired immediately before pickup completes; a robot waits safely at its source if unavailable.
- Completed robots perform a deterministic direct handoff to the highest-priority dispatchable task before parking.
- Parking is used only when no task can be safely dispatched at completion.
- Productive, repositioning and idle time are measured independently.
- Dispatch block reasons and queued dispatchability are reported.
- Workload profiles: light, normal, busy and stress. BUSY (`queue_target=12`, `max_active=10`) is the default GUI and acceptance profile.

Task priority remains the primary queue order. A high-priority task can be temporarily skipped only when its source resource is busy, the active limit is reached, no idle robot exists, or no route exists.

## Before / After (16 robots, 300 seconds, seed 1234)

| Metric | V5 Before | V5.1 After |
|---|---:|---:|
| tasks completed | 46 | 70 |
| tasks created | 55 | 88 |
| queued | 6 | 12 |
| active at end | 3 | 6 |
| idle at end | 11 | 6 |
| average active robots | not measured | 6.866 |
| average idle robots | not measured | 7.059 |
| legacy utilization | 0.2710 | 0.5588 |
| productive utilization | not separated | 0.4291 |
| repositioning utilization | not separated | 0.1297 |
| idle ratio | not separated | 0.4412 |
| average cycle time | 50.066 s | 60.350 s |
| direct handoffs | 0 | 22 |
| parking returns | every completion | 48 |

The longer cycle time is an explicit contention trade-off of higher participation. Eight capacity-1 stations cap theoretical productive utilization at 0.50 for 16 robots, so the suggested 0.60 target cannot be reached without adding capacity or stations.

## Dispatch Diagnostics

- blocked source station: 74
- blocked destination station: 55
- blocked active limit / no idle / no route: 0 / 0 / 0
- queued dispatchable after each complete dispatch pass: 0
- queued blocked at end: 12

## Safety and Stress

- Full tests: 71 passed
- 16 robots: collision/head-on/deadlock/obstacle penetration = 0
- Lost loads / duplicate ownership / invalid pickup/drop = 0
- 24 robots: 8 completed, productive utilization 0.2627; safety values remain 0

## Evidence

- `evidence/v5_1_factory_utilization.png`
- `evidence/v5_1_factory_dispatch_debug.png`
- `evidence/v5_1_factory_utilization_stress.txt`

TASK-010/V6 was not started. No commit or push was made.
