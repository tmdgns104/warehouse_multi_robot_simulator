# TASK-009E - V5.5 Mission Visualization & Operational Explainability

## Status

IMPLEMENTED / AUTOMATED VERIFICATION PASS / HUMAN MISSION VISUALIZATION VERIFICATION REQUIRED

Human GUI verification 전 COMPLETE, commit 또는 push로 처리하지 않는다.

## Scope

V5.4 Domain/dispatch/traffic/timing을 변경하지 않고 Robot이 무엇을 하는지(Operational State)와
왜 하는지(Business Mission)를 5~10초 안에 이해할 수 있는 presentation을 제공한다.

## Implementation

- read-only `RobotMissionView` and `MissionCount`
- LINE_SUPPLY→SUPPLY, WIP_TRANSFER→WIP, QC_TRANSFER→QC, OUTBOUND_MOVE→OUT
- active Robot badge, 16-Robot compact panel, active/completed mission counts
- click selection and actual remaining route highlight
- actual Station service nodes as S/D markers
- LoadState.ON_ROBOT plus owner identity as cargo source of truth
- selected WorkOrder/Lot/Request/Task/priority/reason/lifecycle details
- normal vs debug production views

No fake mission, dummy task, timing change, new dispatch algorithm or V6 optimizer was added.

## Acceptance Baseline

16 robots, seed 1234, 300 seconds remains exactly:

- production 6/20
- 22 requests created, 20 completed
- average lead time 34.035s
- safety counters all zero

Mission created/completed: SUPPLY 8/8, WIP 4/3, QC 4/3, OUT 6/6.

## Evidence

- `evidence/v5_5_mission_visualization.png`
- `evidence/v5_5_selected_robot.png`
- `evidence/v5_5_mission_debug.png`
- `evidence/v5_5_mission_summary.txt`

## Human Gate

Run `python3 app.py --production-demo`, click active Robots, and confirm mission/state separation,
Lot and endpoints, cargo-after-pickup behavior, actual route/S/D highlight, WorkOrder/Machine relation,
and collision-free movement. TASK-010 / V6 remains out of scope.
