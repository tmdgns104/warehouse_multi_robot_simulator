"""Application entry point for GUI and repeatable headless smoke runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from warehouse_sim.simulation import create_default_simulation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--headless-ticks",
        type=int,
        metavar="N",
        help="run N core simulation ticks without opening pygame",
    )
    parser.add_argument(
        "--headless-traffic",
        type=float,
        metavar="SECONDS",
        help="run the V4 continuous traffic demo without pygame",
    )
    parser.add_argument(
        "--headless-factory",
        type=float,
        metavar="SECONDS",
        help="run the V5 task-driven factory without pygame",
    )
    parser.add_argument(
        "--render-factory",
        type=Path,
        metavar="PNG",
        help="render a V5 factory task-flow snapshot and exit",
    )
    parser.add_argument(
        "--render-factory-debug",
        type=Path,
        metavar="PNG",
        help="render V5 task flow with service-point labels",
    )
    parser.add_argument(
        "--traffic-demo",
        action="store_true",
        help="open the preserved V4 random traffic demo instead of V5 factory flow",
    )
    parser.add_argument(
        "--factory-profile",
        choices=("light", "normal", "busy", "stress"),
        default="busy",
        help="V5 factory workload profile (default: busy)",
    )
    parser.add_argument(
        "--render-traffic",
        type=Path,
        metavar="PNG",
        help="render a V4 traffic snapshot with Pillow and exit",
    )
    parser.add_argument(
        "--entity-count", "--entities",
        type=int,
        default=16,
        metavar="N",
        help="V4 demo entity count (1-64, default: 16)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1234,
        help="deterministic V4 scenario seed",
    )
    parser.add_argument(
        "--one-shot",
        action="store_true",
        help="do not assign another goal after a V4 trip arrives",
    )
    parser.add_argument(
        "--headless-motion",
        type=float,
        metavar="SECONDS",
        help="run the V3 lane motion engine without pygame",
    )
    parser.add_argument(
        "--render-motion",
        type=Path,
        metavar="PNG",
        help="render a V3 lane-motion snapshot with Pillow and exit",
    )
    parser.add_argument(
        "--motion-time",
        type=float,
        default=5.0,
        metavar="SECONDS",
        help="simulation time used by --render-motion (default: 5)",
    )
    parser.add_argument(
        "--v1",
        action="store_true",
        help="open the original V1 grid simulator instead of the V2 layout",
    )
    parser.add_argument(
        "--render-reference",
        type=Path,
        metavar="PNG",
        help="render the V2 layout to a PNG with Pillow and exit",
    )
    parser.add_argument(
        "--render-topology-debug",
        type=Path,
        metavar="PNG",
        help="render safe V4 lanes, nodes, and expanded machine bounds",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.headless_factory is not None or args.render_factory is not None or args.render_factory_debug is not None:
        from warehouse_sim.reference_factory_scenario import create_reference_factory_scenario

        duration = args.headless_factory if args.headless_factory is not None else args.motion_time
        if duration < 0:
            raise SystemExit("factory duration must be zero or greater")
        scenario = create_reference_factory_scenario(
            args.entity_count, seed=args.seed, profile=args.factory_profile
        )
        step = 1.0 / 60.0
        remaining = duration
        while remaining > 1e-12:
            delta = min(step, remaining)
            scenario.engine.update(delta)
            scenario.engine.validate_safety()
            remaining -= delta
        factory = scenario.engine.factory_metrics
        traffic = scenario.engine.traffic.metrics
        print(
            f"entities={len(scenario.engine.entities)} simulated_seconds={duration:.3f} "
            f"tasks_created={factory.tasks_created} tasks_queued={factory.tasks_queued} "
            f"tasks_active={factory.tasks_active} tasks_completed={factory.tasks_completed} "
            f"robot_utilization={factory.robot_utilization:.4f} idle_robots={factory.idle_robot_count} "
            f"productive_utilization={factory.productive_utilization:.4f} "
            f"task_waiting_ratio={factory.task_waiting_ratio:.4f} "
            f"engaged_ratio={factory.engaged_ratio:.4f} "
            f"true_idle_ratio={factory.true_idle_ratio:.4f} "
            f"true_idle_robots={factory.true_idle_robot_count} "
            f"average_true_idle_robots={factory.average_true_idle_robots:.3f} "
            f"min_engaged_after_warmup={factory.min_engaged_robots_after_warmup} "
            f"repositioning_utilization={factory.repositioning_utilization:.4f} "
            f"idle_ratio={factory.idle_ratio:.4f} average_idle_robots={factory.average_idle_robots:.3f} "
            f"average_active_robots={factory.average_active_robots:.3f} "
            f"average_task_cycle_time={factory.average_task_cycle_time:.3f} "
            f"average_pickup_wait={factory.average_pickup_wait:.3f} "
            f"loads_in_transit={factory.loads_in_transit} failed_tasks={factory.failed_tasks} "
            f"direct_handoffs={factory.direct_task_handoffs} parking_returns={factory.parking_returns} "
            f"queued_dispatchable={factory.queued_but_dispatchable} "
            f"queued_blocked={factory.queued_but_blocked} "
            f"blocked_source={factory.assignment_blocked_source_station} "
            f"blocked_destination={factory.assignment_blocked_destination_station} "
            f"blocked_active_limit={factory.assignment_blocked_max_active} "
            f"blocked_no_idle={factory.assignment_blocked_no_idle_robot} "
            f"blocked_no_route={factory.assignment_blocked_no_route} "
            f"source_wait={factory.source_wait_time:.3f} "
            f"destination_wait={factory.destination_wait_time:.3f} "
            f"holding_wait={factory.holding_wait_time:.3f} "
            f"staging_blocks={factory.staging_capacity_blocks} "
            f"late_service_reservations={factory.late_service_reservations} "
            f"collision_count=0 head_on_conflicts={traffic.head_on_conflict_count} "
            f"deadlocks={traffic.deadlock_count} obstacle_penetrations={traffic.obstacle_penetration_count}"
        )
        if args.render_factory is not None or args.render_factory_debug is not None:
            from warehouse_sim.reference_renderer import render_factory_with_pillow

            output = args.render_factory or args.render_factory_debug
            render_factory_with_pillow(
                scenario.layout, scenario.engine, output, debug=args.render_factory_debug is not None
            )
            print(f"factory snapshot rendered: {output} time={duration:.3f}s")
        return 0

    if args.render_topology_debug is not None:
        from warehouse_sim.lane_safety import build_safe_lane_graph
        from warehouse_sim.reference_renderer import render_topology_debug_with_pillow
        from warehouse_sim.reference_scenario import create_reference_layout

        layout = create_reference_layout()
        output = render_topology_debug_with_pillow(
            layout, build_safe_lane_graph(layout), args.render_topology_debug
        )
        print(f"topology debug rendered: {output}")
        return 0

    if args.render_reference is not None:
        from warehouse_sim.reference_renderer import render_with_pillow
        from warehouse_sim.reference_scenario import create_reference_layout

        output = render_with_pillow(create_reference_layout(), args.render_reference)
        print(f"reference layout rendered: {output}")
        return 0

    if args.headless_motion is not None or args.render_motion is not None:
        from warehouse_sim.reference_motion_scenario import create_reference_motion_scenario

        duration = args.headless_motion if args.headless_motion is not None else args.motion_time
        if duration < 0:
            raise SystemExit("motion duration must be zero or greater")
        scenario = create_reference_motion_scenario()
        step = 1.0 / 60.0
        remaining = duration
        while remaining > 1e-12:
            delta = min(step, remaining)
            scenario.engine.update(delta)
            remaining -= delta
        for entity_id, position, state in scenario.engine.snapshot():
            print(f"entity={entity_id} position=({position[0]:.3f},{position[1]:.3f}) state={state.value}")
        if args.render_motion is not None:
            from warehouse_sim.reference_renderer import render_motion_with_pillow

            output = render_motion_with_pillow(scenario.layout, scenario.engine, args.render_motion)
            print(f"motion snapshot rendered: {output} time={duration:.3f}s")
        return 0

    if args.headless_traffic is not None or args.render_traffic is not None:
        from warehouse_sim.reference_traffic_scenario import create_reference_traffic_scenario

        duration = args.headless_traffic if args.headless_traffic is not None else args.motion_time
        if duration < 0:
            raise SystemExit("traffic duration must be zero or greater")
        try:
            scenario = create_reference_traffic_scenario(
                args.entity_count, seed=args.seed, looping=not args.one_shot
            )
        except ValueError as error:
            raise SystemExit(str(error)) from error
        step = 1.0 / 60.0
        remaining = duration
        while remaining > 1e-12:
            delta = min(step, remaining)
            scenario.engine.update(delta)
            scenario.engine.validate_safety()
            remaining -= delta
        metrics = scenario.engine.metrics
        print(
            f"entities={len(scenario.engine.entities)} simulated_seconds={duration:.3f} "
            f"moving={metrics.moving_count} waiting={metrics.waiting_count} "
            f"arrived={metrics.arrived_count} completed_trips={metrics.total_completed_trips} "
            f"conflicts_avoided={metrics.reservation_conflicts} "
            f"waiting_events={metrics.waiting_events} "
            f"deadlock_recoveries={metrics.deadlock_recoveries} "
            f"moving_ratio={metrics.moving_ratio:.4f} average_speed={metrics.average_speed:.3f} "
            f"average_wait={metrics.average_wait_time:.3f} max_wait={metrics.max_wait_time:.3f} "
            f"reroutes={metrics.reroute_count} stops={metrics.stop_count} "
            f"stopped_over_5s={metrics.stopped_over_5s} "
            f"head_on_conflicts={metrics.head_on_conflict_count} "
            f"head_on_prevented={metrics.head_on_conflicts_prevented} "
            f"deadlocks={metrics.deadlock_count} deadlocks_prevented={metrics.deadlock_prevented_count} "
            f"indefinite_wait={metrics.indefinite_wait_count} "
            f"throughput_per_min={metrics.throughput_per_minute:.3f} collision_count=0"
            f" obstacle_penetrations={metrics.obstacle_penetration_count}"
        )
        if args.render_traffic is not None:
            from warehouse_sim.reference_renderer import render_motion_with_pillow

            output = render_motion_with_pillow(scenario.layout, scenario.engine, args.render_traffic)
            print(f"traffic snapshot rendered: {output} time={duration:.3f}s")
        return 0

    if args.headless_ticks is not None:
        simulation = create_default_simulation()
        if args.headless_ticks < 0:
            raise SystemExit("--headless-ticks must be zero or greater")
        for _ in range(args.headless_ticks):
            if simulation.all_arrived:
                break
            simulation.tick()
        print(f"ticks={simulation.tick_count} all_arrived={simulation.all_arrived}")
        for robot in simulation.robots:
            print(
                f"robot={robot.id} position={robot.position} "
                f"goal={robot.goal} state={robot.state.value}"
            )
        return 0 if simulation.all_arrived else 1

    try:
        if args.v1:
            from warehouse_sim.ui import WarehouseUI
            simulation = create_default_simulation()
            application = WarehouseUI(simulation)
        elif args.traffic_demo:
            from warehouse_sim.reference_renderer import ReferenceLayoutUI
            from warehouse_sim.reference_traffic_scenario import create_reference_traffic_scenario
            try:
                scenario = create_reference_traffic_scenario(
                    args.entity_count, seed=args.seed, looping=not args.one_shot
                )
            except ValueError as error:
                raise SystemExit(str(error)) from error
            application = ReferenceLayoutUI(scenario.layout, scenario.graph, scenario.engine)
        else:
            from warehouse_sim.reference_factory_scenario import create_reference_factory_scenario
            from warehouse_sim.reference_renderer import ReferenceLayoutUI

            scenario = create_reference_factory_scenario(
                args.entity_count, seed=args.seed, profile=args.factory_profile
            )
            application = ReferenceLayoutUI(scenario.layout, scenario.graph, scenario.engine)
    except ModuleNotFoundError as error:
        if error.name == "pygame":
            print("pygame is not installed. Run: python -m pip install -r requirements.txt")
            return 1
        raise
    application.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
