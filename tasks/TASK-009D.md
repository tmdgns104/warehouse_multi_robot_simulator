# TASK-009D - V5.4 Realistic Production & Material Logistics

## Status

IMPLEMENTED / AUTOMATED VERIFICATION PASS / HUMAN REALISTIC FACTORY VERIFICATION REQUIRED

Human GUI verification 전에는 COMPLETE, commit 또는 push로 처리하지 않는다.

## Scope

Reference-derived V4.3 layout 위에 synthetic manufacturing business semantics를 제공한다.
영상 속 실제 설비 종류를 확정하지 않는다. V5.3 dispatch, staging, late reservation, motion KPI,
SafeLaneGraph와 TrafficController는 그대로 사용한다.

## Domain Flow

```text
WorkOrder -> MaterialUnit -> Machine/Buffer demand -> TransportRequest
          -> MaterialTask -> Robot pickup/move/drop -> inventory/production update
```

- WO-A / PRODUCT-A: IN_A -> PROC_A -> QC_A -> OUT_A
- WO-B / PRODUCT-B: IN_B -> PROC_B -> BUFFER_B -> OUT_B
- MaterialUnit은 장기 inventory/lot source of truth다.
- MaterialLoad는 각 TransportRequest의 실행 task가 운반하는 한 leg의 load다.
- Destination buffer capacity는 request 생성 시 inbound reservation으로 확보한다.
- QC는 deterministic PASS로 모델링한다.

## Acceptance Result

16 robots, seed 1234, 300 simulated seconds:

- WorkOrders started; 6/20 finished products shipped
- LINE_SUPPLY, WIP_TRANSFER, QC_TRANSFER, OUTBOUND_MOVE observed
- 22 requests created, 20 completed
- average transport lead time 34.035s; on-time rate 90%
- machine processing, starvation and blocking observed
- buffer capacity/inventory violations 0
- collisions/head-on/deadlocks/obstacle penetrations 0
- deterministic replay covered by tests
- V1 through V5.3 regression plus V5.4 tests: 102 PASS

## Evidence

- `evidence/v5_4_realistic_factory.png`
- `evidence/v5_4_production_debug.png`
- `evidence/v5_4_material_trace.txt`
- `evidence/v5_4_factory_stress.txt`

## Human Gate

Run `python3 app.py --production-demo` and verify WorkOrder progress, changing machine state,
production-derived Robot task reason/lot/route, changing buffer occupancy, finished count, and
collision-free motion. TASK-010 / V6 is out of scope.
