# TASK-010 - V6 Fleet Management

Status: PLANNED

## Goal

다수 MobileAgent와 Task Queue를 중앙에서 관리하는 Fleet Manager를 구현한다.

## Deliverables

- Fleet Registry
- Agent Availability State
- Task Assignment Policy
- Distance/Waiting 기반 단순 Heuristic
- Route 요청/재계획 연결
- Traffic Manager 연동
- Agent/Task Metrics
- Event Log

## Metrics

- active agents
- idle agents
- waiting agents
- queued tasks
- completed tasks
- average task time
- traffic wait count

## Constraints

- Fleet Manager가 UI와 직접 결합되지 않음
- ROS2 Node 구현은 V8

## Verification

- Idle Agent에 Task 자동 배정
- Busy Agent 중복 배정 없음
- 완료 후 다음 Task 배정
- 장기 대기/경로 실패 시 상태가 관측 가능
- Multi-task deterministic scenario PASS
