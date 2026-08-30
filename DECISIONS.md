# Decisions

## ADR-001 - V1은 ROS2 없이 Python 2D Simulator로 구현

Status: Accepted / Historical Baseline

V1은 Grid, A*, Robot State, Basic Collision을 학습하기 위한 Prototype으로 유지한다.

---

## ADR-002 - V1 Path Planning은 Grid A*

Status: Accepted / Historical Baseline

V1 구현을 위한 선택이다.
V3부터는 영상형 Lane Network에 맞게 Graph Route Planning으로 확장한다.

---

## ADR-003 - GUI와 Core Logic 분리

Status: Accepted / Still Active

Path Planning, Traffic, Task, Fleet Logic은 GUI 없이 Test 가능해야 한다.

---

## ADR-004 - V1 Collision Avoidance는 단순 Reservation

Status: Accepted / Historical Baseline

V1의 same-cell/head-on swap 방지는 V4 Traffic Manager 설계의 기초로 사용한다.

---

## ADR-005 - V2~V7 Primary Renderer는 Python 2D

Status: Accepted

영상의 시각적/동작적 특징을 빠르게 재현하기 위해 V2~V7은 Python 2D Renderer를 유지한다.

Pygame을 우선 사용하되 Renderer와 Domain을 분리하여 향후 교체 가능하게 한다.

---

## ADR-006 - 영상 재현은 Grid가 아닌 Lane Graph를 중심으로 확장

Status: Accepted

Reference 영상에서는 이동 객체가 임의 공간을 자유 이동하기보다 정해진 Network를 따라 움직이는 형태가 시각적으로 확인된다.

따라서 V3부터 핵심 이동 모델은 다음으로 전환한다.

```text
LaneNode → LaneEdge → LaneNode
```

기존 Grid A*는 삭제하지 않고 V1 Prototype/Test Reference로 유지한다.

---

## ADR-007 - Reference에서 확인되지 않는 의미는 확정하지 않음

Status: Accepted

영상만으로 초록/검정/노랑 객체가 실제로 AGV, Pallet, Carrier 등 무엇인지 확정할 수 없다.

문서와 코드에서는 확인 전까지 중립 이름을 사용한다.

- MobileAgent
- Load
- Machine
- Station
- Marker

시각적 재현과 산업적 의미 추론을 분리한다.

---

## ADR-008 - 2D Simulator는 ROS2 전환 후에도 폐기하지 않음

Status: Accepted

V2~V7의 2D 프로그램은 최종적으로 ROS2/Gazebo 상태를 표시하는 Digital Twin Dashboard로 발전시킨다.

따라서 UI가 내부 Simulation 객체에 과도하게 결합되지 않도록 Snapshot/Adapter 경계를 둔다.

---

## ADR-009 - ROS2는 Domain Core의 Adapter Layer

Status: Accepted

V8부터 ROS2를 추가하되 Fleet Policy, Task Lifecycle, Traffic Reservation 등의 핵심 Domain Logic은 가능한 한 ROS2 비종속 Python으로 유지한다.

ROS2 Node는 다음 책임을 가진다.

- Message/Action/Service 통신
- Robot Namespace 관리
- External State 수집
- Domain 명령 전달

---

## ADR-010 - Gazebo Multi-Robot은 Namespace/Frame 격리를 필수로 함

Status: Accepted

V9부터 Robot별로 Namespace와 TF Frame을 분리한다.

예:

```text
/robot_01/odom
/robot_01/scan
/robot_01/cmd_vel
```

다중 Robot에서 Topic과 TF 충돌이 발생하지 않아야 한다.

---

## ADR-011 - Fleet Manager는 직접 Wheel Velocity를 생성하지 않음

Status: Accepted

V10부터 Robot의 실제 주행 제어는 Nav2가 담당한다.

Fleet Manager는 Task, Goal, 상위 수준 Traffic Coordination을 담당하고 Nav2에 목표를 전달한다.

```text
Fleet Goal → Nav2 → /cmd_vel → Robot
```

---

## ADR-012 - Traffic Manager와 Nav2의 책임 분리

Status: Accepted

Traffic Manager:
- Robot 간 Node/Edge/Zone 사용 조정
- 교차로/좁은 구간 상위 수준 예약

Nav2:
- 개별 Robot 경로 추종
- Local Obstacle Avoidance
- 실제 Velocity Command

두 계층의 책임을 혼합하지 않는다.

---

## ADR-013 - 최종 Digital Twin 위치의 Source of Truth는 ROS2/Gazebo

Status: Accepted

V7까지 화면 위치는 내부 Simulation State에서 나온다.

V11 이후에는 Gazebo의 실제 Robot 상태(`/odom`, TF 등)가 Dashboard 위치의 Source of Truth가 된다.

이를 통해 2D 화면과 3D Gazebo가 같은 Robot 상태를 표현하도록 한다.

---

## ADR-014 - Task Assignment와 Station Service Capacity 분리

Status: Accepted

Robot에게 실제 MaterialTask를 배정하는 것은 Station service node를 점유하는 것과
다르다. Source/destination staging 및 remote holding에서 기다릴 수 있으며 service는
entry permission 시점부터 pickup/drop 종료까지만 명시적으로 예약한다.

`TASK_HOLDING`은 assigned nonterminal task가 있는 factory resource wait이며 IDLE이나
dummy patrol이 아니다. 모든 이동은 기존 Traffic Controller와 Safe LaneGraph를 따른다.
