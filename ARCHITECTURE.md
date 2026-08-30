# Architecture

## 1. V1 Architecture

```text
┌────────────────────────────────────────────┐
│                 UI Layer                   │
│                                            │
│ Warehouse / Robot / Path Visualization     │
│ Start / Pause / Reset                      │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────┐
│             Simulation Engine              │
│                                            │
│ Tick                                       │
│ Robot State Update                         │
│ Reservation / Collision Check              │
└───────────────┬────────────────────────────┘
                │
       ┌────────┴────────┐
       ▼                 ▼
┌─────────────┐   ┌───────────────┐
│   Robot     │   │ Task Manager  │
│             │   │               │
│ position    │   │ goal assign   │
│ goal        │   └───────────────┘
│ path        │
│ state       │
└──────┬──────┘
       │
       ▼
┌────────────────────────┐
│      Path Planner      │
│                        │
│          A*            │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│     Warehouse Map      │
│                        │
│ grid / wall / shelf    │
└────────────────────────┘
```

## 2. Suggested Source Layout

```text
warehouse_multi_robot_simulator/
├── README.md
├── PROJECT.md
├── REQUIREMENTS.md
├── ARCHITECTURE.md
├── DECISIONS.md
├── STATUS.md
├── requirements.txt
├── app.py
├── src/
│   └── warehouse_sim/
│       ├── __init__.py
│       ├── map.py
│       ├── robot.py
│       ├── planner.py
│       ├── collision.py
│       ├── task_manager.py
│       ├── simulation.py
│       └── ui.py
├── tests/
│   ├── test_planner.py
│   ├── test_collision.py
│   └── test_simulation.py
└── tasks/
```

## 3. Core Data Flow

```text
Task
 ↓
Robot Goal
 ↓
A* Planner
 ↓
Planned Path
 ↓
Simulation Tick
 ↓
Collision Check
 ↓
Move / Wait
 ↓
UI Update
```

## 4. V1 Collision Policy

모든 Robot의 next cell을 먼저 계산한다.

그 다음 move를 commit한다.

즉 다음과 같은 방식이다.

```text
Robot 1 wants A
Robot 2 wants A

        ↓

Conflict

        ↓

Priority rule

        ↓

Robot 1 MOVE
Robot 2 WAIT
```

Priority V1:

1. ARRIVED / IDLE 제외
2. Waiting time이 긴 Robot 우선
3. 동률이면 낮은 Robot ID 우선

V1의 목적은 완전 최적화가 아니라
다중 로봇 충돌 문제의 원리를 이해하는 것이다.

## 5. Future ROS2 Mapping

V1의 개념은 향후 다음 ROS2 구조로 대응한다.

```text
Robot class
→ /robotN state

Task Manager
→ Fleet Manager Node

A* Planner
→ Nav2 Planner

Simulation Map
→ Occupancy Grid / map_server

Robot movement
→ /cmd_vel

Robot position
→ /odom

Collision / Reservation
→ Fleet Coordination
```
