# Canonical Glossary

| Term | Meaning | Canonical code | Allowed abbreviation | Do not introduce | Owner |
|---|---|---|---|---|---|
| Robot | V1 grid actor | `Robot`, `robot_id` | none | bot/vehicle | `robot.py` |
| Entity | Lane-moving Robot representation | `LaneMobileEntity`, `entity_id` | entity | AMR class duplicate | `motion.py` |
| Lane node | Canonical route coordinate | `LaneNode`, `node_id` | node | waypoint duplicate | `lane_graph.py` |
| Lane edge | Traversable graph segment | `LaneEdge`, `edge_id` | edge | rail link duplicate | `lane_graph.py` |
| Route | Ordered LaneNode IDs | `route`, `route_node_ids` | route | path object duplicate | `motion.py` |
| Station | V2 visual primitive | `Station` | none | WorkStation synonym | `facility_layout.py` |
| Work station | Factory service/staging mapping | `WorkStation`, `station_id` | station in factory context | dock class duplicate | `task_manager.py` |
| Material task | Robot executable transport leg | `MaterialTask`, `task_id` | task | WarehouseTask class | `task_manager.py` |
| Material load | One task's custody state | `MaterialLoad`, `load_id` | load/cargo | inventory source of truth | `task_manager.py` |
| Warehouse request | Warehouse business move requirement | `WarehouseRequest`, `request_id` | WR | TransportRequest synonym | `warehouse.py` |
| Inventory item | Warehouse item location source of truth | `InventoryItem`, `item_id` | item | StockItem/WarehouseItem | `warehouse.py` |
| Inventory location | Receiving/storage/staging container | `InventoryLocation` | location/rack | `StorageLocation` class | `warehouse.py` |
| Inbound order | Scheduled receiving batch | `InboundOrder`, `inbound_order_id` | IB | receipt job | `warehouse.py` |
| Outbound order | SKU demand and shipment lifecycle | `OutboundOrder`, `outbound_order_id` | SO | sales task | `warehouse.py` |
| Putaway | Receiving-to-storage work | `WarehouseRequestType.PUTAWAY` | PUT | stocking mission | `warehouse.py` |
| Picking | Storage-to-staging work | `WarehouseRequestType.PICKING` | PICK | retrieval mission | `warehouse.py` |
| Shipping | Boundary event after READY | `OutboundState.SHIPPED` | SHIP | Robot shipment task | `warehouse.py` |
| Work order | Production target | `WorkOrder`, `work_order_id` | WO | production job duplicate | `production.py` |
| Material unit | Production lot/location source of truth | `MaterialUnit`, `material_unit_id` | material | InventoryItem synonym | `production.py` |
| Transport request | Production business move requirement | `TransportRequest`, `transport_request_id` | TR | WarehouseRequest synonym | `production.py` |
| Production machine | Synthetic process state | `ProductionMachine` | machine | video-confirmed machinery | `production.py` |
| Material buffer | Finite production location | `MaterialBuffer` | buffer | InventoryLocation synonym | `production.py` |
| Mission | Business reason for movement | `mission` | SUPPLY/WIP/QC/OUT, PUT/PICK | combined state enum | view modules |
| Operational state | Physical measured activity | `PhysicalActivity` | state | mission-state fusion | `factory.py` |
| Cargo | Load actually owned by Robot | `has_cargo` | cargo | decorative box | view modules |

`Robot` and `LaneMobileEntity` are compatibility concepts from V1 and V3+, not interchangeable classes.
`Station` and `WorkStation` likewise have visual-layout versus execution-resource responsibilities.
