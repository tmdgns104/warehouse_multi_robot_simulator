# TASK-009F - V5.6 Warehouse Inventory Lifecycle

## Status

IMPLEMENTED / AUTOMATED VERIFICATION PASS / HUMAN WAREHOUSE LIFECYCLE VERIFICATION REQUIRED

## Scope

별도 synthetic Warehouse Demo에서 scheduled inbound, physical item, finite receiving/storage,
putaway, inventory, outbound order, FIFO allocation, picking, staging과 shipping을 구현한다.
V5.4/V5.5 Production Demo 및 기존 Factory/Traffic lifecycle은 보존한다.

## Architecture

- `warehouse.py`: orders, items, locations, requests, lifecycle, KPI and integrity
- `reference_warehouse_scenario.py`: deterministic reference-layout scenario
- `warehouse_view.py`: read-only box and Robot mission projections
- existing MaterialTask/MaterialLoad/FactoryEngine: Robot pickup/drop execution
- existing TrafficController/SafeLaneGraph: motion safety

InventoryItem.current_location이 위치 source of truth다. MaterialLoad는 in-transit custody만
표현한다. Putaway는 compatible location, same SKU preference, stable ID 순서로 선택하고,
Outbound allocation은 stored timestamp와 item ID FIFO다.

## Acceptance

16 robots, seed 1234, 300 seconds:

- 18 arrived, 16 put away
- 6 storage locations, 9/24 stored/reserved
- 3 outbound orders, 1 shipped, 2 items shipped, staging 3
- PUTAWAY and PICKING naturally overlap
- all inventory integrity and traffic safety violations zero

## Evidence

- `evidence/v5_6_warehouse_overview.png`
- `evidence/v5_6_inbound_putaway.png`
- `evidence/v5_6_inventory_storage.png`
- `evidence/v5_6_outbound_picking.png`
- `evidence/v5_6_warehouse_debug.png`
- `evidence/v5_6_item_trace.txt`
- `evidence/v5_6_warehouse_stress.txt`

Human PASS 전 commit/push하지 않는다. TASK-009G Battery/Charging과 TASK-010/V6는 미시작이다.
