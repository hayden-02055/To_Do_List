"""도메인 예외 정의 모듈 (리팩터링 P1-1, v4 업데이트).

[SRP] 도메인 오류를 파이썬 내장 예외(KeyError, OSError 등)가 아니라
      도메인 언어로 표현한다.
      - 서비스 계층: '할일 없음'이라는 도메인 의미를 명확한 타입으로 던짐
      - 저장소 계층: '파일 I/O 실패'를 도메인 언어로 감싸서 상위로 전달
      - API 계층: 도메인 예외를 HTTP 상태 코드로 번역
"""


class TodoError(Exception):
    """할일 도메인 공통 예외의 베이스 클래스."""


class TodoNotFoundError(TodoError):
    """해당 id의 할일이 존재하지 않을 때 발생한다."""

    def __init__(self, todo_id: str) -> None:
        self.todo_id = todo_id
        super().__init__(f"Todo not found: {todo_id}")


class FileIOError(TodoError):
    """JSON 파일 읽기/쓰기에 실패했을 때 발생한다.

    [v4 신규] 파이썬 내장 OSError / json.JSONDecodeError를 도메인 예외로
    감싼다. 이렇게 하면 상위 계층(서비스, API)이 저장 매체(파일 시스템)의
    세부사항에 의존하지 않는다 — 나중에 DB로 바꿔도 예외 타입은 동일하다.

    리팩터링 이전(Bad):
        OSError, json.JSONDecodeError가 그대로 서비스 계층까지 올라옴
        → 서비스가 파일 시스템 세부사항을 알아야 하는 DIP 위반

    리팩터링 이후(Good):
        FileRepository 내부에서 내장 예외를 잡아 FileIOError로 변환
        → 서비스/API 계층은 FileIOError 하나만 알면 됨
    """

    def __init__(self, operation: str, cause: Exception) -> None:
        self.operation = operation   # "load" 또는 "save"
        self.cause = cause
        super().__init__(f"파일 {operation} 실패: {cause}")
