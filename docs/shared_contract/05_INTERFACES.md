# Public Interface Contract

Signatures below are canonical. Private `_...` methods describe behavior but are not cross-module API.

## Scenario factories

```python
def create_reference_warehouse_scenario(entity_count=16, *, seed=1234)
def create_reference_production_scenario(
    entity_count: int = 16, *, seed: int = 1234, target_per_product: int = 10
) -> ReferenceProductionScenario
def create_reference_factory_scenario(
    entity_count: int = 16, *, seed: int = 1234,
    config: FactoryConfig | None = None,
    profile: FactoryProfile | str = FactoryProfile.BUSY,
) -> ReferenceFactoryScenario
def create_reference_traffic_scenario(
    entity_count: int = 16, *, seed: int = 1234, looping: bool = True
) -> ReferenceTrafficScenario
def create_reference_motion_scenario() -> ReferenceMotionScenario
def create_reference_layout() -> FacilityLayout
```

Documentation conflict: warehouse factory currently lacks annotations and explicit return annotation;
call syntax and defaults above are exact and must remain compatible.

## Warehouse engine and locations

```python
WarehouseEngine(factory: FactoryEngine)
engine.update(dt)
engine.pause(); engine.start(); engine.reset()
engine.validate_safety()
engine.validate_inventory_integrity()
engine.warehouse_metrics -> WarehouseMetrics
engine.item_trace(item_id)

InventoryLocation.add(item_id)
InventoryLocation.remove(item_id)
InventoryLocation.reserve(request_id) -> bool
InventoryLocation.receive(request_id, item_id)
InventoryLocation.occupied
InventoryLocation.free
```

`WarehouseEngine.__getattr__` delegates unresolved attributes to `factory`; callers use
`engine.entities`, `engine.robot_tasks`, `engine.activity_states`, `engine.graph`, `engine.stations`.

## Production engine and buffers

```python
ProductionEngine(factory: FactoryEngine, *, target_per_product: int = 10)
engine.update(delta_time: float) -> None
engine.validate_safety() -> None
engine.validate_production_integrity() -> None
engine.material_trace(material_id: str) -> tuple[MaterialTraceEvent, ...]
engine.production_metrics -> ProductionMetrics

MaterialBuffer.add(material_id: str) -> None
MaterialBuffer.remove(material_id: str) -> None
MaterialBuffer.reserve_inbound(request_id: str) -> bool
MaterialBuffer.receive(request_id: str, material_id: str) -> None
```

## Task and Factory execution

```python
FactoryTaskManager.create_task(task: MaterialTask, load: MaterialLoad) -> None
FactoryTaskManager.assign(task: MaterialTask, robot_id: str, now: float) -> None
FactoryTaskManager.transition(task: MaterialTask, state: TaskState, now: float) -> None
FactoryTaskManager.reserve_load(task: MaterialTask) -> None
FactoryTaskManager.pickup(task: MaterialTask, robot_id: str, now: float) -> None
FactoryTaskManager.drop(task: MaterialTask, robot_id: str) -> None
FactoryTaskManager.validate_load_integrity() -> None
FactoryTaskManager.queued / active / completed

FactoryEngine(
    traffic: TrafficMotionEngine, stations: Iterable[WorkStation],
    flows: Iterable[tuple[str, ...]], *, seed: int = 1234,
    config: FactoryConfig = FactoryConfig(),
)
FactoryEngine.update(delta_time: float) -> None
FactoryEngine.validate_safety() -> None
FactoryEngine.factory_metrics -> FactoryMetrics
FactoryEngine.station_diagnostics() -> dict[str, dict[str, object]]
FactoryEngine.flow_diagnostics() -> dict[tuple[str, str], dict[str, float | int]]
```

## Graph, planner, motion and traffic

```python
lane_graph_from_segments(segments: Iterable[NetworkSegment]) -> LaneGraph
graph_astar(graph: LaneGraph, start: str, goal: str) -> Optional[list[str]]
build_safe_lane_graph(layout: FacilityLayout) -> LaneGraph
validate_lane_graph_safety(graph: LaneGraph, obstacles: Iterable[RectangleObstacle]) -> None

LaneGraph.add_node(node); add_edge(edge); node(node_id); edge(edge_id)
LaneGraph.neighbors(node_id); traversals(node_id); traversal(source, target)
LaneGraph.nearest_node(point); network_segments()

TrafficMotionEngine.assign_goal(entity: LaneMobileEntity, goal_node: str) -> bool
TrafficMotionEngine.update(delta_time: float) -> None
TrafficMotionEngine.validate_safety() -> None
TrafficMotionEngine.metrics -> TrafficMetrics
```

## View and renderer

```python
warehouse_robot_view(engine, robot_id) -> WarehouseRobotView
warehouse_robot_views(engine) -> tuple[WarehouseRobotView, ...]
warehouse_box_views(engine) -> tuple[WarehouseBoxView, ...]
robot_mission_view(engine, robot_id: str) -> RobotMissionView
all_robot_missions(engine) -> tuple[RobotMissionView, ...]
mission_counts(engine) -> tuple[MissionCount, ...]

render_warehouse_with_pillow(
    layout, engine, output: Path, size=(1280, 720), debug=False,
    selected_robot_id: str | None = None,
)
render_factory_with_pillow(
    layout: FacilityLayout, engine, output: Path, size=(1280, 720),
    debug=False, selected_robot_id: str | None = None,
) -> Path
```

Render/projection calls must not advance time or mutate any domain collection/state.
