# TASK-013 - V9 Gazebo Multi-Robot Warehouse

Status: PLANNED

## Goal

Reference 2D Layout과 개념적으로 대응되는 Gazebo Warehouse World를 만들고 복수 AMR을 동시에 실행한다.

## Deliverables

- Gazebo Fortress Warehouse World
- Static Warehouse Geometry
- Differential Drive AMR Model
- 최소 3대, 목표 5대 이상 Robot Spawn
- Robot별 Namespace
- Robot별 TF Frame 분리
- LiDAR
- Odometry
- `/cmd_vel`
- ROS2/Gazebo Bridge 또는 적절한 Plugin 구성
- Multi-Robot Launch

## Constraints

- 아직 Nav2 Goal Navigation은 V10
- Robot Namespace/TF 충돌을 임시 Remap으로 숨기지 않음
- 2D Digital Twin을 폐기하지 않음

## Verification

- Gazebo Headless launch 성공
- 모든 Robot 존재 확인
- Robot별 `/odom`, `/scan`, `/cmd_vel`, TF 확인
- 한 Robot의 명령이 다른 Robot을 움직이지 않음
- Robot 간 Topic/Frame 충돌 없음
