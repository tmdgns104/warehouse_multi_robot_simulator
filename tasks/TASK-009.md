# TASK-009 - V5 Task & Material Flow

Status: IMPLEMENTED / AUTOMATED VERIFICATION PASS / HUMAN FACTORY FLOW VERIFICATION REQUIRED

## Goal

Replace random goals in the default demo with deterministic factory work: queue, assignment, source travel, timed pickup, destination travel, timed drop, and completion.

## Domain and Lifecycle

- `WorkStation`: neutral demo role, backing Facility ID, safe service LaneNode
- `MaterialTask`: source/destination/load/priority, lifecycle and timestamps
- `MaterialLoad`: station, robot ownership and lifecycle
- `RobotWorkState`: independent of Traffic `MotionState`
- `TaskEvent`: timestamped transition record

```text
QUEUED -> ASSIGNED -> MOVING_TO_SOURCE -> PICKING
       -> MOVING_TO_DESTINATION -> DROPPING -> COMPLETED
```

`FAILED` and `CANCELLED` are explicit terminal states. Invalid transitions raise an error.

## Factory Demo Roles and Flows

These roles are for this demo and do not claim the video's real facility meaning.

```text
Flow A: IN_A -> PROC_A -> QC_A -> OUT_A
Flow B: IN_B -> PROC_B -> BUFFER_B -> OUT_B
```

Eight work stations use unique obstacle-safe graph nodes near selected MachineBlocks.

## Assignment and Traffic Integration

- Default 16 robots; queue target 6; maximum active tasks 10
- Deterministic assignment: shortest reachable source route, then stable robot order
- No global optimization, bidding, battery model, or V6 fleet balancing
- `TrafficMotionEngine(looping=False)` performs every trip
- Predictive reservations, congestion cost, rerouting and speed coordination remain active

## Processing

- Pickup / drop duration: 2.0 / 2.0 seconds
- Pickup starts only after source arrival
- Destination is assigned only after pickup completes
- Drop starts only after destination arrival
- Completion releases load ownership and returns the robot to IDLE

## Verification

- Full tests: 65 passed
- 16 robots / 300 seconds
- Tasks created/completed: 55 / 46
- Queue/active/idle: 6 / 3 / 11
- Robot utilization: 0.2710
- Average cycle / pickup wait: 50.066 / 4.735 seconds
- Completed checkpoint trend at 100/200/300 seconds: 16 / 32 / 45 (0.05 verification step)
- Failed tasks: 0
- Lost loads / duplicate ownership: 0 / 0
- Pickup-before-arrival / drop-before-arrival: 0 / 0
- Collision/head-on/deadlock/obstacle penetration: 0 / 0 / 0 / 0

## Evidence

- `evidence/v5_factory_task_flow.png`
- `evidence/v5_factory_task_debug.png`
- `evidence/v5_factory_stress.txt`

TASK-010/V6 was not started. No commit or push was made before Human verification.
