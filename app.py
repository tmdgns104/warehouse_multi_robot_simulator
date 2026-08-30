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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.render_reference is not None:
        from warehouse_sim.reference_renderer import render_with_pillow
        from warehouse_sim.reference_scenario import create_reference_layout

        output = render_with_pillow(create_reference_layout(), args.render_reference)
        print(f"reference layout rendered: {output}")
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
        else:
            from warehouse_sim.reference_renderer import ReferenceLayoutUI
            from warehouse_sim.reference_scenario import create_reference_layout
            application = ReferenceLayoutUI(create_reference_layout())
    except ModuleNotFoundError as error:
        if error.name == "pygame":
            print("pygame is not installed. Run: python -m pip install -r requirements.txt")
            return 1
        raise
    application.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
