# TASK-008 - V4 Multi-Agent Traffic Control

Status: PLANNED

## Goal

여러 MobileAgent가 같은 Lane Network를 동시에 사용할 때 충돌과 교차로 혼잡을 제어하는 Traffic Manager를 구현한다.

## Deliverables

- Node Reservation
- Edge Reservation
- 반대 방향 Edge 동시 진입 방지
- Intersection Group/Lock
- WAITING / reservation-denied 상태
- waiting time 기반 우선순위
- 장기 정체/Deadlock Warning Event
- 10대 이상 Agent deterministic scenario

## Constraints

- 완전 최적 MAPF/CBS 구현은 필수 아님
- Task 자동 배정은 V5/V6 범위
- ROS2/Gazebo 추가 금지

## Verification

- 동일 Node 동시 점유 없음
- 단일 차선 Head-on 충돌 없음
- 교차로 Reservation Test PASS
- 장기 대기 Event 발생 검증
- 10+ Agent Scenario가 충돌 없이 실행
