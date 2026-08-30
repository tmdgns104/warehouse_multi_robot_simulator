# Status

Project: Warehouse Multi-Robot Simulator

Current Version: V2
Current Phase: Video Reproduction Specification Ready
Current Task: TASK-006 - V2 Video Layout Reconstruction

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

## Next Gate

TASK-006에서 다음을 수행한다.

1. 기존 V1 Repository/Tests 재확인
2. Reference 영상이 로컬에 있으면 프레임 분석
3. Facility/Layout Model 설계
4. 영상형 2D Layout/Renderer 구현
5. Regression Test
6. 실행 화면 Human Visual Verification
7. STATUS.md 갱신

V2 완료 전 V3 이상의 기능을 대규모로 선행 구현하지 않는다.
