# Requirements

## 1. Scope

이 문서는 V1 Prototype부터 V12 최종 Multi-AMR Digital Twin까지의 요구사항을 정의한다.

현재 개발의 다음 목표는 **V2 Video Layout Reconstruction**이다.

---

## 2. Reference Fidelity Requirements

### RF-001 Visual Reference

V2~V7의 시각적/동작적 목표는 프로젝트 Reference 영상이다.

Repository에는 향후 다음 경로로 원본을 보관한다.

```text
reference/warehouse_reference.mp4
```

### RF-002 Evidence vs Interpretation

영상에서 직접 확인되는 사실과 개발 편의를 위한 추정을 구분한다.

영상만으로 의미가 확인되지 않는 Entity는 `MobileAgent`, `Load`, `Machine`, `Station` 등 중립적 이름을 사용한다.

### RF-003 Visual Similarity

V2 통합 화면은 기존 V1의 큰 Grid Cell/원형 Robot 중심 화면보다 다음 특징을 우선한다.

- 밝은 평면도 배경
- 반복 설비 Layout
- 얇은 Lane/Route Network
- 작은 이동 Entity
- 여러 Entity의 동시 이동
- 상단/중앙/좌우/하단 작업 영역 구분

---

## 3. V1 - Core Prototype [Completed]

기존 기능을 Regression Baseline으로 유지한다.

- Grid Map
- A* Path Planning
- Robot State
- Multi-Robot Tick
- Same-cell conflict prevention
- Head-on swap prevention
- Unit Tests

V2 이후 구조 변경 시에도 V1 핵심 테스트의 의미를 잃지 않도록 필요한 경우 Adapter 또는 새 Regression Test로 대체한다.

---

## 4. V2 - Video Layout Reconstruction

### FR-V2-001 Layout

영상 프레임을 분석하여 주요 작업 영역, 설비 블록, 이동 Network의 상대적 배치를 2D 좌표계로 재구성한다.

### FR-V2-002 Rendering

UI는 영상과 유사한 밝은 산업 자동화 평면도 스타일을 제공한다.

### FR-V2-003 Entity Types

최소 다음 중립 Entity를 표현할 수 있어야 한다.

- MobileAgent
- Load
- Station
- Machine
- Marker

### FR-V2-004 Data-driven Layout

설비와 Lane 위치를 UI 코드에 전부 하드코딩하지 않고 Layout Model/Data와 Rendering을 분리한다.

---

## 5. V3 - Lane Graph + Continuous Motion

### FR-V3-001 Lane Graph

이동 Network를 Node와 Directed/Undirected Edge의 Graph로 표현한다.

### FR-V3-002 Route Planning

MobileAgent는 Grid의 임의 Cell이 아니라 Lane Graph 상의 Node/Edge를 따라 이동한다.

### FR-V3-003 Smooth Motion

Edge 이동은 한 Tick마다 셀 순간이동이 아니라 `progress 0.0~1.0` 기반 보간으로 화면상 연속 이동한다.

### FR-V3-004 Routing

Graph A* 또는 Dijkstra를 이용해 Source Station에서 Destination Station까지 Route를 계산한다.

---

## 6. V4 - Multi-Agent Traffic Control

### FR-V4-001 Node Reservation

한 시점에 충돌 가능한 Node 진입을 예약/제어한다.

### FR-V4-002 Edge Reservation

좁은 Edge에서 반대 방향 Agent의 동시 진입을 방지할 수 있어야 한다.

### FR-V4-003 Intersection Control

교차로 접근 Agent 간 우선순위와 WAITING 상태를 관리한다.

### FR-V4-004 Deadlock Observability

완전한 최적 Deadlock Solver가 아니어도, 일정 시간 이상 진행하지 못하는 Agent/Resource를 탐지하고 Event로 남긴다.

### FR-V4-005 Scale

기본 Demo는 10대 이상의 MobileAgent를 시각적으로 처리할 수 있어야 한다.

---

## 7. V5 - Task & Material Flow

### FR-V5-001 Task Model

Task는 최소 다음을 가진다.

- task_id
- source
- destination
- assigned_agent
- state
- created_at / simulation_time

### FR-V5-002 Task States

- QUEUED
- ASSIGNED
- MOVING_TO_SOURCE
- PICKING
- MOVING_TO_DESTINATION
- DROPPING
- COMPLETED
- FAILED

### FR-V5-003 Station Flow

Station 간 Load 이동을 시각적으로 추적할 수 있어야 한다.

---

## 8. V6 - Fleet Management

### FR-V6-001 Fleet Registry

모든 MobileAgent의 위치, 상태, 현재 Task, 대기 시간, 가용 여부를 중앙에서 관리한다.

### FR-V6-002 Task Assignment

가용 Agent에 Task를 자동 배정한다.

V6에서는 단순 거리/대기시간 기반 Heuristic을 허용한다.

### FR-V6-003 Replanning

경로 사용 불가 또는 장기 대기 시 Route 재계산을 지원한다.

### FR-V6-004 Metrics

최소 다음 지표를 계산한다.

- active agents
- waiting agents
- completed tasks
- average task time
- traffic wait count

---

## 9. V7 - Video-like Digital Twin UI

### FR-V7-001 Integrated Dashboard

영상형 Layout과 Fleet/Traffic/Task 상태를 하나의 실행 화면에서 확인한다.

### FR-V7-002 Controls

- Start
- Pause
- Reset
- Simulation speed
- Agent/Station selection

### FR-V7-003 Inspection

선택한 Agent의 현재 Route, Task, State를 표시한다.

### FR-V7-004 Deterministic Demo

고정 Seed 또는 Scenario로 동일한 Demo를 반복 재생할 수 있어야 한다.

---

## 10. V8 - ROS2 Architecture Integration

### FR-V8-001 ROS2 Boundary

Core Domain Logic을 가능한 한 ROS2 비종속으로 유지하고 ROS2 Adapter/Node 계층을 추가한다.

### FR-V8-002 Nodes

최소 다음 역할을 ROS2 Node 또는 명확한 Component로 분리한다.

- Fleet Manager
- Task Manager
- Traffic Manager
- Robot State Adapter
- Digital Twin Adapter

### FR-V8-003 Namespaces

Robot별 Namespace 구조를 지원한다.

```text
/robot_01
/robot_02
...
```

---

## 11. V9 - Gazebo Multi-Robot Warehouse

### FR-V9-001 Warehouse World

2D Reference Layout과 개념적으로 대응되는 Gazebo Warehouse World를 구성한다.

### FR-V9-002 Multi Robot

최소 3대, 목표 5대 이상의 Differential Drive AMR을 동시에 Spawn한다.

### FR-V9-003 Sensors

각 Robot은 최소 다음 ROS2 데이터를 제공한다.

- `/odom`
- `/tf`
- `/scan`
- `/cmd_vel`

### FR-V9-004 Isolation

각 Robot Topic/TF 충돌을 Namespace와 Frame Prefix로 방지한다.

---

## 12. V10 - Nav2 Autonomous Navigation

### FR-V10-001 Navigation

Fleet에서 할당한 Goal을 Nav2 `NavigateToPose` 계열 Action으로 Robot에 전달한다.

### FR-V10-002 Map

Gazebo Warehouse를 위한 Map/Localization 환경을 구성한다.

### FR-V10-003 Recovery

Navigation 실패/취소 결과를 Fleet 상태로 환류한다.

---

## 13. V11 - ROS2 ↔ Digital Twin Synchronization

### FR-V11-001 Source of Position

2D Dashboard의 Robot 위치 Source를 내부 Animation에서 실제 ROS2 `/odom` 또는 TF로 전환한다.

### FR-V11-002 State Synchronization

Navigation, Task, Traffic 상태를 Dashboard에 실시간 표시한다.

### FR-V11-003 Coordinate Transform

Gazebo World 좌표와 2D Dashboard 좌표 사이의 명시적 변환 계층을 둔다.

---

## 14. V12 - Final Integration

### FR-V12-001 End-to-End Scenario

Task 생성 → Fleet 배정 → Traffic Coordination → Nav2 Goal → Gazebo 이동 → ROS2 State → 2D Digital Twin 반영의 전체 흐름이 동작한다.

### FR-V12-002 Multi-AMR

여러 Robot의 동시 작업을 Demonstration할 수 있어야 한다.

### FR-V12-003 Verification

최종 시나리오는 자동화 Test와 Human Visual Verification을 모두 가진다.

---

## 15. Non-Functional Requirements

- Python 3
- V2~V7: Windows 또는 WSL에서 실행 가능
- V8~V12: Ubuntu 22.04 / ROS2 Humble / Gazebo Fortress 기준
- Core Logic과 UI/ROS2 Adapter 분리
- 초보자가 코드 흐름을 추적할 수 있는 모듈 구조
- 결정론적 Test Scenario 제공
- 모든 주요 Traffic/Task 상태 전이는 Log/Event로 추적 가능
- 영상에 없는 기능/의미를 Reference 사실처럼 문서화하지 않는다
