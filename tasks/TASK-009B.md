# TASK-009B - V5.2 Full Fleet Engagement with Staging Queue

Status: IMPLEMENTED / AUTOMATED PASS / HUMAN FULL FLEET ENGAGEMENT VERIFICATION REQUIRED

## Problem

V5.1 inferred station ownership from long movement phases. A robot travelling toward a
station therefore prevented another real task from being assigned, leaving queued work
while many robots were truly idle. Destination acquisition at pickup completion also
kept a robot at the source when the destination was busy.

## Architecture

- A `WorkStation` has one capacity-1 service node and two obstacle-safe staging nodes.
- Real tasks are assigned before service capacity is available.
- Source and destination have deterministic priority staging queues.
- `station_reservations` and `staging_reservations` explicitly represent ownership.
- Service is reserved only when a staged robot receives entry permission.
- A robot without staging capacity remains `TASK_HOLDING` on a safe graph node.
- A blocked approach backs off to its unique remote holding node before indefinite wait.
- BUSY permits full assignment independently of physical service capacity.
- Completion replenishes work and directly hands off a real queued task before parking.

## State Meaning

`TO_SOURCE_STAGING`, `WAITING_SOURCE`, `TO_PICKUP`, `PICKING`,
`TO_DEST_STAGING`, `WAITING_DEST`, `CARRYING`, `DROPPING`, and
`TASK_HOLDING` all require exactly one assigned nonterminal `MaterialTask`.
Only a robot without such a task is `TRUE_IDLE`.

## Acceptance

16 robots / 300 seconds / seed 1234 / BUSY / 10-second warm-up:

- completion checkpoints: 27 / 57 / 87
- productive / task-waiting / engaged: 0.6971 / 0.3029 / 1.0000
- average true idle robots: 0.000
- minimum engaged after warm-up: 16
- direct handoffs / parking returns: 87 / 0
- collision/head-on/deadlock/obstacle penetration/current indefinite wait: all 0
- reservation leaks and load ownership violations: 0

24 robots completed 82 tasks with engaged ratio 1.0000 and safety values 0. Its
0.5644 productive ratio and 96.642-second cycle time show the remaining physical
station/traffic contention rather than fake activity.

## Evidence

- `evidence/v5_2_full_fleet_engagement.png`
- `evidence/v5_2_staging_queue_debug.png`
- `evidence/v5_2_factory_stress.txt`

TASK-010/V6 was not started. Commit and push are prohibited until Human verification.
