# TASK-004 - Collision Avoidance

## Goal

다중 Robot 충돌 방지.

## Required Conflicts

- same cell conflict
- head-on swap conflict

## Policy

- wait count 높은 Robot 우선
- 동률이면 Robot ID 우선

## Tests

충돌 시 두 Robot이 같은 셀을 차지하지 않아야 함.
