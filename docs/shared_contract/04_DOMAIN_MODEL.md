# Domain Model Contract

`R` means required constructor argument; `factory` means an independent empty collection.

## Warehouse (`warehouse.py`)

### `InventoryItem` (mutable dataclass)

| Field | Type | Default |
|---|---|---|
| `id` | `str` | R |
| `sku` | `str` | R |
| `lot_id` | `str` | R |
| `inbound_order_id` | `str` | R |
| `arrival_time` | `float` | R |
| `state` | `InventoryState` | `EXPECTED` |
| `current_location` | `str | None` | `None` |
| `outbound_order_id` | `str | None` | `None` |
| `active_request_id` | `str | None` | `None` |
| `stored_time` | `float | None` | `None` |

`current_location` is the warehouse location source of truth. `IN_TRANSIT` and `SHIPPED` imply
no location membership. Long-term location must not be stored in `MaterialLoad`.

### `InventoryLocation` (mutable dataclass)

Fields: `id: str`, `station_id: str`, `capacity: int` (R),
`compatible_skus: tuple[str,...]=()`, `contents: list[str]=factory`,
`reservations: set[str]=factory`. Derived `occupied=len(contents)` and
`free=capacity-occupied-len(reservations)`. `reserve()` prevents overbooking; `receive()` requires
the request reservation. Do not create a second `StorageLocation` class.

### Orders and request

| Class | Exact fields |
|---|---|
| `InboundOrder` | `id`, `supplier`, `arrival_time`, `item_ids`, `state=PLANNED`, `received_time=None`, `completed_time=None` |
| `OutboundOrder` | `id`, `customer`, `lines`, `created_time`, `due_time`, `state=OPEN`, `allocated_items=factory`, `ready_time=None`, `shipped_time=None` |
| `WarehouseRequest` | `id`, `request_type`, `item_id`, `source`, `destination`, `created_time`, `inbound_order_id=None`, `outbound_order_id=None`, `state=OPEN`, `task_id=None`, `assigned_time=None`, `completed_time=None` |
| `WarehouseEvent` frozen | `time`, `event`, `item_id=None`, `robot_id=None`, `request_id=None`, `order_id=None`, `location=None` |

`WarehouseMetrics` is frozen with fields, in order: `inbound_items_arrived`, `putaway_completed`,
`average_putaway_time`, `inventory_total`, `inventory_capacity`, `inventory_occupancy_ratio`,
`outbound_orders_created`, `outbound_orders_shipped`, `outbound_items_shipped`,
`average_order_cycle_time`, `average_pick_time`, `backordered_items`, `receiving_wait_count`,
`outbound_staging_count`, `inventory_integrity_errors`.

### Documentation conflict

`InboundOrder.dock` is currently assigned dynamically in `WarehouseEngine._build_schedule()` but is
not a declared dataclass field. Reimplementations must preserve current behavior (`order.dock`) for
compatibility. Do not silently rename or repair it; a future approved migration should declare it.

## Production (`production.py`)

| Class | Exact fields/defaults |
|---|---|
| `WorkOrder` | `id`, `product_id`, `target_quantity`, `priority=NORMAL`, `created_time=0.0`, `due_time=300.0`, `completed_quantity=0`, `state=PLANNED` |
| `MaterialUnit` | `id`, `material_id`, `lot_id`, `quantity`, `work_order_id`, `current_location`, `state=AVAILABLE`, `active_request_id=None` |
| `MaterialTraceEvent` frozen | `time`, `material_unit_id`, `event`, `from_location`, `to_location`, `robot_id`, `transport_request_id`, `material_task_id`, `work_order_id` |
| `MaterialBuffer` | `id`, `station_id`, `capacity`, `contents=factory`, `inbound_reservations=factory`, `maximum_occupancy=0` |
| `ProductionMachine` | `id`, `station_id`, `next_station_id`, `processing_time`, `request_type`, `state=WAITING_MATERIAL`, `current_material_id=None`, `remaining_time=0.0`, `starvation_time=0.0`, `blocking_time=0.0`, `completed_cycles=0` |
| `TransportRequest` | `id`, `request_type`, `work_order_id`, `material_unit_id`, `source_location`, `destination_location`, `priority`, `reason`, `requested_time`, `due_time`, `state=OPEN`, `material_task_id=None`, `assigned_time=None`, `completed_time=None` |

`MaterialUnit.current_location` is the production source of truth. `MaterialLoad` represents only a
single Robot transport leg. `ProductionMetrics` fields are the exact names exposed by the
`production_metrics` property; do not shorten metric names.

## Robot execution (`task_manager.py`, `factory.py`)

| Class | Exact fields/defaults |
|---|---|
| `WorkStation` frozen | `id`, `role`, `facility_id`, `service_node_id`, `staging_node_ids=()` |
| `MaterialTask` | `id`, `source_station_id`, `destination_station_id`, `load_id`, `priority=1`, `state=QUEUED`, `assigned_robot_id=None`, `created_time=0.0`, `assigned_time=None`, `pickup_time=None`, `completed_time=None`, `transport_request_id=None` |
| `MaterialLoad` | `id`, `state`, `current_station_id`, `carried_by_robot_id`, `task_id` |
| `TaskEvent` frozen | `time`, `task_id`, `event`, `robot_id=None` |
| `FactoryConfig` frozen | `pickup_duration=2.0`, `drop_duration=2.0`, `queue_target=6`, `max_active_tasks=10`, `engagement_warmup=10.0`, `balance_workload=False`, `park_when_empty=True` |

Exactly one `MaterialLoad` belongs to one `MaterialTask`; task/load IDs and links must agree. A Robot
may own at most one ON_ROBOT load.

## Layout, lane and motion

- `LaneNode` frozen: `id`, `x`, `y`, `node_type='lane'`, `metadata=factory`.
- `LaneEdge` frozen: `id`, `source`, `target`, `length`, `bidirectional=True`, `metadata=factory`;
  length must be positive and endpoints distinct.
- `LaneTraversal` frozen: `edge`, `source`, `target`.
- `LaneMobileEntity`: `id`, `current_node`, `goal_node`, `speed`, then visual, route/progress,
  waiting, speed coordination and reroute metric fields exactly as in `motion.py`.
- `FacilityLayout`: `design_width`, `design_height`, tuples `zones`, `machines`, `stations`, `network`,
  `entities`; geometry validates bounds and IDs.

## Read-only projections

- `RobotMissionView` and `MissionCount` are frozen production views.
- `WarehouseRobotView` is frozen: `robot_id`, `operational_state`, `mission=None`,
  `phase='AVAILABLE'`, Item/SKU/Lot/source/destination/order/request/task fields, `has_cargo=False`,
  `route_node_ids=()`, source/destination node IDs.
- `WarehouseBoxView` frozen: `item_id`, `label`, `sku`, `lot_id`, `location`.

Views never mutate engines and never invent cargo or missions.

## Exact enum members

| Enum | Members in order |
|---|---|
| `InventoryState` | `EXPECTED`, `WAITING_PUTAWAY`, `IN_TRANSIT`, `STORED`, `RESERVED_FOR_PICK`, `OUTBOUND_STAGING`, `SHIPPED` |
| `WarehouseRequestType` | `PUTAWAY`, `PICKING` |
| `WarehouseRequestState` | `OPEN`, `ASSIGNED`, `IN_PROGRESS`, `COMPLETED` |
| `InboundState` | `PLANNED`, `WAITING_DOCK`, `PUTAWAY_IN_PROGRESS`, `COMPLETED` |
| `OutboundState` | `OPEN`, `WAITING_INVENTORY`, `PICKING`, `READY_TO_SHIP`, `SHIPPED` |
| `WorkOrderState` | `PLANNED`, `RUNNING`, `COMPLETED` |
| `MaterialUnitState` | `AVAILABLE`, `RESERVED`, `IN_TRANSIT`, `AT_PROCESS`, `PROCESSING`, `WAITING_TRANSFER`, `FINISHED`, `SHIPPED` |
| `MachineState` | `IDLE`, `WAITING_MATERIAL`, `PROCESSING`, `WAITING_UNLOAD` |
| `TransportRequestType` | `INBOUND_MOVE`, `LINE_SUPPLY`, `WIP_TRANSFER`, `QC_TRANSFER`, `OUTBOUND_MOVE` |
| `TransportPriority` | `LOW=1`, `NORMAL=2`, `HIGH=3`, `CRITICAL=4` |
| `TransportRequestState` | `OPEN`, `ASSIGNED`, `IN_PROGRESS`, `COMPLETED` |
| `TaskState` | `QUEUED`, `ASSIGNED`, `MOVING_TO_SOURCE`, `WAITING_FOR_SOURCE`, `PICKING`, `MOVING_TO_DESTINATION`, `WAITING_FOR_DESTINATION`, `DROPPING`, `COMPLETED`, `FAILED`, `CANCELLED` |
| `LoadState` | `AT_SOURCE`, `RESERVED`, `ON_ROBOT`, `AT_DESTINATION` |
| `RobotWorkState` | `IDLE`, `TO_PICKUP`, `TO_SOURCE_STAGING`, `WAITING_SOURCE`, `PICKING`, `CARRYING`, `TO_DESTINATION_STAGING`, `WAITING_DESTINATION`, `DROPPING`, `RETURNING`, `TASK_HOLDING` |
| `PhysicalActivity` | `ACTUALLY_MOVING`, `SERVICING`, `TRAFFIC_WAIT`, `RESOURCE_WAIT`, `HOLDING`, `TRUE_IDLE` |
| `MotionState` | `IDLE`, `PLANNING`, `MOVING`, `WAITING`, `ARRIVED`, `NO_ROUTE` |
| `EntityShape` | `RECTANGLE`, `CIRCLE`, `DIAMOND` |
| `FactoryProfile` | `LIGHT`, `NORMAL`, `BUSY`, `STRESS` |
