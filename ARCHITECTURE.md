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

#### V3 Implemented Boundary

```text
V2 NetworkSegment[]
        ↓ intersection splitting
LaneGraph (LaneNode + LaneEdge)
        ↓ Graph A*
node-id route
        ↓ MotionEngine.update(delta_time)
edge progress / interpolated position
        ↓
ReferenceLayoutUI
```

Reference Scenario의 graph edge가 Renderer의 Network 선 source도 담당하므로 표시된 lane과 실제 이동 좌표가 일치한다. MotionEngine은 pygame을 import하지 않으며, 초 단위 `delta_time`과 pixels/second 속도를 사용한다. V3에는 reservation/traffic permission을 넣지 않는다.

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

#### V4 Implemented Boundary

```text
TrafficMotionEngine
  ├─ seeded goal reassignment / Graph A*
  ├─ update(delta_time)
  └─ priority-ordered entry requests
              ↓
TrafficController
  ├─ node_reservations[node_id] = entity_id
  ├─ edge_reservations[edge_id] = entity_id
  ├─ GRANT / WAIT
  └─ blocked warning events
              ↓
LaneGraph
```

Entity가 Edge에 들어가기 전에 Edge와 target Node를 함께 예약하고 현재 Node를 해제한다. Edge 완료 시 Edge만 해제하고 target Node 점유는 유지한다. 기본 V4는 안전을 위해 같은 Edge의 같은 방향 follow도 직렬화한다. 완전한 deadlock solver 대신 장기 대기 경고와 빈 인접 Node를 이용한 제한적 demo recovery만 제공한다.

#### Predictive V4 Upgrade

```text
Route horizon (4 edges)
  ├─ expiring soft reservations
  ├─ congestion + zone cost
  └─ predicted next-conflict ETA
          ↓
traffic-aware A* / cooldown reroute / target speed
          ↓
hard Node+Edge reservation at actual entry
```

Soft reservation은 미래 의도를 표현하고 route/speed 비용에만 영향을 준다. 실제 안전성은 hard reservation이 보장한다. Wait-for cycle이 예상되면 alternate route를 탐색한다. Reroute는 3초 cooldown과 10% 비용 개선 조건으로 oscillation을 제한한다.

#### V4.1 Obstacle-safe Lane Topology

```text
FacilityLayout
  ├─ MachineBlock -> expanded RectangleObstacle (7 px)
  └─ NetworkSegment (drivable / visual-only)
              ↓ obstacle-aware aisle repair + safe 2 px snap
         Safe LaneGraph
              ├─ geometry validation
              ├─ TrafficMotionEngine
              └─ network_segments() -> Renderer
```

7px clearance는 V4 최대 Entity 폭 11px의 반폭 5.5px와 1.5px 수치/렌더링 여유의 합이다. Machine을 관통하던 세 vertical은 확장 경계와 다음 안전 vertical 사이의 aisle 중심을 데이터에서 계산한다. 상단 cap은 관찰된 MobileEntity 주행 근거가 없어 `drivable=False`인 회청색 시각 구조로 유지한다. Reference 여러 시점의 하단 이동 객체와 정렬되는 중앙 `vertical_5`~`vertical_8`만 기존 centerline 그대로 bottom return에 연결한다. 나머지 15px stub은 주행 근거가 없어 연결하지 않는다. Machine 내부 장식선은 짙은 청색 equipment primitive이며 Station/Marker의 통행 불가 의미도 확인되지 않아 obstacle로 승격하지 않는다.

#### V4.2 Canonical Lane Rendering

```text
Safe LaneGraph edges + canonical LaneNode coordinates
                         ↓
                 network_segments()
                         ↓
            reference_render_segments()
              ├─ exact driving edges
              └─ explicit visual-only detail
                         ↓
                  pygame / Pillow
```

Renderer는 raw drivable `FacilityLayout.network`를 다시 그리지 않는다. 모든 driving line endpoint는 LaneNode 좌표에서 생성되므로 planner, motion, graph, renderer가 동일한 snap-normalized 좌표를 사용한다. Reference에서 bottom return 연결 근거가 없는 vertical은 y=618 driving junction에서 끝나고 y=618~633 tail만 회청색 visual-only로 보존한다. 따라서 bottom return과의 15px 간격은 끊어진 driving rail이 아니라 의도적으로 분리된 reference detail이다.

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
