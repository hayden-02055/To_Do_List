"""이벤트 버스(Observer 패턴) 구현 모듈."""

from typing import Any, Callable, Dict, List


class EventBus:
    """Observer 패턴 구현체.

    발행자(Publisher)와 구독자(Subscriber)를 느슨하게 연결한다.
    구독자는 관심 있는 이벤트 이름에 콜백을 등록(on)하고, 발행자는 이벤트를
    발행(emit)하기만 하면 등록된 모든 콜백이 실행된다. 발행자와 구독자는
    서로의 존재를 직접 알 필요가 없다.

    사용 이벤트:
      - "todo.created"   : 할일 생성 시
      - "todo.completed" : 완료 토글 시
      - "todo.deleted"   : 삭제 시
    """

    def __init__(self) -> None:
        # 이벤트 이름 -> 콜백 리스트
        self._listeners: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable) -> None:
        """이벤트 구독을 등록한다.

        Args:
            event: 구독할 이벤트 이름.
            callback: 이벤트 발생 시 호출될 콜백(데이터를 인자로 받음).
        """
        self._listeners.setdefault(event, []).append(callback)

    def emit(self, event: str, data: Any = None) -> None:
        """이벤트를 발행하여 등록된 모든 콜백을 실행한다.

        [Observer] 한 구독자에서 예외가 나도 나머지 구독자는 정상 실행되도록
        각 콜백을 try/except로 격리한다. 이렇게 해야 발행자-구독자의 진짜
        독립성이 보장된다(한 구독자의 실패가 다른 구독자로 전파되지 않음).

        Args:
            event: 발행할 이벤트 이름.
            data: 콜백에 전달할 데이터.
        """
        for callback in self._listeners.get(event, []):
            try:
                callback(data)
            except Exception as exc:  # [Observer] 구독자 예외 격리
                print(f"[EventBus] '{event}' 구독자 처리 실패: {exc}")


# 싱글턴 인스턴스 (앱 전역에서 공유한다)
event_bus = EventBus()
