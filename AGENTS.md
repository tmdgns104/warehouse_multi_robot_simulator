# AGENTS

## Human

- 프로젝트 목적과 Reference Target 승인
- 큰 Architecture 변경 승인
- 실제 실행 화면과 영상 유사도 최종 확인
- ROS2/Gazebo 실제 GUI/물리 동작 Human Verification

## ChatGPT

- Reference 영상 분석
- Architecture/Requirements/Task 설계
- Codex 구현 결과 Review
- Version Gate와 다음 단계 정의
- 영상에서 확인된 사실과 추론을 구분

## Codex

- Repository 상태 조사
- 현재 Task 구현
- 테스트
- 오류 수정
- 문서화
- Evidence 기록

## Source of Truth Priority

충돌 시 우선순위:

1. Human의 현재 승인된 목표
2. PROJECT.md
3. REQUIREMENTS.md
4. ARCHITECTURE.md
5. DECISIONS.md
6. 현재 Task 문서
7. 기존 구현

Reference 영상의 시각적 사실은 V2~V7 재현 요구사항의 근거다.
영상에서 의미가 확인되지 않는 Entity를 임의로 특정 산업 설비/로봇으로 확정하지 않는다.

## Autonomous Work Policy

현재 승인된 Version/Task 범위 안에서는 Codex가 다음 흐름을 자동으로 계속한다.

```text
inspect → implement → test → diagnose → fix → retest → document
```

일반적인 코드 오류, 테스트 실패, 작은 Refactor, 문서 정합성 수정은 Human 승인 없이 해결한다.

다음 상황에서만 Human Gate가 필요하다.

- 승인된 Version Scope를 크게 확대/축소해야 함
- 기존 Architecture의 핵심 경계를 변경해야 함
- 시스템 관리자 권한 또는 sudo 필요
- 기존 사용자 데이터/Repository History를 파괴할 위험
- 새로운 유료/대형 외부 서비스 의존성 필요
- Reference 영상과 요구사항이 명확하게 충돌함

## Version Discipline

현재 Version을 완료하기 전에 다음 Version의 기능을 임의로 구현하지 않는다.

단, 다음 Version을 위한 Interface를 준비하는 작은 비침투적 설계는 허용한다.

각 Version 완료 조건:

- 해당 Task 구현
- Unit/Integration Test PASS
- Regression 확인
- STATUS.md 갱신
- 실행 방법 문서화
- GUI 관련 Version은 가능한 범위의 Human Visual Verification 항목 명시

## ROS2/Gazebo Discipline

V8 이전에는 ROS2/Gazebo 의존성을 Core에 넣지 않는다.

V8 이후에도 Domain Core와 ROS2 Adapter를 분리한다.

Fleet Manager가 직접 Wheel Velocity를 만들지 않는다.
V10부터 실제 Robot 주행은 Nav2 책임으로 둔다.
