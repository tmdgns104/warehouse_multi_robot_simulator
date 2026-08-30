# TASK-008A - V4.1 Safe Lane Topology

Status: REVISION IMPLEMENTED / AUTOMATED VERIFICATION PASS / HUMAN TOPOLOGY VERIFICATION REQUIRED

## Cause

The visual `NetworkSegment` collection and `MachineBlock` geometry were independent. The graph converter therefore produced nine edges through the first three columns of repeated machines. Small 1–2 px endpoint gaps also left side loops visually disconnected. The upper cap formed a second graph component despite having no observed MobileEntity traffic.

## Implemented Scope

- Expanded each MachineBlock by a 7 px entity-centre clearance.
- Added point, orthogonal-segment, node, and edge obstacle validation.
- Derived safe aisle centres for `vertical_3`, `vertical_5`, and `vertical_7`.
- Snapped only safe perpendicular endpoint gaps up to 2 px.
- Kept the upper cap as non-drivable visual geometry.
- Rechecked eight video times and enlarged top/bottom frames. Four central lower aisles (`vertical_5`–`vertical_8`) align with observed lower moving objects and now connect on their existing centerlines to the bottom return. Other unverified stubs remain unchanged.
- Made the default renderer consume the same Safe LaneGraph used for motion.
- Added continuous entity-position obstacle checks.
- Styled the Upper Cap in blue-grey and Machine decoration in dark blue so neither reads as a driving lane.
- Added an exact rendered-edge/topology equivalence and perpendicular near-gap regression.

## Measured Topology

- Before: 224 nodes / 359 edges / 2 graph components / 9 unsafe edges
- After Human revision: 213 nodes / 355 edges / 1 driving component
- Unsafe nodes: 0
- Unsafe edges: 0

## Stress Verification

- 16 entities / 300 seconds: 272 trips, 0 collisions, 0 head-on conflicts, 0 deadlocks, 0 obstacle penetrations
- 24 entities / 300 seconds: 395 trips, 0 collisions, 0 head-on conflicts, 0 deadlocks, 0 obstacle penetrations
- Full test suite: 57 passed

## Evidence

- `evidence/v4_1_safe_lane_topology.png`
- `evidence/v4_1_topology_debug.png`

TASK-009 was not started.

Completion remains gated on Human pygame topology verification. No commit or push was made.
