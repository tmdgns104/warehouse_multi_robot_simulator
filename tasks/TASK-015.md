# TASK-015 - V11 ROS2 ↔ Digital Twin Synchronization

Status: PLANNED

## Goal

2D Dashboard의 Agent 위치/상태 Source를 내부 Animation에서 실제 ROS2/Gazebo State로 전환한다.

## Deliverables

- DigitalTwinBridge
- `/odom` / TF → 2D 좌표 변환
- Robot State / Navigation State 수집
- Task/Fleet/Traffic 상태 Snapshot 통합
- WorldSnapshot Interface
- 내부 Simulation Source와 ROS2 Source 선택 가능 구조
- 연결 끊김/오래된 State 표시

## Constraints

- Renderer가 ROS2 API를 직접 호출하지 않음
- 좌표 변환을 UI 내부 Magic Number로 처리하지 않음
- Gazebo/ROS2 State가 연결되면 Dashboard 위치의 Source of Truth가 됨

## Verification

- Gazebo Robot 이동 시 2D Agent 위치 동기화
- Robot별 Heading/State 대응
- ROS2 Update 중단 시 stale 상태 감지
- 여러 Robot ID 매핑 오류 없음
- 2D/Gazebo 위치 오차 허용 기준 문서화
