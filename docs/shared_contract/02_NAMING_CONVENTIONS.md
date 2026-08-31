# Naming Conventions

- Modules/functions/methods/variables: `snake_case`.
- Classes/dataclasses/enums: `PascalCase`.
- Enum members/constants: `UPPER_SNAKE_CASE`.
- Scenario factory: `create_reference_<domain>_scenario(...)`.
- Immutable projections/events/metrics use `@dataclass(frozen=True)` where current code does.
- Collections use plural responsibility names: `entities`, `items`, `requests`, `tasks`, `stations`,
  `buffers`, `machines`, `contents`, `reservations`.
- Boolean projection: `has_cargo`; policy predicates use `_has_*`, `_at_*`, `_engaged`.
- Validation: `validate_safety`, `validate_*_integrity`, `validate_lane_graph_safety`.
- Metric fields are explicit units/meaning: `average_putaway_time`, `actual_motion_ratio`.

## Canonical identifiers

| Concept | Identifier |
|---|---|
| Robot | `robot_id` |
| Lane entity | `entity_id` or `entity.id` |
| Lane node/edge | `node_id` / `edge_id` |
| Item | `item_id` |
| Production material | `material_unit_id` or local `material_id` |
| Task | `task_id` |
| Warehouse request | `request_id`; stored in `MaterialTask.transport_request_id` for compatibility |
| Production request | `transport_request_id` |
| Inbound/outbound/work order | `inbound_order_id` / `outbound_order_id` / `work_order_id` |
| Station/load/lot | `station_id` / `load_id` / `lot_id` |
| SKU | `sku` |

Compatibility note: `MaterialTask.transport_request_id` links both `TransportRequest.id` and
`WarehouseRequest.id`; do not add `warehouse_request_id` without an approved migration.
