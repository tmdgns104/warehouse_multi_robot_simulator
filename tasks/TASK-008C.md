# TASK-008C - V4.3 Obstacle-safe Manhattan Grid

Status: COMPLETE / HUMAN GRID LANE VERIFICATION PASS

## Goal

Human review found that the safe reference-derived rails still did not read as a connected warehouse grid. V4.3 reconstructs the displayed and drivable network as the same obstacle-safe Manhattan grid.

## Pipeline

```text
Measured aisle X/Y coordinates
  -> full horizontal/vertical candidate grid
  -> Machine + Station 7 px expanded obstacle pruning
  -> 1 px cut separation and canonical 2 px snap
  -> LaneGraph
  -> network_segments()
  -> pygame / Pillow renderer
```

Candidate lines are split at obstacle intervals rather than deleting an entire aisle. Safe surviving pieces meet at canonical intersection coordinates and form junction nodes automatically.

## Connected Regions

- Top: a full y=112 driving rail joins safe vertical aisles above and around the top Stations.
- Left/right: outer x=226/x=962 rails connect all safe cross aisles and bypass side Station stacks.
- Centre: horizontal cross aisles connect safe vertical pieces around each Machine row.
- Bottom: every surviving vertical joins y=555/588/618/648 return rails.

## Visual-only

- The y=66 Upper Cap enclosure (`top_cap_a/b/c`) remains blue-grey visual-only geometry.
- Machine internal detail remains dark blue.
- Facility, Machine, and Station decoration are not graph edges.

## Topology

- Before V4.3: 200 nodes / 342 edges / 1 component / cycle rank 143
- After V4.3: 251 nodes / 405 edges / 1 component / cycle rank 155
- Branching nodes: 203
- Renderer driving segments: 405, exactly matching graph edges
- Unsafe nodes / edges: 0 / 0
- Unintended 1–2 px gaps: 0

## Verification

- Full tests: 57 passed
- 16 entities / 300 seconds: 265 trips; 360 edges and 207 nodes used
- 24 entities / 300 seconds: 379 trips
- Both runs: collisions/head-on/deadlocks/obstacle penetrations = 0

## Evidence

- `evidence/v4_3_grid_lane_topology.png`
- `evidence/v4_3_grid_lane_debug.png`
- `evidence/v4_3_grid_lane_stress.txt`

Human verified the pygame Manhattan grid and approved progression to TASK-009.
