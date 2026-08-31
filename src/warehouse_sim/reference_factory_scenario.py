"""Deterministic V5 factory roles, service points, and material flows."""

from __future__ import annotations

from dataclasses import dataclass

from .factory import FactoryConfig, FactoryEngine, FactoryProfile, factory_config_for_profile
from .graph_planner import graph_astar
from .lane_safety import driving_obstacles
from .reference_traffic_scenario import create_reference_traffic_scenario
from .task_manager import WorkStation
from .traffic_simulation import TrafficMotionEngine


@dataclass(frozen=True)
class ReferenceFactoryScenario:
    layout: object
    graph: object
    engine: FactoryEngine


def _service_node(graph, x: float, y: float, used: set[str]) -> str:
    candidates = sorted(
        graph.nodes,
        key=lambda node: (abs(node.x - x) + abs(node.y - y), node.id),
    )
    node = next(node for node in candidates if node.id not in used and len(graph.neighbors(node.id)) >= 2)
    used.add(node.id)
    return node.id


def _staging_nodes(graph, service_node_id: str, used: set[str], count: int = 3) -> tuple[str, ...]:
    """Choose nearby non-junction lane nodes so waiting does not occupy a hub."""
    service = graph.node(service_node_id)
    candidates = sorted(
        (
            node for node in graph.nodes
            if node.id not in used
            and node.id != service_node_id
            and 1 <= len(graph.neighbors(node.id)) <= 3
            and graph_astar(graph, node.id, service_node_id) is not None
        ),
        key=lambda node: (abs(node.x - service.x) + abs(node.y - service.y), node.id),
    )
    selected = tuple(node.id for node in candidates[:count])
    if len(selected) != count:
        raise ValueError(f"Not enough safe staging nodes for {service_node_id}")
    used.update(selected)
    return selected


def create_reference_factory_scenario(
    entity_count: int = 16,
    *,
    seed: int = 1234,
    config: FactoryConfig | None = None,
    profile: FactoryProfile | str = FactoryProfile.BUSY,
) -> ReferenceFactoryScenario:
    config = config or factory_config_for_profile(profile)
    base = create_reference_traffic_scenario(entity_count, seed=seed, looping=False)
    for entity in base.engine.entities:
        entity.goal_node = entity.current_node
        entity.route = [entity.current_node]
        entity.route_index = 0
        entity.current_edge = None
        entity.progress = 0.0
    traffic = TrafficMotionEngine(
        base.graph,
        base.engine.entities,
        seed=seed,
        looping=False,
        blocked_warning_seconds=3.0,
        zones=base.engine.congestion.zones,
        obstacles=driving_obstacles(base.layout),
    )
    # Keep service docks distinct from the deterministic robot parking nodes;
    # otherwise an idle robot could permanently occupy a future task target.
    used = {entity.current_node for entity in traffic.entities}
    specs = (
        ("IN_A", "INPUT", "machine_0_0", 334, 219),
        ("PROC_A", "PROCESS_A", "machine_1_1", 429, 343),
        ("QC_A", "INSPECTION", "machine_2_3", 640, 555),
        ("OUT_A", "OUTPUT", "machine_0_5", 862, 219),
        ("IN_B", "INPUT", "machine_2_0", 334, 555),
        ("PROC_B", "PROCESS_B", "machine_1_2", 524, 343),
        ("BUFFER_B", "BUFFER", "machine_0_3", 640, 219),
        ("OUT_B", "OUTPUT", "machine_2_5", 862, 555),
    )
    station_specs = []
    for identifier, role, facility_id, x, y in specs:
        service = _service_node(base.graph, x, y, used)
        station_specs.append((identifier, role, facility_id, service))
    stations = tuple(
        WorkStation(identifier, role, facility_id, service, _staging_nodes(base.graph, service, used))
        for identifier, role, facility_id, service in station_specs
    )
    flows = (
        ("IN_A", "PROC_A", "QC_A", "OUT_A"),
        ("IN_B", "PROC_B", "BUFFER_B", "OUT_B"),
    )
    engine = FactoryEngine(traffic, stations, flows, seed=seed, config=config)
    return ReferenceFactoryScenario(base.layout, base.graph, engine)
