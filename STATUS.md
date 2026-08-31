# Status

Project: Warehouse Multi-Robot Simulator

Current Version: V5.6.1
Current Phase: TASK-009F-A Implemented / Automated Verification Pass / Human Visual Flow Verification Required
Current Task: TASK-009F-A - Warehouse Visual Flow & Operational Explainability Upgrade

## Final Goal

Reference 영상의 2D 자동화 시스템을 단계적으로 재현한 뒤 ROS2 Humble + Gazebo Fortress + Nav2 기반 Multi-AMR Warehouse Digital Twin으로 발전시킨다.

## TASK-009F-A Result

Warehouse domain/timing을 변경하지 않고 화면 정보 우선순위를 Robot physical state에서 실제
material flow로 전환했다.

- 좌측 Receiving, 중앙 Storage/Rack, 우측 Outbound/Shipping의 큰 시각 zone
- 10개 logical location의 독립 card, occupancy/capacity와 actual box grid
- 같은 service station을 공유하는 logical rack도 겹치지 않는 display anchor 사용
- Robot row: Work(PUTAWAY/PICKING) → Phase → Item → From/To 순서
- human phase: TO PICKUP, PICKING ITEM, CARRYING, DROPPING ITEM, TRAFFIC/RESOURCE WAIT, HOLD, AVAILABLE
- Warehouse Robot click selection, actual remaining route, Item/SKU/Lot/Order/Cargo detail
- Shipping된 Item은 actual location contents에서 제거되므로 화면에서도 사라짐
- Warehouse business 300초 결과와 safety 결과는 V5.6 baseline 유지

Human visual verification 전 COMPLETE가 아니다. TASK-009G/V5.7 및 TASK-010/V6는 미시작이다.

## TASK-009F Result

V5.6은 Production Demo를 보존하면서 별도의 **Reference-derived layout + synthetic warehouse
scenario**를 제공한다.

- 5개 scheduled InboundOrder와 SKU A/B/C InventoryItem 18개
- capacity 8의 Receiving 2개, capacity 4의 logical StorageLocation 6개
- deterministic SKU compatibility / same-SKU preference / stable-ID putaway policy
- 3개 scheduled OutboundOrder와 stored-time/item-ID FIFO allocation
- PUTAWAY/PICKING WarehouseRequest를 기존 MaterialTask/Factory/Traffic으로 실행
- capacity reservation으로 storage/staging inbound overbooking 방지
- READY_TO_SHIP 후 5초 business Shipping event
- actual receiving/storage/staging contents만 Box로 렌더링
- PUT/PICK Robot badge 및 warehouse KPI/debug event panel

16 Robots / seed 1234 / 300 seconds:

- inbound 18, putaway completed 16, average putaway 64.181s
- stored/reserved inventory 9/24, staging 3, shipped items 2
- outbound orders 3 created / 1 shipped, cycle 37.767s
- integrity errors 0
- collision/head-on/deadlock/obstacle penetration 0/0/0/0

Human GUI verification 전 COMPLETE가 아니다. TASK-009G/V5.7 및 TASK-010/V6는 시작하지 않았다.

## TASK-009E Result

V5.5는 V5.4 production domain과 timing을 변경하지 않고 실제 TransportRequest를 읽는
presentation projection을 추가한다.

- Operational State와 Business Mission을 별도 필드로 표시
- Robot 근처에 `M03 SUP`, `M04 WIP`, `M07 QC`, `M09 OUT` 형식의 text/color badge
- 우측 panel에서 16대 Robot과 Mission, Lot, source/destination 확인
- SUPPLY/WIP/QC/OUT active 및 cumulative completed summary
- Robot click selection, 실제 remaining route highlight, source/destination S/D marker
- 실제 `MaterialLoad` ownership이 ON_ROBOT일 때만 Cargo 표시
- selected detail에서 WorkOrder, Request, Task, priority, reason 및 lifecycle 표시
- Normal 업무 화면과 Debug machine/buffer/trace 화면 분리
- 렌더링이 simulation state를 변경하지 않는 regression test

V5.4 동일 300초 baseline 유지:

- production 6/20
- requests 22 created / 20 completed
- average lead time 34.035s
- collisions/head-on/deadlocks/obstacle penetrations 0/0/0/0

Mission diversity: SUPPLY 8/8, WIP 4/3, QC 4/3, OUT 6/6 created/completed.
Human GUI verification 전 COMPLETE가 아니며 TASK-010 / V6는 시작하지 않았다.

## TASK-009D Result

V5.4는 Reference에서 파생한 화면 배치 위에 **합성 제조 시나리오**를 추가한다. 영상 속
설비의 실제 업무 의미를 확인한 것으로 주장하지 않는다.

- WorkOrder 2건과 추적 가능한 MaterialUnit/Lot 20개
- 용량 및 inbound reservation을 가진 8개 MaterialBuffer
- WAITING_MATERIAL / PROCESSING / WAITING_UNLOAD 상태를 가진 4개 ProductionMachine
- LINE_SUPPLY / WIP_TRANSFER / QC_TRANSFER / OUTBOUND_MOVE TransportRequest
- 모든 production MaterialTask를 TransportRequest와 WorkOrder까지 역추적 가능
- Material location source of truth는 MaterialUnit; MaterialLoad는 한 운송 leg의 Robot custody
- Machine starvation/blocking이 실제 Robot delivery/unload 지연으로 누적
- Work Order, production KPI, machine/buffer/trace 및 업무형 Robot task를 GUI에 표시
- 기존 V5.3 기본 실행과 synthetic factory profile은 regression 용도로 보존

16 robots / seed 1234 / 300 simulated seconds:

- production: 6 / 20, 1.200 units/min
- transport requests: 22 created / 20 completed
- average lead time: 34.035s; on-time rate: 0.9000
- WIP: 2; buffers: 12 / 52; inventory errors: 0
- largest starvation: QC_A 240.217s
- largest blocking: PROC_A 150.050s
- collisions/head-on/deadlocks/obstacle penetrations: 0 / 0 / 0 / 0
- full regression: 102 tests PASS

Evidence:

- `evidence/v5_4_realistic_factory.png`
- `evidence/v5_4_production_debug.png`
- `evidence/v5_4_material_trace.txt`
- `evidence/v5_4_factory_stress.txt`

TASK-009D is not COMPLETE until Human verifies the production GUI. TASK-010 / V6 has not started.

## V1 Baseline - Completed

V1은 최종 제품이 아니라 Core Algorithm Prototype으로 유지한다.

Completed:

- 22x16 warehouse grid
- Four robots
- Manhattan A*
- Robot state
- Simultaneous tick proposals/commits
- Same-cell conflict prevention
- Head-on swap prevention
- Pygame visualization
- Start/Pause/Reset
- Click-to-change-goal
- Headless smoke run
- 13 core tests reported passing at V1 completion

V1 GUI는 기존 STATUS 기록상 pygame이 없는 실행 환경 때문에 최종 Human Visual Verification이 남아 있었다.

## Direction Change Approved

V1의 단순 Grid 화면을 Reference 영상 재현의 최종 결과로 취급하지 않는다.

승인된 방향:

```text
V2  Video Layout Reconstruction
V3  Lane Graph + Continuous Motion
V4  Multi-Agent Traffic Control
V5  Task & Material Flow
V6  Fleet Management
V7  Video-like Digital Twin UI
V8  ROS2 Architecture Integration
V9  Gazebo Multi-Robot Warehouse
V10 Nav2 Autonomous Navigation
V11 ROS2 ↔ Digital Twin Synchronization
V12 Multi-AMR Warehouse Digital Twin
```

## Reference

- `VIDEO_ANALYSIS.md`: 현재 대화에서 제공된 Reference 영상 분석 기준
- 로컬 권장 경로: `reference/warehouse_reference.mp4`
- `reference/README.md`: Reference Asset 관리 규칙

영상에서 확인되지 않는 객체의 정확한 의미는 임의로 확정하지 않는다.

## TASK-006 Result

- Reference 영상 8개 시점의 프레임을 OpenCV로 실제 확인
- 1280x720 영상 좌표계 기반 `FacilityLayout` Domain Model 구현
- Zone, MachineBlock, Station, NetworkSegment, MobileEntity 분리
- 상단 8개 블록, 중앙 6x3 반복 설비, 좌우 Marker, 하단 Network 재구성
- backend-neutral Render Plan 구현
- 같은 Render Plan을 사용하는 pygame UI와 Pillow Evidence Renderer 구현
- V2를 기본 화면으로 전환하고 기존 V1은 `--v1` 옵션으로 보존
- Layout/Render Plan 신규 Test 4건 추가
- V1 Regression을 포함한 전체 17 tests passing
- PNG Evidence: `evidence/v2_reference_layout.png`
- Human pygame visual verification: PASS

## Verification

- Python compile/import: PASS
- V1 core regression tests: PASS
- V2 layout tests: PASS
- Pillow reference rendering: PASS (1280x720 PNG 직접 확인)
- pygame GUI window: PASS (Human verification)
- Human visual comparison against the video: PASS

V2 is COMPLETE. TASK-007 implementation is COMPLETE and Human Motion Verification is required. TASK-008 이상은 시작하지 않았다.

## TASK-007 Result

- V2 `NetworkSegment`에서 교차점과 끝점을 자동 추출
- 224 LaneNode / 359 LaneEdge Reference Graph
- Directed/Bidirectional edge와 neighbor/traversal API
- Euclidean heuristic Graph A*와 안전한 no-route 처리
- `progress 0.0~1.0` edge interpolation
- 남은 이동거리를 다음 edge로 넘기는 multi-edge transition
- FPS와 분리된 `MotionEngine.update(delta_time)`
- 서로 다른 route/speed/shape를 가진 5개 LaneMobileEntity
- 기본 실행 화면을 V3 motion demo로 연결
- V1 `--v1`, V2 `--render-reference`, V1 headless 경로 보존
- V3 Evidence: `evidence/v3_lane_motion.png`

## V3 Verification

- Python compile/import: PASS
- V1/V2 regression + V3 tests: 30 PASS
- Directed/Bidirectional/route/no-route tests: PASS
- progress/interpolation/edge transition/arrival tests: PASS
- FPS independence and lane-bound movement tests: PASS
- V3 demo 5-second headless snapshot: PASS
- V3 demo 60-second arrival (5/5 ARRIVED): PASS
- Pillow V3 Evidence rendering: PASS
- pygame continuous-motion verification: PASS (Human verification)

V3 is COMPLETE and Human Motion Verification is PASS.

## TASK-008 Result

- Default 16 entities; configurable from 1 to 64
- Seeded scenario generation with unique starts and varied goals/speeds/shapes
- Continuous arrival → new LaneNode goal → route → motion loop
- Central TrafficController separated from TrafficMotionEngine
- Exclusive destination Node and narrow Edge reservations
- Same-node, same-edge and head-on conflict prevention
- Longest waiting_count priority, stable creation-order tie break
- WAITING state, waiting time/count and blocked warning events
- Limited deterministic adjacent-goal recovery after 10-second block warning
- Runtime traffic metrics and debug rendering toggles
- V4 Evidence: `evidence/v4_traffic.png`
- Stress Evidence: `evidence/v4_traffic_stress.txt`

## V4 Verification

- Python compile/import: PASS
- V1/V2/V3 regression + V4 tests: 42 PASS
- Node/edge/head-on/release/priority/waiting tests: PASS
- Seed/16-entity/goal reassignment/continuous-operation tests: PASS
- 16 entities / 120 simulated seconds: PASS
- Completed trips: 97
- Reservation denials handled: 44,745
- Waiting events: 151
- Limited recoveries: 31
- Collision count: 0
- pygame continuous traffic verification: HUMAN REQUIRED

TASK-009 이상은 시작하지 않았다.

## TASK-008 Predictive Upgrade

- 4-edge predictive soft-reservation horizon with expiry
- Congestion-aware A*: distance + ownership + prediction + zone capacity
- Three traffic zones with capacity penalties
- 3-second reroute cooldown and 10% improvement threshold
- Acceleration-limited preferred/current/target speed coordination
- Wait-for cycle detection and deadlock-preventing response
- Traffic-aware goal selection and expanded performance metrics

## Predictive V4 Verification

16 entities / 300 simulated seconds:

- completed trips: 277
- moving ratio: 0.9892
- average speed: 36.698 px/s
- average cumulative wait per entity: 2.959 s
- max single wait: 4.650 s
- reroutes: 203
- stopped over 5 seconds: 0
- throughput: 55.400 trips/min
- collisions/head-on/deadlocks/indefinite waits: 0

24 entities / 300 simulated seconds:

- completed trips: 384
- moving ratio: 0.9355
- average speed: 36.031 px/s
- average cumulative wait per entity: 19.093 s
- max single wait: 5.017 s
- reroutes: 549
- stopped over 5 seconds: 18
- throughput: 76.800 trips/min
- collisions/head-on/deadlocks/indefinite waits: 0

Automated verification is PASS for required 16-entity acceptance. Human pygame verification is REQUIRED. TASK-009 이상은 시작하지 않았다.

## TASK-008A Result

Human이 발견한 Machine 관통 주행과 작은 topology gap을 수정했다.

- Machine expanded obstacle clearance: 7px
- Safe endpoint snap tolerance: 2px
- `vertical_3`, `vertical_5`, `vertical_7`: Machine 오른쪽 free aisle로 data-driven 재배치
- left/right loop 1px/2px gap: obstacle-safe snap
- Upper Cap: MobileEntity 주행 Evidence가 없어 회청색 visual-only 처리
- Machine 내부 장식: driving lane과 다른 짙은 청색으로 변경
- 하단 15px gap: Reference 하단 이동 객체와 정렬되는 중앙 `vertical_5`~`vertical_8`만 연결, 나머지는 unverified stub으로 유지
- Before: 224 nodes / 359 edges / 2 components / 9 unsafe edges
- After Human revision: 213 nodes / 355 edges / 1 driving component / 0 unsafe nodes / 0 unsafe edges
- Renderer source: Safe LaneGraph `network_segments()` + visual-only upper cap
- Rendered driving edges와 graph edges exact match; 1px/2px perpendicular near-gap 0
- Full regression and new safety tests: 57 PASS

16 entities / 300 seconds:

- completed trips: 272
- collisions/head-on/deadlocks/obstacle penetrations: 0
- stopped over 5 seconds: 0

24 entities / 300 seconds:

- completed trips: 395
- collisions/head-on/deadlocks/obstacle penetrations: 0
- stopped over 5 seconds: 23

Evidence:

- `evidence/v4_1_safe_lane_topology.png`
- `evidence/v4_1_topology_debug.png`
- `evidence/v4_1_safe_topology_stress.txt`

HUMAN TOPOLOGY / OBSTACLE VERIFICATION REQUIRED. TASK-009 이상은 시작하지 않았다.

## TASK-008B Result

Human 발견 문제인 "Safe Graph는 되었지만 rendered rail continuity가 불완전함"을 수정했다.

- Driving renderer source를 Safe LaneGraph `network_segments()`로 단일화
- Route/Motion/Renderer가 동일한 canonical LaneNode 좌표 사용
- Renderer driving segments 342 == graph edges 342
- Renderer에 누락되거나 추가된 driving edge 0
- 의도하지 않은 1px/2px perpendicular endpoint gap 0
- Upper Cap: 회청색 visual-only 유지
- Machine 내부 detail: 짙은 청색 facility primitive 유지
- 하단 중앙 `vertical_5`~`vertical_8`: bottom return driving connection 유지
- 나머지 vertical: y=618 cross aisle에서 driving 종료, y=618~633은 회청색 visual-only tail
- `D` debug overlay: LaneNode, Machine bounds, expanded clearance
- Before: 213 nodes / 355 edges / 1 component
- After: 200 nodes / 342 edges / 1 component
- Unsafe nodes / edges: 0 / 0
- Full tests: 57 PASS

새 300초 stress 결과:

- 16 entities: 272 trips; collisions/head-on/deadlocks/obstacle penetrations = 0
- 24 entities: 395 trips; collisions/head-on/deadlocks/obstacle penetrations = 0

Evidence:

- `evidence/v4_2_lane_continuity.png`
- `evidence/v4_2_lane_debug.png`
- `evidence/v4_2_traffic_stress.txt`

TASK-008B IMPLEMENTED / AUTOMATED VERIFICATION PASS / HUMAN LANE CONTINUITY VERIFICATION REQUIRED. TASK-009 이상은 시작하지 않았다.

## TASK-008C Result

Human 요청에 따라 reference-derived rail을 obstacle-safe warehouse Manhattan grid로 재구성했다.

- Reference aisle 좌표 기반 candidate grid: 30 segments
- Machine + Station 7px expanded obstacle interval pruning
- Surviving source segments: 53
- 상단 y=112 driving rail 연결
- 좌우 x=226/x=962 outer rail 및 Station stack 우회 연결
- 중앙 Machine row 사이 cross aisle 연결
- 모든 안전 vertical과 하단 y=555/588/618/648 return 연결
- Upper Cap y=66 enclosure만 회청색 visual-only 유지
- Before: 200 nodes / 342 edges / 1 component / cycle rank 143
- After: 251 nodes / 405 edges / 1 component / cycle rank 155
- Branching nodes: 203
- Rendered driving segments 405 == graph edges 405
- Unsafe nodes / edges: 0 / 0
- Unintended 1px/2px gaps: 0
- Full tests: 57 PASS

새 300초 stress 결과:

- 16 entities: 265 trips, 360 edges / 207 nodes 실제 사용
- 24 entities: 379 trips
- collisions/head-on/deadlocks/obstacle penetrations: 모두 0

Evidence:

- `evidence/v4_3_grid_lane_topology.png`
- `evidence/v4_3_grid_lane_debug.png`
- `evidence/v4_3_grid_lane_stress.txt`

TASK-008C COMPLETE / HUMAN GRID LANE VERIFICATION PASS.

## TASK-009 Result

- V4.3 Human Grid Lane Verification: PASS
- 8 obstacle-safe WorkStation service points
- Demo Flow A: `IN_A -> PROC_A -> QC_A -> OUT_A`
- Demo Flow B: `IN_B -> PROC_B -> BUFFER_B -> OUT_B`
- MaterialTask / MaterialLoad / RobotWorkState / TaskEvent Domain 구현
- Strict lifecycle 및 invalid transition 차단
- 2초 Pickup / 2초 Drop timer
- Queue target 6 / maximum active 10 / deterministic continuous generator
- 단순 최근접 reachable-source + stable-order assignment
- 기본 실행을 V5 task-driven factory로 전환
- 기존 V4 random traffic은 `--traffic-demo`로 보존
- compact task/robot UI panel과 carrying/picking/dropping marker
- `--headless-factory`, `--render-factory`, `--render-factory-debug`
- Full V1~V5 regression: 65 PASS

16 robots / 300 seconds:

- tasks created/completed: 55 / 46
- queued/active/idle robots: 6 / 3 / 11
- robot utilization: 0.2710
- average task cycle time: 50.066 seconds
- average pickup wait: 4.735 seconds
- loads in transit: 2
- completed checkpoint trend at 100/200/300 seconds: 16 / 32 / 45
- failed tasks: 0
- lost loads / duplicate ownership: 0 / 0
- pickup-before-arrival / drop-before-arrival: 0 / 0
- collisions/head-on/deadlocks/obstacle penetrations: 0

Evidence:

- `evidence/v5_factory_task_flow.png`
- `evidence/v5_factory_task_debug.png`
- `evidence/v5_factory_stress.txt`

TASK-009 IMPLEMENTED / AUTOMATED VERIFICATION PASS / HUMAN FACTORY FLOW VERIFICATION REQUIRED. TASK-010 이상은 시작하지 않았다.

## TASK-009A Result

- Root cause: source+destination full-lifecycle reservation limited eight service points to three active tasks
- Phase-aware source/destination capacity usage
- Pickup-complete destination acquisition
- 22 direct task handoffs before parking
- Productive / repositioning / idle utilization separation
- Dispatch block diagnostics and workload profiles
- Default/acceptance profile: BUSY (`queue_target=12`, `max_active=10`)
- Full tests: 71 PASS

16 robots / 300 seconds, seed 1234:

- completed tasks: 46 -> 70
- productive utilization: 0.4291
- repositioning utilization: 0.1297
- idle ratio: 0.4412
- average active / idle robots: 6.866 / 7.059
- direct handoffs / parking returns: 22 / 48
- blocked source/destination: 74 / 55
- blocked limit/no-idle/no-route: 0 / 0 / 0
- cycle time: 50.066 -> 60.350 seconds (higher-contention trade-off)
- collision/head-on/deadlock/obstacle penetration: 0
- load/lifecycle integrity violations: 0

24 robots / 300 seconds:

- tasks completed: 8
- productive utilization: 0.2627
- safety violations: 0

TASK-009A IMPLEMENTED / AUTOMATED VERIFICATION PASS / HUMAN FACTORY UTILIZATION VERIFICATION REQUIRED. TASK-010 이상은 시작하지 않았다.

## TASK-009B Result

Human은 TASK-009A GUI에서 backlog가 있는데도 Robot이 너무 많이 IDLE이라고 판단했다.
TASK-009B는 task assignment와 physical service capacity를 분리해 이 gate를 이어받았다.

- Source/destination별 obstacle-safe staging node와 deterministic wait queue
- 명시적 service/staging reservation; staged service entry 시점의 late reservation
- staging 부족 시 실제 task를 유지하는 safe remote `TASK_HOLDING`
- BUSY full assignment, RETURNING 재투입, completion direct handoff
- 10초 warm-up 이후 true idle/engagement metric과 M01~M16 panel
- Full regression: 79 PASS

16 robots / 300 seconds / seed 1234 / busy:

- completed checkpoints: 27 / 57 / 87
- productive / task waiting / engaged: 0.6971 / 0.3029 / 1.0000
- average true idle robots: 0.000
- min engaged / max true idle after warm-up: 16 / 0
- direct handoffs / parking returns: 87 / 0
- collision/head-on/deadlock/obstacle penetration/current indefinite wait: 0

24 robots / 300 seconds completed 82 tasks with engaged ratio 1.0000 and safety 0.
Cycle time 96.642 seconds는 남은 physical contention을 보여준다.

TASK-009B IMPLEMENTED / AUTOMATED PASS / HUMAN FULL FLEET ENGAGEMENT VERIFICATION REQUIRED. TASK-010은 시작하지 않았다.

## TASK-009C Result

V5.2의 `ENGAGED=100%`는 task ownership만 증명했다. 새 position 계측 baseline은
actual motion 0.8036이었지만 stationary holding 0.0861, 최대 연속 정지 44.917초,
long holding event 31건을 확인했다. Random link 생성과 priority-only dispatch로
Flow A 후단 두 link에 active task 12개가 편중된 것이 주 원인이었다.

- 0.01px actual position delta 기반 physical activity instrumentation
- movement/service/traffic wait/resource wait/flow hold/true idle 분리
- per-robot distance/stationary time, station queue, flow-link WIP 진단
- BUSY/STRESS real flow link deterministic balancing
- free staging, active-link WIP, station pressure 기반 bounded dispatch
- Station당 obstacle-safe staging 2개에서 3개로 확장; service capacity 1 유지
- V5.3 physical activity panel과 debug STILL 표시
- Full regression: 89 PASS

16 robots / 300 seconds / seed 1234 / busy:

- completed checkpoints: 33 / 76 / 116
- actual motion / service / useful: 0.8150 / 0.1007 / 0.9157
- traffic wait / resource wait / holding: 0.0172 / 0.0651 / 0.0020
- average moving / holding robots: 13.041 / 0.033
- cycle time: 60.287 seconds
- true idle/collision/head-on/deadlock/obstacle penetration: 0

24 robots completed 127 tasks; actual motion 0.7381, holding 0.0292, safety 0.

TASK-009C IMPLEMENTED / AUTOMATED VERIFICATION PASS / HUMAN ACTUAL FLEET MOTION VERIFICATION REQUIRED. TASK-010은 시작하지 않았다.
