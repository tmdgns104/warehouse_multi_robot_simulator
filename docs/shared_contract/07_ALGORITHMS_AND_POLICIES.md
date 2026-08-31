# Algorithms and Deterministic Policies

## Lane construction and routing

1. Create candidate Manhattan segments from reference-derived aisle coordinates.
2. Subtract Machine/Station rectangles expanded by `OBSTACLE_CLEARANCE=7.0`.
3. Canonicalize/snap safe endpoints and build `LaneGraph`.
4. Renderer uses `SafeLaneGraph.network_segments()` for drivable rails; visual-only segments differ.
5. `graph_astar` uses Euclidean heuristic. Traffic A* adds hard/soft reservation, congestion and zone
   capacity cost; rerouting has cooldown/improvement thresholds.

## Traffic safety

- Exclusive target-node and narrow-edge reservation.
- Deny same-node, same-edge and reverse-edge head-on entry.
- Longest wait then stable order/ID determines priority.
- Four-edge predictive soft reservation horizon with expiry.
- Wait-for cycle detection prevents deadlock-producing grants.
- All business movement must use TrafficMotionEngine; never teleport a Robot.

## Factory assignment

Queued task order is `(-priority, created_time, id)`. With `balance_workload=False`, first reachable
task is assigned. BUSY profiles may consider staging availability, link WIP and queue pressure.
Assignment is distinct from late Station service reservation. Source/destination staging holds
waiting Robots away from service nodes. Production/Warehouse use `queue_target=0`,
`max_active_tasks=entity_count`, `park_when_empty=False`.

## Warehouse policies

- Putaway candidate: SKU-compatible, `free>0`; prefer location already containing same SKU; tie by ID.
- Reserve destination before creating task; no reservation means no request.
- Outbound allocation: only unallocated STORED items; FIFO `(stored_time, item.id)`.
- Insufficient quantity: no partial/fake allocation; order `WAITING_INVENTORY`.
- Shipping: all allocated items in OUTBOUND_STAGING, then five simulated seconds.

## Production policies

- Production state alone creates tasks in production mode.
- Starved supply is HIGH/CRITICAL; downstream WIP/QC NORMAL; outbound LOW.
- Destination MaterialBuffer reserves inbound capacity at request creation.
- Processing times: PROC_A/PROC_B 12s; QC_A/BUFFER_B 6s; QC is deterministic PASS.

## Determinism

All timers use simulation delta, never wall clock. Equal choices use stable IDs/orders. Random scenario
choices use the passed seed. Rendering must not consume random values or update engines.
