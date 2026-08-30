# Decisions

## ADR-001 - V1은 ROS2 없이 Python 2D Simulator로 구현

Status: Accepted

### Reason

초보자가 ROS2, Gazebo, Nav2, 다중 로봇 조정을 동시에 배우면
문제의 원인을 파악하기 어렵다.

먼저 2D 환경에서 다음 핵심 개념을 눈으로 확인한다.

- Grid Map
- A*
- Robot State
- Multi-Robot Conflict
- Task
- Simulation Tick

그 후 같은 개념을 ROS2로 옮긴다.

---

## ADR-002 - Path Planning은 A*

Status: Accepted

V1에서는 구현과 시각화가 쉽고,
Grid 기반 창고 경로 계획 학습에 적합한 A*를 사용한다.

---

## ADR-003 - GUI와 Core Logic 분리

Status: Accepted

Path Planner / Collision / Simulation은 GUI 없이 Test 가능해야 한다.

---

## ADR-004 - V1 Collision Avoidance는 Reservation 기반 단순 정책

Status: Accepted

CBS, WHCA*, MAPF 최적화는 V1 범위 밖이다.

V1에서는:
- same-cell conflict
- head-on swap

을 방지한다.

---

## ADR-005 - GUI Framework

Preferred: pygame

Reason:
- 2D Grid Simulation에 적합
- 설치와 실행이 단순
- 애니메이션 표현이 쉬움

단, 현재 환경에서 pygame 사용이 불가능하면
Tkinter를 대안으로 사용할 수 있다.
