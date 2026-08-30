# TASK-006 - V2 Video Layout Reconstruction

Status: IMPLEMENTED / HUMAN VISUAL VERIFICATION REQUIRED

## Goal

현재 V1 Grid UI를 최종 화면으로 취급하지 않고, Reference 영상과 유사한 2D 자동화 시설 Layout/스타일을 재구성한다.

## Read First

- PROJECT.md
- REQUIREMENTS.md
- ARCHITECTURE.md
- DECISIONS.md
- VIDEO_ANALYSIS.md
- STATUS.md

로컬에 존재하면 `reference/warehouse_reference.mp4`도 프레임 단위로 확인한다.

## Deliverables

- Facility/Zone/Machine/Station용 Layout Model
- 영상의 상단/중앙/좌우/하단 영역을 반영한 Reference Scenario
- 밝은 배경, 반복 설비, 얇은 이동 Network 기반 Renderer
- 작은 중립 Entity 표현
- 기존 V1 Core Regression 유지
- 화면 구조 설명 문서/README 갱신

## Constraints

- 아직 ROS2/Gazebo/Nav2 추가 금지
- 아직 Lane Graph Routing 완전 구현 금지; V3 범위
- 영상에서 확인되지 않는 객체 의미를 임의 확정 금지
- UI 코드에 모든 Layout 좌표를 무질서하게 직접 하드코딩하지 않음

## Verification

- Unit tests PASS
- 앱 실행 가능
- Reference Scenario가 한 화면에 표시
- V1보다 영상과 유사한 공간 구성/객체 크기/색감
- Human Visual Verification 필요

## Completion Gate

STATUS.md에 V2 구현 결과와 Human Visual Verification 필요 여부를 기록한 뒤 완료한다.
