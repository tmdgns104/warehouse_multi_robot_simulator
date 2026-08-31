# State Machine Contract

## MaterialTask

```text
QUEUED → ASSIGNED → MOVING_TO_SOURCE
MOVING_TO_SOURCE → WAITING_FOR_SOURCE or PICKING or FAILED
WAITING_FOR_SOURCE → PICKING or FAILED
PICKING → MOVING_TO_DESTINATION or FAILED
MOVING_TO_DESTINATION → WAITING_FOR_DESTINATION or DROPPING or FAILED
WAITING_FOR_DESTINATION → DROPPING or FAILED
DROPPING → COMPLETED or FAILED
QUEUED → CANCELLED
COMPLETED/FAILED/CANCELLED are terminal
```

`FactoryTaskManager._TRANSITIONS` is authoritative. Assignment records Robot/time; completion records
`completed_time` and every transition appends `TaskEvent`.

## MaterialLoad custody

`AT_SOURCE → RESERVED → ON_ROBOT → AT_DESTINATION`. Pickup requires task PICKING, assigned Robot and
RESERVED load. Drop requires task DROPPING and matching owner. ON_ROBOT implies one non-null owner;
one Robot cannot own two loads.

## Warehouse lifecycle

```text
InventoryItem:
EXPECTED → WAITING_PUTAWAY → IN_TRANSIT → STORED
STORED → RESERVED_FOR_PICK → IN_TRANSIT → OUTBOUND_STAGING → SHIPPED

WarehouseRequest: OPEN → ASSIGNED → IN_PROGRESS → COMPLETED
InboundOrder: PLANNED ↔ WAITING_DOCK → PUTAWAY_IN_PROGRESS → COMPLETED
OutboundOrder: OPEN ↔ WAITING_INVENTORY → PICKING → READY_TO_SHIP → SHIPPED
```

Pickup atomically removes the Item from source contents, clears `current_location`, and sets
`IN_TRANSIT`. Drop consumes destination capacity reservation, adds contents and sets location/state.
Shipping waits five simulated seconds after READY, removes staging contents, sets location `None`,
then marks Item and order SHIPPED.

## Production lifecycle

```text
WorkOrder: PLANNED → RUNNING → COMPLETED at target quantity
TransportRequest: OPEN → ASSIGNED → IN_PROGRESS → COMPLETED
Machine: WAITING_MATERIAL → PROCESSING → WAITING_UNLOAD → WAITING_MATERIAL
MaterialUnit: AVAILABLE → RESERVED → IN_TRANSIT → AT_PROCESS → PROCESSING
              → WAITING_TRANSFER → ... → SHIPPED
```

WAITING_MATERIAL accumulates starvation; WAITING_UNLOAD accumulates blocking.

## Robot execution and physical activity

`RobotWorkState` controls staging/service phase. `PhysicalActivity` is measured from position delta:
ACTUALLY_MOVING, SERVICING, TRAFFIC_WAIT, RESOURCE_WAIT, HOLDING, TRUE_IDLE. Warehouse display
translates without changing state: no task=`AVAILABLE`; source work=`TO PICKUP`/`PICKING ITEM`;
owned load=`CARRYING`; destination service=`DROPPING ITEM`; wait conditions remain explicit.

## Motion

`IDLE → PLANNING → MOVING → ARRIVED`; reservation denial produces WAITING; failed planning produces
NO_ROUTE. `route_index`, `current_edge`, and `progress` are the continuous-motion source of truth.
