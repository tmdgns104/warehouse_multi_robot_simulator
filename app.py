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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    simulation = create_default_simulation()
    if args.headless_ticks is not None:
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
        from warehouse_sim.ui import WarehouseUI
    except ModuleNotFoundError as error:
        if error.name == "pygame":
            print("pygame is not installed. Run: python -m pip install -r requirements.txt")
            return 1
        raise
    WarehouseUI(simulation).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
