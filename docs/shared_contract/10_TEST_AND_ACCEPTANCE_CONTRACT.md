# Test and Acceptance Contract

Run from repository root:

```bash
python3 -m compileall -q app.py src tests
python3 -m pytest -q
python3 app.py --headless-warehouse 300 --entities 16 --seed 1234
python3 app.py --headless-production 300 --entities 16 --seed 1234
```

Current extracted suite: 129 tests including uncommitted TASK-009F-A tests; committed V5.6 baseline
contains 126. Reimplementation must pass all tests present in its checkout, not hard-code the count.

## Mandatory invariants

- Buffer/location occupancy in `[0, capacity]`; reservations prevent overbooking.
- Item/material appears in at most one container or one Robot custody.
- IN_TRANSIT has no fixed current_location; STORED has a valid storage membership.
- SHIPPED has no location and is absent from every BoxView.
- Pick requires outbound allocation; no fake inventory on shortage.
- ON_ROBOT load has exactly one owner; Robot owns at most one load.
- Render before/after snapshots are identical.
- Same seed produces equal metrics/events.
- unsafe nodes/edges, collision, head-on conflict, deadlock and obstacle penetration are zero.

## Scenario acceptance

Warehouse exact business baseline is defined in `08_SCENARIO_SPEC.md`; lifecycle must visibly include
arrival, Putaway pickup/cargo/drop, stored accumulation, FIFO allocation, Picking, staging, READY and
Shipping. Production exact baseline must remain 6/20 and 22/20 at 300 seconds.

## Test ownership

- V1 map/planner/collision/simulation: `test_planner.py`, `test_collision.py`, `test_simulation.py`.
- Layout/lane/safety/motion/traffic: corresponding `test_reference_layout.py`, `test_lane_*`,
  `test_motion.py`, `test_traffic.py`, `test_predictive_traffic.py`.
- Factory/task/custody: `test_factory.py`.
- Production/mission: `test_production.py`, `test_mission_view.py`.
- Warehouse/domain/view: `test_warehouse.py`.

Human gates remain mandatory for pygame visual correctness. Automated PNG success is not a Human PASS.
