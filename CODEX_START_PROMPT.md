# Codex Start Prompt

현재 Repository는 `warehouse_multi_robot_simulator`다.

## Source of Truth

먼저 다음을 전부 읽어라.

- PROJECT.md
- REQUIREMENTS.md
- ARCHITECTURE.md
- DECISIONS.md
- AGENTS.md
- STATUS.md
- VIDEO_ANALYSIS.md
- reference/README.md
- tasks/TASK-001.md ~ TASK-006.md

기존 V1 구현과 테스트도 직접 조사한다.

현재 승인된 작업은 **TASK-006 - V2 Video Layout Reconstruction** 하나다.

V1을 최종 완성본으로 취급하지 마라.
V1은 Grid/A*/Basic Collision을 학습하기 위한 Prototype이다.

## Reference Target

로컬에 다음 파일이 존재하면 실제로 분석한다.

```text
reference/warehouse_reference.mp4
```

영상이 존재하면 적절한 수의 대표 Frame을 추출하여 다음을 조사한다.

- 전체 화면 비율
- 상단/중앙/좌우/하단 Zone
- 반복 설비 배치
- Lane/Route Network 형태
- 이동 객체의 크기/색/밀도
- 시간에 따른 객체 이동 패턴

영상에서 확인할 수 없는 객체의 정확한 산업적 의미를 임의로 확정하지 마라.

예:

- 초록 객체 = AGV라고 단정 금지
- 검은 원 = Sensor라고 단정 금지
- 노랑 객체 = Pallet이라고 단정 금지

필요하면 중립 이름을 사용한다.

```text
MobileAgent
Load
Machine
Station
Marker
```

## TASK-006 Goal

현재의 큰 Grid Cell + 큰 원형 Robot 중심 Pygame 화면을 Reference 영상에 더 가까운 산업 자동화 2D Layout으로 발전시킨다.

필수:

- 밝은 배경
- 영상과 유사한 시설 전체 비율
- 반복되는 중앙 설비 블록
- 상단/좌우/하단 작업 영역
- 얇은 Lane/Route Network 표시
- 작은 이동 Entity 표시
- Facility/Layout Data Model과 Renderer 분리
- 기존 V1 Core Logic/Tests Regression 유지

## Important Scope Boundary

이번 Task에서는 V2까지만 구현한다.

다음은 아직 대규모 구현하지 않는다.

- V3 Lane Graph Routing
- V4 Traffic Manager
- V5 Task Flow
- V6 Fleet Manager
- V8 ROS2
- V9 Gazebo
- V10 Nav2

단, V3에서 사용할 수 있도록 Layout/Lane Data Interface를 깔끔하게 설계하는 것은 허용한다.

## Work Policy

현재 승인 범위 안에서는 다음을 자동으로 진행한다.

```text
inspect
→ analyze reference
→ implement
→ test
→ diagnose
→ fix
→ retest
→ document
```

일반적인 코드 오류/테스트 실패/작은 Refactor에 대해 Human 승인 요청을 하지 않는다.

다음 상황에서만 멈춘다.

- sudo/관리자 권한 필요
- 파괴적 파일/History 변경 필요
- V2 Architecture를 크게 변경해야 함
- Reference와 Requirements가 명확히 충돌

## Verification

반드시 실제 Evidence로 확인한다.

- Python compile/import
- pytest
- 기존 V1 Regression
- V2 Layout Model tests
- 앱 실행 가능 여부
- GUI 실행 환경이 가능하면 실제 창 표시

GUI를 직접 확인할 수 없다면 PASS라고 추측하지 말고 Human Visual Verification Required라고 기록한다.

작업이 끝나면 STATUS.md를 실제 결과에 맞게 갱신한다.

최종 보고는 다음만 간결히 작성한다.

- 구현 내용
- 테스트 결과
- 실행 방법
- Reference 대비 개선점
- Human이 직접 확인해야 할 항목
- 다음 Task(TASK-007) 준비 상태

지금 바로 Repository 상태를 조사하고 TASK-006부터 시작하라.
