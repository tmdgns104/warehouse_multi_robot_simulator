# Deterministic Scenario Specification

## Shared factory topology

Default `entity_count=16`, `seed=1234`. Eight `WorkStation`s use these service nodes:

| Station | Service node |
|---|---|
| IN_A | `lane_320_219` |
| PROC_A | `lane_405_343` |
| QC_A | `lane_625_555` |
| OUT_A | `lane_870_219` |
| IN_B | `lane_320_555` |
| PROC_B | `lane_494_343` |
| BUFFER_B | `lane_625_190` |
| OUT_B | `lane_870_555` |

Each station has three deterministic staging nodes selected during construction. Preserve the
selection algorithm (nearest unused reachable non-hub nodes), not merely copied IDs if graph changes.

## Warehouse scenario

Factory config: `queue_target=0`, `max_active_tasks=entity_count`, `engagement_warmup=10`,
`balance_workload=False`, `park_when_empty=False`.

Locations:

| ID | WorkStation | Capacity | Compatible SKU |
|---|---|---:|---|
| RECV_A / RECV_B | IN_A / IN_B | 8 each | unrestricted |
| RACK-A01 | PROC_A | 4 | A |
| RACK-A02 | QC_A | 4 | A,C |
| RACK-A03 | PROC_A | 4 | A,C |
| RACK-B01 | PROC_B | 4 | B |
| RACK-B02 | BUFFER_B | 4 | B,C |
| RACK-B03 | PROC_B | 4 | B,C |
| OUT_STAGE_A / B | OUT_A / OUT_B | 8 each | unrestricted |

Inbound schedule: IB-001 t=0 A×4→RECV_A; IB-002 t=30 B×4→RECV_B; IB-003 t=60
C×4→RECV_A; IB-004 t=120 A×3→RECV_A; IB-005 t=180 B,C,C→RECV_B. Item IDs
are sequential ITEM-001..018 and lots `LOT-<SKU suffix>-<item sequence:03d>`.

Outbound schedule: SO-001 t=90 A×2 due190→OUT_STAGE_A; SO-002 t=150 B×2+C×1
due250→OUT_STAGE_B; SO-003 t=210 A×2+C×1 due310→OUT_STAGE_A.

300-second baseline: 18 arrived, 16 put away, inventory 9/24, three outbound orders created,
one shipped, two items shipped, staging 3, integrity errors 0; actual motion ratio 0.3004;
collision/head-on/deadlock/obstacle penetration all zero.

## Production scenario

WO-A PRODUCT-A target10 and WO-B PRODUCT-B target10. Twenty MaterialUnits start in IN_A/IN_B.
Flows: `IN_A→PROC_A→QC_A→OUT_A`, `IN_B→PROC_B→BUFFER_B→OUT_B`. Buffer capacities:
input/output 10, processing 3. Machine processing times 12/6/12/6 seconds.

300-second baseline: production 6/20, requests 22 created/20 completed, average lead 34.035s,
on-time 0.9000, WIP2, buffer 12/52, all safety/inventory errors zero.

## Geometry disclaimer

Layout is reference-derived; production and warehouse meanings are synthetic. Never state that the
video proves PROC/QC/Rack semantics.
