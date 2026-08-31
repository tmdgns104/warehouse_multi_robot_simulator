# Project Structure and Dependency Direction

| Module | Owns | Must not own | Depends on / called by |
|---|---|---|---|
| `facility_layout.py` | Zone/MachineBlock/Station/NetworkSegment/MobileEntity geometry | routing/business semantics | scenario, render plan |
| `lane_safety.py` | candidate grid, obstacle pruning, safe graph validation | task dispatch | layout, lane graph |
| `lane_graph.py` | LaneNode/LaneEdge/Traversal graph | traffic policy | facility segments |
| `graph_planner.py` | Euclidean graph A* | reservations | lane graph |
| `motion.py` | continuous edge progress | factory/warehouse state | lane graph/planner |
| `traffic.py` | node/edge/predictive reservations, wait cycles | business requests | traffic simulation |
| `traffic_planner.py` | congestion-aware A* costs | inventory | graph/controller |
| `traffic_simulation.py` | safe continuous multi-entity motion and traffic metrics | pickup/drop | motion/traffic/planner |
| `task_manager.py` | MaterialTask/MaterialLoad states and custody integrity | demand generation/path planning | FactoryEngine |
| `factory.py` | Robot assignment, staging, service, pickup/drop orchestration | production/warehouse demand | task manager/traffic |
| `production.py` | WorkOrder, MaterialUnit, machines/buffers/TransportRequest | Robot safety/rendering | FactoryEngine |
| `warehouse.py` | orders, InventoryItem/location, WarehouseRequest, shipping | rendering/battery/fleet optimization | FactoryEngine |
| `mission_view.py` | read-only production mission projection | state mutation | production/factory |
| `warehouse_view.py` | read-only warehouse box/Robot projection and display anchors | inventory mutation | warehouse/factory |
| `reference_*_scenario.py` | deterministic composition/defaults | domain algorithms | corresponding engines |
| `render_plan.py` | backend-neutral primitives | simulation mutation | layout |
| `reference_renderer.py` | pygame/Pillow UI and evidence | business decisions | all read-only projections |
| `app.py` | CLI selection and simulation loop | domain rules | scenario factories/renderers |

```text
WarehouseEngine / ProductionEngine
        ↓ creates requirement
WarehouseRequest / TransportRequest
        ↓ links
MaterialTask + MaterialLoad
        ↓ executed by
FactoryEngine
        ↓ delegates motion safety
TrafficMotionEngine → TrafficController → Safe LaneGraph

View projection ← read-only domain/factory state → Renderer
```

V1 (`map.py`, `planner.py`, `robot.py`, `simulation.py`, `ui.py`) remains regression code and must
not be deleted or silently merged into V3+ classes.
