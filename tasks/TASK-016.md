# TASK-016 - V12 Multi-AMR Warehouse Digital Twin

Status: PLANNED

## Goal

영상 재현에서 시작한 2D 관제 프로그램과 ROS2/Gazebo/Nav2 다중 AMR 시스템을 하나의 End-to-End Digital Twin으로 통합한다.

## Required Flow

```text
Task Create
→ Fleet Assignment
→ Traffic Coordination
→ Nav2 Goal
→ Gazebo Robot Movement
→ /odom /tf /navigation state
→ Digital Twin Bridge
→ 2D Dashboard Update
→ Task Complete
```

## Deliverables

- End-to-End Launch/Run Guide
- Multi-AMR Scenario
- Task Queue + Fleet + Traffic + Nav2 통합
- Gazebo ↔ 2D Dashboard 실시간 동기화
- Metrics/Events
- Failure/Recovery Scenario
- 자동 Regression Suite
- 초보자용 Architecture/실행 문서

## Verification

- 최소 3대 AMR 동시 Scenario
- 각 Robot에 서로 다른 Task 배정
- Nav2 기반 실제 이동
- Task Completion 상태 일치
- Dashboard 위치/상태가 Gazebo와 동기화
- Robot 간 Namespace/TF 충돌 없음
- End-to-End Test PASS
- Human Visual Verification PASS

## Final Gate

V12 완료 시 프로젝트를 "ROS2 기반 Multi-AMR Warehouse Digital Twin & Fleet Management System"으로 정의할 수 있어야 한다.
