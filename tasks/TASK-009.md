# TASK-009 - V5 Task & Material Flow

Status: PLANNED

## Goal

단순 Goal 이동을 실제 물류 흐름처럼 Source Station → Destination Station 작업으로 확장한다.

## Deliverables

- Task Domain Model
- Task Queue
- Task Lifecycle
- Source / Destination Station
- Pickup / Drop 처리 시간
- Load 상태/위치 추적
- Task Event Log
- Deterministic Task Scenario

## Task States

QUEUED → ASSIGNED → MOVING_TO_SOURCE → PICKING → MOVING_TO_DESTINATION → DROPPING → COMPLETED

실패 상태도 명시한다.

## Constraints

- Fleet 자동 최적 배정은 V6
- 실제 Robot Sensor/ROS2 연동은 아직 금지

## Verification

- Task State Transition Test PASS
- Agent가 Source에 도착하기 전 Pickup 금지
- Pickup 후 Destination 이동
- Drop 후 COMPLETED
- Load 중복 소유/유실 없음
