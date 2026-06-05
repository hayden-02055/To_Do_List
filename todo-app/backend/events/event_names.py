"""이벤트 이름 상수 정의 모듈 (리팩터링 P1-3).

[DRY / SSOT] 이벤트 이름을 한 곳에서 관리한다. 문자열을 코드 곳곳에 흩뿌리면
             오타가 런타임에야 드러나지만, Enum 멤버를 쓰면 오타 시 즉시
             에러가 난다.

str을 함께 상속하므로 기존의 문자열 기반 구독/발행과도 호환된다
(TodoEvent.CREATED == "todo.created").
"""

from enum import Enum


class TodoEvent(str, Enum):
    """할일 도메인에서 발행하는 이벤트 이름."""

    CREATED = "todo.created"    # 할일 생성 시
    COMPLETED = "todo.completed"  # 완료 토글 시
    DELETED = "todo.deleted"    # 삭제 시
