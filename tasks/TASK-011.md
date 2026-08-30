# TASK-011 - V7 Video-like Digital Twin UI

Status: PLANNED

## Goal

V2~V6에서 만든 Layout, Lane, Traffic, Task, Fleet을 Reference 영상과 유사한 하나의 통합 2D 관제 화면으로 완성한다.

## Deliverables

- 영상형 Layout 최종 조정
- Agent/Load/Station 상태 시각화
- Route/Reservation 선택 표시
- Start / Pause / Reset / Speed Control
- Agent/Station 선택
- Fleet/Task/Traffic Metrics Panel
- Scenario 선택 또는 고정 Seed Demo
- WorldSnapshot 기반 Renderer Interface

## Constraints

- 화면이 Domain 객체 내부 상태를 직접 변경하지 않도록 Command/API 경계 유지
- ROS2/Gazebo 연결은 아직 Mock/Adapter Interface까지만 허용

## Verification

- 10+ Agent 동시 동작
- Task/Fleet/Traffic 상태가 화면과 일치
- 반복 실행 가능한 Demo
- 자동 Test PASS
- Reference 영상과 Human Visual Comparison 수행

## Completion Gate

V7 완료 시 "영상 재현 단계 완료" 여부를 Human이 판단한다.
