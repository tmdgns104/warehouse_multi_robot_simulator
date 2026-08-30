# Warehouse Multi-Robot Simulator

## 1. Project Goal

영상에서 본 물류창고 다중 이동 로봇 관제 시스템을 이해하고 재현하기 위한 학습용 프로젝트다.

최종적으로는 다음 방향으로 확장한다.

V1 2D Warehouse Multi-Robot Simulator
→ V2 Path Planning
→ V3 Multi-Robot Collision Avoidance
→ V4 Task / Fleet Manager
→ V5 ROS2 Fleet Manager
→ V6 Gazebo Multi-Robot
→ V7 Nav2
→ V8 Web Monitoring Dashboard

이번 구현 범위는 **V1**이다.

V1은 ROS2 / Gazebo를 사용하지 않는다.
먼저 Python 기반 2D 시뮬레이터에서 다음 원리를 눈으로 이해하는 것이 목적이다.

- 창고 Map
- Grid
- Robot
- Start / Goal
- A* Path Planning
- 여러 로봇
- 경로 이동
- 기본적인 충돌 방지
- 작업 상태
- 화면 시각화

## 2. Primary User

ROS2, AMR, AGV, 다중 로봇 시스템을 처음 배우는 초보자.

## 3. V1 Success Criteria

사용자가 프로그램을 실행하면 창고 형태의 2D Map이 열린다.

최소 3대의 로봇이 존재한다.

각 로봇은 목적지를 가진다.

각 로봇은 A* 기반 경로를 생성한다.

로봇은 장애물 / 선반을 통과하지 않는다.

동일 셀에 두 로봇이 동시에 진입하지 않는다.

화면에서 다음을 확인할 수 있다.

- Robot ID
- 현재 위치
- 목표 위치
- 계획 경로
- 상태
- 작업 진행

초보자가 README만 보고 실행할 수 있어야 한다.
