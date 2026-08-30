# TASK-008 - V4 Predictive Multi-Agent Traffic Control

Status: IMPLEMENTED / AUTOMATED VERIFICATION PASS / HUMAN TRAFFIC VERIFICATION REQUIRED

## Goal

16개 이상의 MobileEntity가 지속 운행할 때 충돌 이후 정지하는 방식보다 미래 병목을 예측해 route, reservation timing, speed를 조절한다.

## Deliverables

- Continuous goal reassignment and deterministic scenario generator
- Node/Edge hard safety reservation
- 3~5 edge predictive soft-reservation horizon with expiry
- Congestion-aware route cost and traffic-aware A*
- Cooldown/improvement-threshold dynamic rerouting
- Preferred/current/target speed coordination and smoothing
- Traffic zones and capacity penalties
- Wait-for cycle detection and deadlock-preventing response
- Starvation priority, stuck detection and bounded recovery
- Throughput/moving/wait/speed/reroute/deadlock/collision metrics
- 16 Entity 300-second acceptance and 24 Entity scalability evidence

## Safety / Flow Acceptance

- collision_count = 0
- head_on_conflict_count = 0
- deadlock_count = 0
- indefinite_wait_count = 0
- completed trips continue increasing
- no stale reservations
- long stop events are measured and minimized, not hidden

## Constraints

- No ROS2/Gazebo/Nav2
- No CBS or complete MAPF solver
- No V5 task/material workflow or V6 fleet assignment
- Preserve V1/V2/V3 regression and legacy commands

## Completion Gate

Automated verification and actual 16/24 Entity stress metrics must be recorded. Human pygame traffic verification remains required.

## Measured Result

- 48 total tests PASS
- 16 entities / 300 seconds: 277 trips, moving ratio 0.9892, max wait 4.650s
- 16 entities: collisions/head-on/deadlocks/indefinite waits/stops over 5s = 0
- 24 entities / 300 seconds: 384 trips, moving ratio 0.9355, max wait 5.017s
- 24 entities: collisions/head-on/deadlocks/indefinite waits = 0; stops over 5s = 18
- Evidence: `evidence/v4_predictive_traffic.png`, `evidence/v4_predictive_stress.txt`
