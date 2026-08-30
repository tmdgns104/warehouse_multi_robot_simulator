# Requirements

## Functional Requirements

### FR-001 Warehouse Map

2D Grid 기반 창고 Map을 제공한다.

Map은 최소 다음 요소를 구분한다.

- FREE
- WALL
- SHELF
- START / STATION
- ROBOT

### FR-002 Robot

최소 3대의 Robot을 지원한다.

각 Robot은 최소 다음 상태를 가진다.

- id
- position
- goal
- path
- state

Robot state:

- IDLE
- PLANNING
- MOVING
- WAITING
- ARRIVED

### FR-003 Path Planning

A* Algorithm을 사용하여 현재 위치에서 Goal까지 경로를 계산한다.

Shelf / Wall은 통과할 수 없다.

경로를 화면에 시각화한다.

### FR-004 Multi-Robot Movement

여러 Robot이 한 Simulation Tick 안에서 이동한다.

Robot은 한 Tick에 최대 한 Grid Cell 이동한다.

### FR-005 Collision Avoidance

최소 다음 충돌을 방지한다.

1. 같은 셀 동시 진입
2. 서로 위치를 교환하는 head-on swap

충돌 가능성이 있으면 한 Robot은 WAITING 한다.

V1에서는 완전한 MAPF 최적화 알고리즘까지 요구하지 않는다.

### FR-006 Task

각 Robot에 Goal을 지정할 수 있어야 한다.

초기 버전에서는 사전 정의된 Task를 자동 할당해도 된다.

### FR-007 Visualization

화면에 최소 다음을 표시한다.

- Warehouse
- Shelves
- Robot
- Goal
- Planned Path
- Robot status
- Tick / simulation state

### FR-008 Controls

최소 다음을 제공한다.

- Start / Pause
- Reset

가능하면:
- Robot 선택
- Goal 클릭 지정

### FR-009 Logging

중요 Event를 Console 또는 UI에 표시한다.

예:

- Robot 1 path planned
- Robot 2 waiting
- Robot 3 arrived

### FR-010 Tests

A*와 Collision Logic은 GUI와 분리하여 Unit Test 가능하게 한다.

## Non-Functional Requirements

- Python 3
- Windows 또는 WSL에서 실행 가능
- 초보자가 읽을 수 있는 코드 구조
- 핵심 로직과 GUI 분리
- 과도한 Framework 금지
- V1에서는 ROS2 의존성 금지
- V1에서는 Database / Cloud 불필요
