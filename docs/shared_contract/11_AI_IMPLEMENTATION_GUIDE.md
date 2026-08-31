# AI Implementation Guide

## Reconstruction order

1. Implement V1 map, Robot, Manhattan A*, collision resolution and tests.
2. Implement FacilityLayout and backend-neutral DrawCommand plan.
3. Build safe LaneGraph, graph A*, continuous LaneMobileEntity motion.
4. Add TrafficController and TrafficMotionEngine reservations/safety.
5. Add MaterialTask/MaterialLoad and FactoryEngine staging/service lifecycle.
6. Compose ProductionEngine; do not merge it into FactoryEngine.
7. Compose WarehouseEngine separately; do not reuse MaterialUnit as InventoryItem.
8. Add read-only mission/warehouse projections.
9. Add Pillow evidence then pygame UI from the same state.
10. Reproduce deterministic scenarios and acceptance numbers before extending scope.

## Required discipline

- Copy canonical names/signatures/enums exactly; do not beautify them.
- Search this pack before creating a class. If responsibility exists, extend through composition.
- Use `MaterialTask` for Robot execution in both production and warehouse domains.
- Keep WarehouseRequest and TransportRequest distinct business types.
- Do not let business engines reserve graph resources or directly move Robots.
- Do not let renderers infer fake boxes, cargo, tasks or inventory.
- Preserve V1 regression modules and all CLI modes.
- Battery/charging, V6 fleet optimization, ROS2/Gazebo/Nav2 are out of current contract.

## Completion checklist

- Project tree matches `03`.
- Every dataclass field/default and enum matches `04`.
- Public calls match `05`; state transitions match `06`.
- Policies/default schedules match `07` and `08`.
- UI hierarchy and selection match `09`.
- Compile, complete pytest, headless baselines, integrity and visual evidence pass.
- Document any unavoidable mismatch as `DOCUMENTATION CONFLICT`; never silently invent compatibility.
