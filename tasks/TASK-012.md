# TASK-012 - V8 ROS2 Architecture Integration

Status: PLANNED

## Goal

V7까지의 Domain Core를 유지하면서 ROS2 Humble Adapter/Node 계층을 추가한다.

## Deliverables

- ROS2 Workspace/Package 구조 설계
- Fleet Manager Node
- Task Manager Node
- Traffic Manager Node
- Robot State Adapter
- Digital Twin Bridge Interface
- Robot Namespace Convention
- Launch/Config 기본 구조
- ROS2 없이도 Domain Unit Test 가능한 구조 유지

## Environment

- Ubuntu 22.04
- ROS2 Humble

## Constraints

- Gazebo Robot Spawn은 V9
- Nav2는 V10
- Fleet Manager가 `/cmd_vel`을 직접 생성하지 않음
- 불필요한 Custom Message 남발 금지

## Verification

- Packages build
- ROS2 node discovery
- 기본 Topic/Service/Action interface smoke test
- Domain Regression PASS
- Namespace collision 없음
