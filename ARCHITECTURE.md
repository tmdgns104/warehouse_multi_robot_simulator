# Architecture

## 1. Architecture Goal

현재 V1 Grid Simulator를 버리지 않고, Core Domain을 확장하여 다음 최종 구조로 발전시킨다.

```text
┌──────────────────────────────────────────────┐
│          2D Digital Twin / Dashboard         │
│ Layout / Agents / Tasks / Traffic / Metrics  │
└──────────────────────┬───────────────────────┘
                       │ Adapter
┌──────────────────────▼───────────────────────┐
│                Domain Core                   │
│ Layout / Lane Graph / Fleet / Task / Traffic │
│ Route Planning / Events / Scenario           │
└──────────────────────┬───────────────────────┘
                       │
             V2~V7     │     V8~V12
                       │ ROS2 Adapter
┌──────────────────────▼───────────────────────┐
│                    ROS2                      │
│ Fleet / Task / Traffic / Robot State Nodes   │
└──────────────────────┬───────────────────────┘
                       │ Nav2 Action / Topics
┌──────────────────────▼───────────────────────┐
│                   Nav2                       │
│ Planner / Controller / Localization          │
└──────────────────────┬───────────────────────┘
                       │ /cmd_vel
┌──────────────────────▼───────────────────────┐
│            Gazebo Multi-Robot World          │
│ AMR / LiDAR / Odom / TF / Collision          │
└──────────────────────┬───────────────────────┘
                       │ /odom /tf /scan
                       └──────────────→ Digital Twin
```

---

## 2. Architectural Principle

### 2.1 Domain Core is not the UI

Simulation/Fleet/Traffic Logic은 Pygame Rendering과 분리한다.

### 2.2 Domain Core is not ROS2

V8 이후에도 Task, Fleet Policy, Traffic Reservation 등의 핵심 로직은 가능한 한 일반 Python Domain으로 유지한다.
ROS2 Node는 Transport/Integration Adapter 역할을 한다.

### 2.3 Reference Layout is Data

영상 재현 Layout을 UI 함수 안에 직접 그려 넣기보다 Data Model로 정의한다.

예:

```text
Layout
├── Machines
├── Stations
├── Zones
├── LaneNodes
└── LaneEdges
```

---

## 3. V1 Baseline

현재 구현:

```text
Grid Map
  ↓
Grid A*
  ↓
Robot Path
  ↓
Simulation Tick
  ↓
Basic Collision
  ↓
Pygame UI
```

V1은 알고리즘 Prototype/Regression Reference로 유지한다.

---

## 4. V2~V7 Video Reproduction Architecture

```text
Scenario / Reference Layout
              │
              ▼
┌────────────────────────────┐
│       Facility Model       │
│ zones / machines / stations│
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│         Lane Graph         │
│ nodes / edges / direction  │
└──────────────┬─────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌─────────────┐   ┌──────────────┐
│Route Planner│   │Traffic Manager│
│Graph A*/Dijk│   │Reservations   │
└──────┬──────┘   └──────┬───────┘
       │                 │
       └────────┬────────┘
                ▼
        ┌──────────────┐
        │ Fleet Manager│
        │ Agent States │
        │ Assignment   │
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ Task Manager │
        │ Queue / Flow │
        └──────┬───────┘
               │ Events / Snapshot
               ▼
┌────────────────────────────┐
│    Digital Twin Renderer   │
│ smooth motion / dashboard  │
└────────────────────────────┘
```

### 4.1 Facility Model

영상에서 보이는 공간적 구성만 모델링한다.

- Zone
- Machine
- Station
- LaneNode
- LaneEdge

정확한 설비 명칭이 불명확하면 중립 이름을 유지한다.

### 4.2 Lane Graph

```python
LaneNode(id, x, y, kind)
LaneEdge(id, source, target, length, bidirectional, capacity)
```

Agent의 Route는 Node ID List 또는 Edge ID List로 표현한다.

### 4.3 Continuous Motion

Agent는 Edge 진입 시 다음 상태를 가진다.

```text
edge_id
progress: 0.0 ~ 1.0
speed
```

화면 위치:

```text
P = start + progress * (end - start)
```

Simulation update와 Rendering frame rate를 분리하여 부드러운 Animation을 허용한다.

### 4.4 Traffic Manager

Traffic Manager는 이동 전에 Resource를 예약한다.

```text
Agent Route
   ↓
Request next Edge / Node
   ↓
Reservation Check
   ├─ GRANTED → MOVE
   └─ DENIED  → WAIT
```

Resource:

- Node
- Edge
- Intersection Group
- Optional Station Dock

### 4.5 Task Manager

Task는 이동 목적을 제공한다.

```text
QUEUED
 ↓
ASSIGNED
 ↓
MOVE_TO_SOURCE
 ↓
PICK
 ↓
MOVE_TO_DESTINATION
 ↓
DROP
 ↓
COMPLETED
```

### 4.6 Fleet Manager

Fleet Manager는 `Agent -> Task -> Route -> Traffic Permission`을 연결한다.

---

## 5. V8 ROS2 Integration Architecture

ROS2는 Domain Core를 대체하지 않고 외부 Robot과 연결하는 Adapter Layer다.

권장 Package 방향:

```text
ros2_ws/src/
├── warehouse_fleet_msgs/
├── warehouse_fleet_manager/
├── warehouse_task_manager/
├── warehouse_traffic_manager/
├── warehouse_robot_adapter/
└── warehouse_digital_twin_bridge/
```

초기에는 Custom Message를 최소화하고 표준 Message/Action을 우선 검토한다.

### 5.1 Namespace

```text
/robot_01/cmd_vel
/robot_01/odom
/robot_01/scan

/robot_02/cmd_vel
/robot_02/odom
/robot_02/scan
```

TF Frame도 Robot별 충돌을 피한다.

---

## 6. V9 Gazebo Architecture

```text
Gazebo Warehouse World
├── Warehouse Geometry
├── Static Machines / Shelves
├── robot_01
├── robot_02
├── robot_03
└── ...
```

각 Robot:

```text
base_link
├── wheels
└── lidar
```

Bridge/Plugin을 통해 ROS2에 최소 다음을 제공한다.

```text
/cmd_vel
/odom
/tf
/scan
```

---

## 7. V10 Nav2 Architecture

Fleet Manager가 직접 Wheel Velocity를 계산하지 않는다.

```text
Task Destination
      ↓
Fleet Manager
      ↓
NavigateToPose Goal
      ↓
Nav2
      ↓
/cmd_vel
      ↓
Gazebo Robot
```

Traffic Manager와 Nav2 Local Planner의 책임을 구분한다.

- Fleet Traffic: Robot 간 상위 수준 자원/구역 조정
- Nav2: 개별 Robot의 실제 경로 추종과 Local Obstacle Avoidance

---

## 8. V11 Digital Twin Synchronization

V7까지는 내부 Simulation State가 화면의 Source of Truth다.

V11부터는 External ROS2 State가 Source가 된다.

```text
Gazebo
  ↓
/odom /tf /navigation state
  ↓
DigitalTwinBridge
  ↓
WorldSnapshot
  ↓
같은 2D Renderer
```

이를 위해 Renderer는 `Simulation` 객체에 직접 종속되지 않고 `WorldSnapshot` Interface를 소비하도록 발전시킨다.

권장 Snapshot:

```text
WorldSnapshot
├── timestamp
├── agents[]
│   ├── id
│   ├── x/y
│   ├── heading
│   ├── state
│   └── task
├── tasks[]
├── reservations[]
└── metrics
```

---

## 9. Testing Strategy

### V2~V7

- Layout parsing/unit tests
- Graph route tests
- Reservation tests
- Task lifecycle tests
- Fleet assignment tests
- deterministic scenario tests
- renderer smoke test

### V8~V12

- ROS2 unit tests
- launch tests
- namespace/topic verification
- Gazebo headless smoke tests
- Nav2 goal/result tests
- Digital Twin synchronization tests
- final visual verification

---

## 10. Source Evolution

기존 `src/warehouse_sim`을 즉시 폐기하지 않는다.

예상 발전 형태:

```text
src/warehouse_sim/
├── domain/
│   ├── facility.py
│   ├── lane_graph.py
│   ├── agent.py
│   ├── task.py
│   └── events.py
├── planning/
│   └── graph_planner.py
├── traffic/
│   └── reservation.py
├── fleet/
│   └── manager.py
├── simulation/
│   └── engine.py
├── scenarios/
│   └── reference_layout.py
└── ui/
    └── pygame_renderer.py
```

실제 Refactor 시 기존 테스트와 기능을 보존하면서 단계적으로 이동한다.
