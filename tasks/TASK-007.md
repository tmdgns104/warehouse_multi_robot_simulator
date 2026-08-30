# TASK-007 - V3 Lane Graph + Continuous Motion

Status: PLANNED

## Goal

Grid Cell 자유이동 중심 구조에서 Reference 영상에 더 가까운 `LaneNode / LaneEdge` 이동 Network로 전환하고, Agent가 Edge 위를 부드럽게 이동하도록 한다.

## Deliverables

- LaneNode / LaneEdge Domain Model
- Directed/Bidirectional Edge 지원
- Graph A* 또는 Dijkstra Route Planner
- Agent의 edge_id / progress / speed 상태
- Simulation Update와 Rendering Frame 분리
- Edge 보간 기반 Smooth Motion
- Route/No-route Unit Tests

## Constraints

- V1 Grid Planner 삭제 금지
- Traffic Reservation은 최소 Interface만 준비; 본 구현은 V4
- ROS2/Gazebo 추가 금지

## Verification

- Agent가 Lane 밖으로 이동하지 않음
- Source→Destination Route 생성
- Edge 진행률이 연속적으로 증가
- Renderer에서 순간 Cell 점프가 아닌 부드러운 이동 확인
- 기존 Regression PASS
