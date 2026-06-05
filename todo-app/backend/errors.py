"""도메인 예외 정의 모듈 (리팩터링 P1-1).

[SRP] 도메인 오류를 파이썬 내장 예외(KeyError 등)가 아니라 도메인 언어로
      표현한다. 서비스 계층은 '할일 없음'이라는 도메인 의미를 명확한 타입으로
      던지고, API 계층은 이를 HTTP 상태 코드로 번역한다.
"""


class TodoError(Exception):
    """할일 도메인 공통 예외의 베이스 클래스."""


class TodoNotFoundError(TodoError):
    """해당 id의 할일이 존재하지 않을 때 발생한다."""

    def __init__(self, todo_id: str) -> None:
        self.todo_id = todo_id
        super().__init__(f"Todo not found: {todo_id}")
