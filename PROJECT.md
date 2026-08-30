# Warehouse Multi-Robot Simulator

## 1. Project Goal

이 프로젝트의 최종 목표는 첨부한 물류/자동화 시뮬레이션 영상을 단순히 참고하는 수준이 아니라, **영상에서 확인되는 2D 자동화 시스템의 화면과 동작을 단계적으로 재현한 뒤 ROS2, Gazebo, Nav2 기반의 실제 다중 AMR Digital Twin으로 업그레이드하는 것**이다.

현재 V1은 최종 제품이 아니라 알고리즘 학습용 Prototype이다.

V1에서 만든 Grid, A*, Robot State, 충돌 방지, Simulation Tick은 이후 버전에서 재사용할 수 있는 기초 개념으로 유지한다.

## 2. Reference Target

영상에서 직접 확인되는 시각적 특징을 재현 목표로 사용한다.

- 넓은 흰색 계열 2D 자동화 설비 화면
- 반복 배치된 여러 설비/작업 구역
- 전체 시설을 연결하는 얇은 주행 Network
- Network 위를 이동하는 여러 작은 객체
- 서로 다른 색/형태의 여러 Entity
- 여러 Entity의 동시 이동
- 상단, 중앙, 좌우, 하단으로 구분되는 작업 영역

영상에서 객체의 정확한 산업적 의미가 확인되지 않는 경우 임의로 AGV, Pallet 등의 의미를 확정하지 않는다.
초기 구현에서는 `MobileAgent`, `Load`, `Station`, `Machine` 같은 중립적인 이름을 사용한다.

## 3. Final Product Vision

최종 시스템은 다음 두 화면/계층을 동시에 가진다.

```text
2D Digital Twin / Fleet Dashboard
             ↕ ROS2
Fleet Manager / Traffic Manager / Task Manager
             ↕
          Nav2
             ↕
Gazebo Multi-Robot Warehouse
```

2D 화면의 Robot 위치를 임의 Animation으로만 움직이는 것이 아니라, 최종 단계에서는 Gazebo Robot의 `/odom`, `/tf`, 상태 Topic을 받아 실시간 Digital Twin으로 표시한다.

## 4. Version Roadmap

```text
V1   Core Algorithm Prototype             [COMPLETED]
     Grid + A* + Robot + Basic Collision

V2   Video Layout Reconstruction
     영상과 유사한 2D 시설 Layout과 시각 스타일 재현

V3   Lane Graph + Continuous Motion
     Grid 자유이동 대신 Node/Edge/Lane Network와 부드러운 이동

V4   Predictive Multi-Agent Traffic Control
     Reservation, congestion routing, speed coordination, deadlock prevention

V5   Task & Material Flow
     Pickup/Drop/Move 형태의 작업과 Station 간 흐름

V6   Fleet Management
     다수 MobileAgent의 작업 배정, 상태, Queue, 재계획

V7   Video-like Digital Twin UI
     영상 재현 단계의 통합 완성 및 운영/통계 UI

V8   ROS2 Architecture Integration
     Core Domain을 ROS2 Node/Topic/Service/Action 경계와 연결

V9   Gazebo Multi-Robot Warehouse
     창고 World, 복수 AMR, LiDAR/Odom/TF, Namespaces

V10  Nav2 Autonomous Navigation
     실제 ROS2 Map/Nav2 기반 목표 자율주행

V11  ROS2 ↔ Digital Twin Synchronization
     Gazebo/ROS2 실제 상태를 2D 관제 화면에 실시간 반영

V12  Multi-AMR Warehouse Digital Twin
     Fleet + Traffic + Task + Nav2 + Gazebo + 2D 관제 통합
```

## 5. Primary User

ROS2, AMR/AGV, 물류 자동화, 다중 로봇 Fleet System, Digital Twin을 단계적으로 학습하려는 초보 개발자.

## 6. Project Principles

1. 영상 재현과 산업적 의미 추정을 구분한다.
2. 영상에서 보이지 않는 의미는 임의로 사실처럼 확정하지 않는다.
3. 2D Simulation Core를 ROS2/Gazebo 전환 후에도 재사용할 수 있도록 UI와 분리한다.
4. V2~V7에서는 물류/Fleet 동작을 먼저 이해하고, V8부터 ROS2 경계를 추가한다.
5. 최종적으로 2D 화면은 버리는 Prototype이 아니라 ROS2 Digital Twin Dashboard로 발전시킨다.
6. 각 Version은 실행 가능하고 Test 가능한 상태로 종료한다.
