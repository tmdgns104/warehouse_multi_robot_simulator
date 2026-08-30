# Warehouse Multi-Robot Simulator V1

물류창고 다중 이동 로봇의 핵심 원리를 눈으로 익히기 위한 Python 2D 학습 프로젝트입니다. ROS2, Gazebo, Nav2 없이 Grid Map, A* 경로 계획, 동시 이동과 충돌 회피를 작은 코드베이스에서 분리해 살펴볼 수 있습니다.

## 화면에서 볼 수 있는 것

- 벽, 선반, 통로, 작업 스테이션으로 구성된 22×16 창고
- 서로 다른 색과 ID를 가진 Robot 4대
- Robot별 현재 위치, 목표, 남은 계획 경로, 상태, 대기 횟수
- 동일 셀 진입 및 서로 위치 교환 충돌을 피하는 tick 기반 동시 이동
- Start, Pause, Reset 버튼과 현재 simulation tick
- 최근 path planning, waiting, arrival 이벤트
- Robot 클릭 후 이동 가능한 셀을 클릭하는 목표 변경 기능

## 실행 조건

- Python 3.9 이상 권장
- Windows, Linux 또는 WSL
- GUI 실행에는 `pygame` 필요
- 테스트에는 `pytest` 필요

## 설치

프로젝트 루트에서 가상환경을 만들고 dependency를 설치합니다.

Linux / WSL:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Ubuntu에서 가상환경 생성 자체가 실패하면 먼저 `sudo apt install python3-venv`로 배포판 패키지를 설치해야 할 수 있습니다.

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 실행

```bash
python app.py
```

- `Start`: robot 이동 시작
- `Pause`: 현재 위치에서 일시정지
- `Reset`: 최초 위치, 목표, 경로와 tick 복원
- `Space`: Start/Pause 단축키
- 목표 변경: robot을 클릭한 뒤 원하는 빈 통로 셀 클릭

GUI 없이 core simulation의 도착 여부만 빠르게 확인할 수도 있습니다. 지정한 tick 전에 모두 도착하면 exit code 0을 반환합니다.

```bash
python app.py --headless-ticks 100
```

## 테스트

```bash
python -m pytest -q
```

테스트는 pygame 창을 열지 않으며 A*, 장애물 처리, no-path, same-cell conflict, head-on swap, 한 칸 이동, 도착과 reset을 검증합니다.

## 핵심 원리

### A* 경로 계획

A*는 출발점에서 지금까지 든 비용과 목표까지 남았다고 추정하는 비용을 합쳐, 다음에 탐색할 cell을 고르는 알고리즘입니다. 이 프로젝트는 상하좌우로만 이동하고 추정값으로 Manhattan Distance(`|x1-x2| + |y1-y2|`)를 사용합니다. WALL과 SHELF는 후보에서 제외하며 도달할 수 없으면 예외 대신 `None`을 반환합니다.

### Robot State

- `IDLE`: 할당된 작업이 없거나 유효한 경로가 없음
- `PLANNING`: 새 목표의 경로를 계산할 예정
- `MOVING`: 경로의 다음 cell로 이동 가능
- `WAITING`: 이번 tick에 충돌을 피하려고 정지
- `ARRIVED`: 현재 위치가 목표와 같음

### Collision Avoidance

각 tick은 모든 robot의 다음 위치를 먼저 제안하고, 충돌 검사를 마친 뒤 허용된 이동만 한꺼번에 반영합니다. 두 robot이 같은 cell을 원하면 `waiting_count`가 큰 robot, 동률이면 ID가 낮은 robot이 우선입니다. 서로의 현재 cell로 맞바꾸려는 head-on swap은 둘 다 정지합니다. 정지한 robot의 cell로 뒤따라 들어가는 연쇄 충돌도 함께 차단합니다.

이 정책은 학습을 위한 단순 reservation 방식입니다. 전체 이동 거리를 최적화하는 CBS나 MAPF는 V1 범위가 아닙니다.

## 폴더 구조와 파일 역할

```text
.
├── app.py                         # GUI/headless 실행 진입점
├── requirements.txt              # pygame, pytest dependency
├── src/warehouse_sim/
│   ├── map.py                     # grid, cell 종류, 기본 창고
│   ├── robot.py                   # Robot와 RobotState
│   ├── planner.py                 # Manhattan A*
│   ├── collision.py               # 한 tick의 이동 예약/충돌 판정
│   ├── task_manager.py            # goal 유효성 검사와 할당
│   ├── simulation.py              # planning, tick, commit, reset
│   └── ui.py                      # pygame 렌더링과 입력 처리
├── tests/
│   ├── test_planner.py
│   ├── test_collision.py
│   └── test_simulation.py
└── tasks/                         # V1 task 명세
```

Core Logic(`map`, `planner`, `collision`, `simulation`)은 pygame을 import하지 않습니다. 따라서 GUI가 없는 CI나 서버에서도 테스트할 수 있습니다.

## 향후 ROS2 / Gazebo 확장

현재 `Robot`은 ROS2의 robot별 state/odometry, `TaskManager`는 Fleet Manager node, `WarehouseMap`은 occupancy grid/map server, A*는 Nav2 planner, tick 이동은 Gazebo의 물리 이동 및 `/cmd_vel`과 대응시킬 수 있습니다. 다음 단계에서는 시간 기반 예약과 재계획을 학습한 뒤 ROS2 node와 topic으로 경계를 치환하는 방식이 적합합니다.

## V1 제한사항

- 단순 reservation이므로 복잡한 좁은 통로에서 교착 상태를 완전히 해결하지 않습니다.
- robot은 점유 cell 단위로 즉시 이동하며 실제 속도, 회전, 가감속과 센서는 모델링하지 않습니다.
- 작업 queue, 자동 재할당, 저장소와 네트워크 관제는 포함하지 않습니다.
