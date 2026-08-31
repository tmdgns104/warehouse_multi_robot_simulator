# TASK-009C - V5.3 Actual Fleet Motion & Continuous Factory Flow

Status: IMPLEMENTED / AUTOMATED VERIFICATION PASS / HUMAN ACTUAL FLEET MOTION VERIFICATION REQUIRED

## Root Cause

V5.2 `ENGAGED` proved only that a robot owned a task. Position instrumentation showed
80.36% actual motion but also 8.61% stationary holding, 44.9 seconds maximum continuous
stationary time, and 31 long holding events. Random link generation plus priority-only
dispatch concentrated twelve of sixteen active jobs on two downstream Flow A links.

## Implementation

- Position delta greater than 0.01 px is the only definition of actual movement.
- Physical activity is partitioned into movement, service, traffic wait, resource wait,
  flow hold, and true idle after a 10-second warm-up.
- Per-robot distance and stationary time, station pressure, and flow-link WIP are recorded.
- BUSY/STRESS workload generation deterministically balances the six existing links.
- Bounded dispatch prefers free source staging and low link/station pressure.
- Each station has three distinct obstacle-safe staging LaneNodes; service capacity stays one.
- GUI V5.3 displays physical activity rather than merely the assigned work-state name.

## Acceptance

16 robots / 300 seconds / seed 1234 / BUSY:

- completion trend 33 / 76 / 116; V5.2 completed 87
- actual motion 0.8150; service 0.1007; useful activity 0.9157
- holding 0.0020; average moving 13.041; average holding 0.033
- cycle time 60.287 seconds, down from 80.600
- true idle, collision, head-on, deadlock, obstacle penetration: 0

24 robots completed 127 tasks with 0.7381 actual motion and 0.0292 holding.
Traffic wait rises to 0.0882, identifying congestion rather than hidden holding as the
remaining scaling constraint.

## Evidence

- `evidence/v5_3_actual_fleet_motion.png`
- `evidence/v5_3_motion_debug.png`
- `evidence/v5_3_factory_flow_stress.txt`

TASK-010/V6 was not started. No commit or push before Human verification.
