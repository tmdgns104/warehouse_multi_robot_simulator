# Warehouse Multi-Robot Simulator

Reference 영상의 2D 자동화/물류 시뮬레이션 화면과 동작을 단계적으로 재현한 뒤, **ROS2 Humble + Gazebo Fortress + Nav2 기반 Multi-AMR Warehouse Digital Twin**으로 발전시키는 학습/포트폴리오 프로젝트입니다.

## 현재 상태

현재 V1은 완료된 **Core Algorithm Prototype**입니다.

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

현재 다음 작업은:

```text
TASK-006 / V2 Video Layout Reconstruction
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
| V2 | Video Layout Reconstruction ← 현재 |
| V3 | Lane Graph + Continuous Motion |
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

## V1 실행

기존 Prototype은 계속 실행할 수 있습니다.

### Linux / WSL

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Headless core simulation:

```bash
python app.py --headless-ticks 100
```

테스트:

```bash
python -m pytest -q
```

## 기존 V1 구조

```text
src/warehouse_sim/
├── map.py
├── robot.py
├── planner.py
├── collision.py
├── task_manager.py
├── simulation.py
└── ui.py
```

이 구조는 V2 이후 단계적으로 `Facility / Lane Graph / Traffic / Fleet / Snapshot / Renderer` 구조로 발전합니다.

기존 코드를 무조건 삭제하고 새로 만드는 것이 아니라, V1의 검증된 알고리즘과 테스트를 보존하면서 단계적으로 Refactor합니다.

## Codex로 다음 작업 시작

현재 Repository를 VS Code/Codex에서 열고 `CODEX_START_PROMPT.md` 내용을 사용하면 됩니다.

현재 Prompt는 **TASK-006 / V2만 수행**하도록 제한되어 있습니다.

V2가 검증되기 전에 ROS2/Gazebo/Nav2를 한꺼번에 구현하지 않습니다.

## 최종 프로젝트 정의

V12 완료 후 목표 이름:

**ROS2-based Multi-AMR Warehouse Digital Twin & Fleet Management System**
