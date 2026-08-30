# Codex Start Prompt

현재 새 프로젝트의 Repository root에 있다.

이 Repository의 Source of Truth:

- PROJECT.md
- REQUIREMENTS.md
- ARCHITECTURE.md
- DECISIONS.md
- AGENTS.md
- STATUS.md
- tasks/TASK-001.md ~ TASK-005.md

를 먼저 전부 읽어라.

이번 목표는 영상에서 본 물류창고 다중 로봇 시스템의 원리를 재현하는
"Warehouse Multi-Robot Simulator V1" 완성본 구현이다.

중요:

V1에서는 ROS2 / Gazebo / Nav2를 사용하지 않는다.

Python 2D Simulator로 다음을 완성한다.

- warehouse grid map
- shelves / walls
- minimum 3 robots
- A* path planning
- robot state
- simultaneous simulation ticks
- same-cell collision prevention
- head-on swap prevention
- goal/task
- planned path visualization
- start/pause/reset
- beginner-friendly README
- unit tests

Preferred GUI:
pygame

현재 Python 환경에서 pygame이 없으면 requirements.txt에 명시한다.
사용자가 설치할 수 없는 시스템 패키지나 sudo가 필요한 경우에만 멈춰서 보고한다.

작업 방식:

1. 현재 Repository 상태 조사
2. 명세 전체 읽기
3. TASK-001부터 순서대로 구현
4. 각 Task 구현 후 pytest
5. 오류가 있으면 직접 수정
6. TASK-005까지 완료
7. 전체 실행 확인
8. README 완성
9. STATUS.md를 실제 결과에 맞게 업데이트

Human에게 Task별 승인 요청을 하지 않는다.

Architecture 변경 / Scope 확대 / 시스템 권한 상승이 필요한 경우에만 질문한다.

완성되지 않은 skeleton, TODO, placeholder 상태로 종료하지 않는다.

최종 보고는 다음만 간결하게 작성한다.

- 구현 기능
- 실행 방법
- 테스트 결과
- 파일 구조
- 남은 제한사항

지금 바로 시작하라.
