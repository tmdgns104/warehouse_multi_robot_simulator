# Shared AI Implementation Contract

이 문서 세트는 서로 다른 Human/AI가 독립적으로 구현해도 현재 시스템과 같은 Architecture,
이름, 상태, 정책과 acceptance 결과를 만들기 위한 reconstructable specification이다.

## Source-of-truth priority

1. Human-approved current goal
2. `PROJECT.md`
3. `REQUIREMENTS.md`
4. `ARCHITECTURE.md`
5. `DECISIONS.md`
6. `docs/shared_contract/*`
7. current `tasks/TASK-*.md`
8. implementation

`AGENTS.md`의 실행 규칙과 충돌하면 `AGENTS.md`를 따른다. 이 pack은 현재 implementation에서
추출했으며, 불일치는 `DOCUMENTATION CONFLICT`로 기록한다.

## Mandatory reading order

`00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12`

## Non-negotiable rules

- Do not invent synonyms for canonical concepts.
- Do not rename canonical interfaces.
- Do not create a second implementation of an existing responsibility.
- Business engines create requirements; `FactoryEngine` executes Robot work; traffic owns safety.
- Views and renderers are read-only projections.
- Reference-derived geometry and synthetic business semantics must be distinguished.

Baseline extracted: `main` at `46834f68287578fda1ceaf0d4f74709a88382c2a`, plus the
uncommitted Human-gated TASK-009F-A V5.6.1 view changes present during extraction.
