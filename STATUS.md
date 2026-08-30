# Status

Project: Warehouse Multi-Robot Simulator

Current Version: V2
Current Phase: V2 Implemented / Human Visual Verification Required
Current Task: TASK-006 - V2 Video Layout Reconstruction Complete

## Final Goal

Reference 영상의 2D 자동화 시스템을 단계적으로 재현한 뒤 ROS2 Humble + Gazebo Fortress + Nav2 기반 Multi-AMR Warehouse Digital Twin으로 발전시킨다.

## V1 Baseline - Completed

V1은 최종 제품이 아니라 Core Algorithm Prototype으로 유지한다.

Completed:

- 22x16 warehouse grid
- Four robots
- Manhattan A*
- Robot state
- Simultaneous tick proposals/commits
- Same-cell conflict prevention
- Head-on swap prevention
- Pygame visualization
- Start/Pause/Reset
- Click-to-change-goal
- Headless smoke run
- 13 core tests reported passing at V1 completion

V1 GUI는 기존 STATUS 기록상 pygame이 없는 실행 환경 때문에 최종 Human Visual Verification이 남아 있었다.

## Direction Change Approved

V1의 단순 Grid 화면을 Reference 영상 재현의 최종 결과로 취급하지 않는다.

승인된 방향:

```text
V2  Video Layout Reconstruction
V3  Lane Graph + Continuous Motion
V4  Multi-Agent Traffic Control
V5  Task & Material Flow
V6  Fleet Management
V7  Video-like Digital Twin UI
V8  ROS2 Architecture Integration
V9  Gazebo Multi-Robot Warehouse
V10 Nav2 Autonomous Navigation
V11 ROS2 ↔ Digital Twin Synchronization
V12 Multi-AMR Warehouse Digital Twin
```

## Reference

- `VIDEO_ANALYSIS.md`: 현재 대화에서 제공된 Reference 영상 분석 기준
- 로컬 권장 경로: `reference/warehouse_reference.mp4`
- `reference/README.md`: Reference Asset 관리 규칙

영상에서 확인되지 않는 객체의 정확한 의미는 임의로 확정하지 않는다.

## TASK-006 Result

- Reference 영상 8개 시점의 프레임을 OpenCV로 실제 확인
- 1280x720 영상 좌표계 기반 `FacilityLayout` Domain Model 구현
- Zone, MachineBlock, Station, NetworkSegment, MobileEntity 분리
- 상단 8개 블록, 중앙 6x3 반복 설비, 좌우 Marker, 하단 Network 재구성
- backend-neutral Render Plan 구현
- 같은 Render Plan을 사용하는 pygame UI와 Pillow Evidence Renderer 구현
- V2를 기본 화면으로 전환하고 기존 V1은 `--v1` 옵션으로 보존
- Layout/Render Plan 신규 Test 4건 추가
- V1 Regression을 포함한 전체 17 tests passing
- PNG Evidence: `evidence/v2_reference_layout.png`

## Verification

- Python compile/import: PASS
- V1 core regression tests: PASS
- V2 layout tests: PASS
- Pillow reference rendering: PASS (1280x720 PNG 직접 확인)
- pygame GUI window: NOT VERIFIED in the Codex environment because pygame is unavailable
- Human visual comparison against the video: REQUIRED

TASK-007 이상은 시작하지 않았다.
