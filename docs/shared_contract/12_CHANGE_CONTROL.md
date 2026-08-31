# Change Control

## Contract-changing modifications

Human approval and coordinated updates are required for:

- canonical class/module/field/function/enum names;
- public signatures/defaults or identifier formats;
- source-of-truth ownership;
- state transitions and terminal states;
- capacity, allocation, routing, dispatch or safety policies;
- deterministic schedules/baseline outputs;
- dependency direction or new external services.

## Required change sequence

1. Record reason, scope, compatibility and migration decision in `DECISIONS.md` when architectural.
2. Update implementation and regression tests together.
3. Update every affected shared-contract document in the same change.
4. Regenerate deterministic evidence and report numeric deltas.
5. Preserve compatibility or explicitly document breakage and migration.
6. Obtain Human visual verification for GUI contracts before COMPLETE.

## Additive changes

New optional view fields or CLI aliases may be additive only when existing call syntax and semantics
remain intact. A synonym must not become a second canonical concept.

## Known documentation conflicts at extraction

1. `InboundOrder.dock` is a dynamic attribute, not a dataclass field.
2. `MaterialTask.transport_request_id` also carries `WarehouseRequest.id`.
3. `create_reference_warehouse_scenario` currently lacks type annotations/return annotation.
4. TASK-009F-A files were uncommitted while this pack was extracted; baseline commit is V5.6 and
   V5.6.1 is a Human-gated working-tree extension.

Do not automatically fix these while reconstructing. Preserve compatibility, raise a documented
proposal, add migration tests, and wait for approval.
