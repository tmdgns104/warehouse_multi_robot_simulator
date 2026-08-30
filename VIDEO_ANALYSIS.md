# Video Analysis

## Purpose

이 문서는 프로젝트의 시각적 Reference 영상에서 **직접 관찰 가능한 요소**, **구현을 위한 합리적 추정**, **현재 확인 불가능한 의미**를 구분한다.

원본 Reference는 Repository에 다음 이름으로 추가하는 것을 권장한다.

```text
reference/warehouse_reference.mp4
```

## Directly Observed

영상 프레임에서 다음 특징이 반복적으로 확인된다.

- 밝은 흰색/회색 계열의 넓은 2D 자동화 시설 화면
- 중앙에 규칙적으로 반복되는 여러 설비 블록
- 상단에 별도 설비/대기 영역처럼 보이는 반복 요소
- 좌우와 하단에도 별도 작업/이동 영역 존재
- 시설 전체를 연결하는 얇은 선 형태의 이동 Network
- 여러 개의 작은 객체가 Network를 따라 동시에 이동
- 초록색 사각형 계열 객체
- 노랑/갈색 계열 작은 객체
- 검은 원형 객체
- 파랑/하늘색 계열 설비 또는 객체
- 시간에 따라 객체 위치가 지속적으로 변함

## Strong Implementation Inference

다음은 영상의 움직임을 재현하기 위해 채택하는 구현 모델이며, 영상의 실제 내부 소프트웨어 구조가 확인되었다는 의미는 아니다.

- 이동 공간을 자유 Grid보다 `Node/Edge Lane Graph`로 모델링
- Agent가 Lane Edge를 따라 연속적으로 이동
- 교차점/좁은 Lane에서 자원 예약 또는 우선순위 제어
- Station 또는 작업 구역 간 Task Flow
- 여러 Agent 상태를 중앙 Fleet Manager에서 관리

## Unknown / Do Not Assert as Fact

영상만으로 다음을 확정하지 않는다.

- 초록색 객체가 실제 AGV/AMR인지
- 검은 원형 객체의 정확한 역할
- 노랑/갈색 객체가 Pallet/Load인지
- 파랑 객체가 Robot, Machine, Conveyor 중 무엇인지
- 실제 프로그램이 A*, Dijkstra, MAPF, PLC Logic 중 무엇을 사용하는지
- 실제 통신 방식이 ROS2, PLC, MQTT, OPC UA 등 무엇인지

확인 전 코드에서는 중립 이름을 사용한다.

```text
MobileAgent
Load
Machine
Station
Marker
LaneNode
LaneEdge
```

## Reproduction Priority

영상 재현 단계 V2~V7에서 우선순위는 다음과 같다.

1. 전체 Layout 비율과 구역 구성
2. Lane Network의 시각적 형태
3. 객체 크기/색/밀도
4. 여러 객체의 동시 이동
5. 부드러운 이동 Animation
6. Traffic Waiting / Queue 표현
7. Task/Fleet 상태 Panel

정확한 산업적 의미는 시각/동작 재현보다 뒤에 둔다.

## Human Visual Verification

각 영상 재현 Version은 자동 Test만으로 완료하지 않는다.

Human이 원본 영상과 실행 화면을 나란히 비교하여 다음을 확인한다.

- Layout가 충분히 유사한가
- 객체 크기와 밀도가 비슷한가
- 이동선/교차로가 영상 느낌과 비슷한가
- 움직임 속도와 부드러움이 자연스러운가
- 동시에 움직이는 객체 수가 충분한가

Human Visual Verification 결과는 STATUS.md에 기록한다.
