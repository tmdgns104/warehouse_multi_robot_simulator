# TASK-014 - V10 Nav2 Autonomous Navigation

Status: PLANNED

## Goal

Fleet Task의 Destination을 Gazebo AMR의 실제 Nav2 Goal로 연결한다.

## Deliverables

- Map/Localization 구성
- Robot별 Nav2 설정
- `NavigateToPose` 계열 Goal Adapter
- Fleet Task → Nav2 Goal 연결
- Navigation Result/Failure → Fleet State 환류
- Multi-Robot Goal Scenario
- Recovery/Cancel 상태 처리

## Constraints

- Fleet Manager가 직접 Wheel Velocity를 계산하지 않음
- Nav2 Local Obstacle Avoidance와 Fleet Traffic Coordination 책임을 구분
- Traffic Manager가 Nav2 내부 Planner를 임의 대체하지 않음

## Verification

- 단일 Robot Goal 도착
- 복수 Robot 개별 Goal 실행
- Goal 성공/실패/취소 상태 환류
- `/cmd_vel`은 Nav2 경로를 통해 발생
- Robot Namespace 격리 유지
