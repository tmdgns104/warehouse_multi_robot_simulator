# TASK-007 - V3 Lane Graph + Continuous Motion

Status: COMPLETE / HUMAN MOTION VERIFICATION PASS

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

## Implementation Result

- V2 NetworkSegment 교차점을 자동 분할하여 LaneGraph 생성
- Reference graph: 224 nodes / 359 edges
- Directed/Bidirectional edge 및 neighbor/traversal 조회
- Euclidean heuristic 기반 Graph A*
- `MotionEngine.update(delta_time)` 연속 이동
- 5개 MobileEntity demo route
- V1/V2 regression 포함 30 tests passing
- `evidence/v3_lane_motion.png` 생성

Human이 pygame에서 연속 이동, 수평/수직/다중 Edge 이동과 정상 실행을 확인했다.
