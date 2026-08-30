# Warehouse Multi-Robot Simulator

Reference 영상의 2D 자동화/물류 시뮬레이션 화면과 동작을 단계적으로 재현한 뒤, **ROS2 Humble + Gazebo Fortress + Nav2 기반 Multi-AMR Warehouse Digital Twin**으로 발전시키는 학습/포트폴리오 프로젝트입니다.

## 현재 상태

현재 V2 Layout Reconstruction은 Human Verification까지 완료되었고, V3 Lane Graph + Continuous Motion이 구현되어 Human Motion Verification을 기다리고 있습니다.

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
TASK-007 / V3 Lane Graph + Continuous Motion 구현 완료
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
| V3 | Lane Graph + Continuous Motion ✅ (움직임 확인 필요) |
| V4 | Multi-Agent Traffic Control |
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

## V3 실행

기본 실행은 V2 Facility 위에서 5개 Entity가 Lane Graph를 따라 연속 이동하는 V3 Demo를 표시합니다.

### Linux / WSL

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

V3 화면 키:

- `Space`: 이동 Pause/Start
- `R`: scenario Reset
- `N`: LaneNode 표시 전환
- `P`: 계획 route 표시 전환
- `Q` 또는 `Esc`: 종료

GUI 없이 5초간 motion을 실행하고 위치를 출력:

```bash
python app.py --headless-motion 5
```

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

## V3 Graph/Motion 구조

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
├── map.py
├── robot.py
├── planner.py
├── collision.py
├── task_manager.py
├── simulation.py
└── ui.py
```

V2 `NetworkSegment`의 교차점이 LaneNode가 되고, 분할된 선 조각이 LaneEdge가 됩니다. 같은 Graph edge를 Renderer가 다시 Network로 그리므로 이동 좌표와 표시 좌표가 일치합니다. Traffic reservation과 충돌 우선순위는 V4 범위이므로 아직 포함하지 않습니다.

기존 코드를 무조건 삭제하고 새로 만드는 것이 아니라, V1의 검증된 알고리즘과 테스트를 보존하면서 단계적으로 Refactor합니다.

## Visual Evidence

V2 화면은 `evidence/v2_reference_layout.png`, V3의 5초 motion snapshot은 `evidence/v3_lane_motion.png`에서 확인할 수 있습니다. 연속성 자체는 `tests/test_motion.py`의 FPS 독립성, 보간, edge transition 테스트와 `--headless-motion`으로 검증합니다.

## 최종 프로젝트 정의

V12 완료 후 목표 이름:

**ROS2-based Multi-AMR Warehouse Digital Twin & Fleet Management System**
