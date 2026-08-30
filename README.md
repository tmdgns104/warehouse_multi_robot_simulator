# Warehouse Multi-Robot Simulator

Reference 영상의 2D 자동화/물류 시뮬레이션 화면과 동작을 단계적으로 재현한 뒤, **ROS2 Humble + Gazebo Fortress + Nav2 기반 Multi-AMR Warehouse Digital Twin**으로 발전시키는 학습/포트폴리오 프로젝트입니다.

## 현재 상태

V2와 V3는 Human Verification까지 완료되었습니다. V4는 predictive reservation, congestion-aware routing, dynamic rerouting과 speed coordination까지 자동 검증됐으며 Human Traffic Verification을 기다리고 있습니다.

V1에서 구현된 것:

- Grid Map
- Manhattan A*
- 4대 Robot
- Robot State
- 동시 Simulation Tick
- Same-cell / head-on swap 충돌 방지
- Pygame UI
- Start / Pause / Reset
- Unit Tests

하지만 이 화면은 Reference 영상의 최종 재현본이 아닙니다.

현재 구현 결과:

```text
TASK-009 / V5 Task-driven Factory Material Flow 구현 / Human 확인 필요
```

입니다.

## 최종 목표

```text
Reference Video
      ↓
Video-like 2D Simulator
      ↓
Lane Graph / Continuous Motion
      ↓
Traffic Manager
      ↓
Task / Material Flow
      ↓
Fleet Manager
      ↓
2D Digital Twin Dashboard
      ↓
ROS2
      ↓
Gazebo Multi-Robot
      ↓
Nav2
      ↓
ROS2 ↔ 2D Digital Twin Synchronization
```

최종 단계에서는 2D 화면의 Robot 위치를 내부 Animation으로 임의 이동시키지 않습니다.

```text
Gazebo Robot
   ↓ /odom /tf /navigation state
ROS2
   ↓
Digital Twin Bridge
   ↓
2D Dashboard
```

즉 2D 관제 화면과 Gazebo의 실제 Robot이 같은 상태를 표현하게 됩니다.

## Roadmap

| Version | 목표 |
|---|---|
| V1 | Core Algorithm Prototype ✅ |
| V2 | Video Layout Reconstruction ✅ |
| V3 | Lane Graph + Continuous Motion ✅ |
| V4 | Multi-Agent Traffic Control ✅ (화면 확인 필요) |
| V5 | Task & Material Flow |
| V6 | Fleet Management |
| V7 | Video-like Digital Twin UI |
| V8 | ROS2 Architecture Integration |
| V9 | Gazebo Multi-Robot Warehouse |
| V10 | Nav2 Autonomous Navigation |
| V11 | ROS2 ↔ Digital Twin Synchronization |
| V12 | Multi-AMR Warehouse Digital Twin |

세부 내용은 다음 문서를 참고합니다.

- `PROJECT.md`
- `REQUIREMENTS.md`
- `ARCHITECTURE.md`
- `DECISIONS.md`
- `VIDEO_ANALYSIS.md`
- `STATUS.md`
- `tasks/`

## Reference 영상 원칙

로컬 Reference 권장 경로:

```text
reference/warehouse_reference.mp4
```

영상에서 직접 확인되는 **화면/배치/움직임**은 재현 대상으로 사용합니다.

반면 영상만으로 정확한 의미를 알 수 없는 객체는 임의로 사실처럼 단정하지 않습니다.

예를 들어 초록색 객체가 실제 AGV인지 확인되지 않았다면 코드에서는 우선 `MobileAgent` 같은 중립 이름을 사용합니다.

자세한 기준은 `VIDEO_ANALYSIS.md`에 기록되어 있습니다.

## V4 실행

기본 실행은 16개 Entity가 미래 4개 Edge를 확인하고 혼잡 비용 기반 route 및 속도 조정을 사용하며 계속 이동하는 V4 Demo를 표시합니다. 도착하면 traffic-aware 새 LaneNode goal이 자동 할당됩니다.

### Linux / WSL

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

V4 화면 키:

- `Space`: 이동 Pause/Start
- `R`: scenario Reset
- `N`: LaneNode 표시 전환
- `P`: 계획 route 표시 전환
- `T`: Edge reservation 표시 전환
- `I`: Entity ID 표시 전환
- `D`: LaneNode, Machine bounds, 7px clearance debug overlay 전환
- `Q` 또는 `Esc`: 종료

기본 실행은 V5 Factory Task Flow입니다. 16대 Robot 중 최대 10대가 deterministic Task를 수행하고 나머지는 IDLE pool로 유지됩니다.

```bash
python app.py
```

V5 headless Factory acceptance와 Evidence:

```bash
python app.py --headless-factory 300 --entities 16 --seed 1234
python app.py --render-factory evidence/v5_factory_task_flow.png --motion-time 60 --entities 16
python app.py --render-factory-debug evidence/v5_factory_task_debug.png --motion-time 60 --entities 16
```

기존 V4 random traffic demo는 `python app.py --traffic-demo`로 보존됩니다.

GUI 없이 5초간 motion을 실행하고 위치를 출력:

```bash
python app.py --headless-motion 5
```

V4 장시간 traffic 검증:

```bash
python app.py --headless-traffic 120 --entities 16 --seed 1234
```

300초 Acceptance/Scalability 검증:

```bash
python app.py --headless-traffic 300 --entities 16 --seed 1234
python app.py --headless-traffic 300 --entities 24 --seed 1234
```

Entity 수 변경과 one-shot 실행:

```bash
python app.py --entities 24
python app.py --entities 16 --one-shot
```

V4 Evidence 생성:

```bash
python app.py --render-traffic evidence/v4_traffic.png --motion-time 30 --entities 16
```

V4.1 안전 topology Evidence 생성:

```bash
python app.py --render-traffic evidence/v4_1_safe_lane_topology.png --motion-time 30 --entities 16
python app.py --render-topology-debug evidence/v4_1_topology_debug.png
```

V4.2 Lane continuity Evidence 생성:

```bash
python app.py --render-traffic evidence/v4_2_lane_continuity.png --motion-time 30 --entities 16
python app.py --render-topology-debug evidence/v4_2_lane_debug.png
```

V4.2에서는 `SafeLaneGraph.network_segments()`가 화면의 유일한 driving rail source입니다. Upper Cap과 Reference의 비주행 하단 tail은 회청색 visual-only 구조이며, Machine 내부 detail은 짙은 청색입니다.

V4.3 obstacle-safe Manhattan grid Evidence 생성:

```bash
python app.py --render-traffic evidence/v4_3_grid_lane_topology.png --motion-time 30 --entities 16
python app.py --render-topology-debug evidence/v4_3_grid_lane_debug.png
```

V4.3 기본 주행망은 영상에서 측정한 aisle X/Y 좌표로 candidate grid를 만든 뒤 Machine과 Station의 7px 확장 영역을 통과하는 부분만 분할 제거합니다. 상단·좌우 outer rail·중앙 cross aisle·하단 return이 하나의 Manhattan driving component이며, y=66 Upper Cap enclosure만 회청색 visual-only로 유지합니다.

V4.1/V4.2는 obstacle-safe graph와 canonical renderer를 도입한 이력으로 유지됩니다. 현재 기본 화면은 위 V4.3 candidate-grid 결과를 사용합니다.

V3 Motion Evidence 생성:

```bash
python app.py --render-motion evidence/v3_lane_motion.png --motion-time 5
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

V2 정적 Evidence PNG 생성:

```bash
python app.py --render-reference evidence/v2_reference_layout.png
```

기존 V1 Grid Simulator 실행:

```bash
python app.py --v1
```

Headless core simulation:

```bash
python app.py --headless-ticks 100
```

테스트:

```bash
python -m pytest -q
```

## V4 Traffic 구조

```text
src/warehouse_sim/
├── facility_layout.py       # Zone/Machine/Station/Network/Entity 모델
├── reference_scenario.py    # 영상 측정 기반 Reference Scenario
├── render_plan.py           # backend-neutral drawing primitives
├── reference_renderer.py    # pygame 화면 + Pillow Evidence 출력
├── lane_graph.py            # LaneNode/LaneEdge와 V2 선→Graph 변환
├── graph_planner.py          # Lane Graph A*
├── motion.py                 # Entity progress와 update(delta_time)
├── reference_motion_scenario.py # 5개 Entity V3 demo
├── traffic.py               # 중앙 Node/Edge reservation controller
├── traffic_simulation.py    # priority, WAITING, 지속 운행과 metrics
├── traffic_planner.py       # congestion/zone/prediction 비용 기반 A*
├── reference_traffic_scenario.py # seed 기반 기본 16 Entity demo
├── map.py
├── robot.py
├── planner.py
├── collision.py
├── task_manager.py
├── simulation.py
└── ui.py
```

TrafficController는 실제 진입 안전용 hard reservation과 4-edge horizon의 만료되는 predictive reservation을 분리합니다. Traffic A*는 거리, hard/soft reservation, 예상 혼잡과 zone capacity를 비용으로 사용합니다. 재계획은 cooldown과 개선 임계치를 적용하며 미래 병목이 보이면 정지 전에 속도를 부드럽게 낮춥니다. 완전한 MAPF solver는 포함하지 않습니다.

기존 코드를 무조건 삭제하고 새로 만드는 것이 아니라, V1의 검증된 알고리즘과 테스트를 보존하면서 단계적으로 Refactor합니다.

## Visual Evidence

Predictive V4 화면은 `evidence/v4_predictive_traffic.png`, 16/24 Entity 수치는 `evidence/v4_predictive_stress.txt`에 있습니다. 장시간 안전성과 흐름은 `--headless-traffic`, `tests/test_traffic.py`, `tests/test_predictive_traffic.py`로 검증합니다.

## 최종 프로젝트 정의

V12 완료 후 목표 이름:

**ROS2-based Multi-AMR Warehouse Digital Twin & Fleet Management System**
