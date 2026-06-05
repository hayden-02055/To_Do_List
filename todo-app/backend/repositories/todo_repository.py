"""인메모리 기반 할일 저장소 구현 모듈."""

from typing import List, Optional

from interfaces.repository import AbstractTodoRepository
from models.todo import Todo


class MemoryTodoRepository(AbstractTodoRepository):
    """인메모리(딕셔너리) 기반 할일 저장소 구현체.

    [LSP] AbstractTodoRepository를 완전히 대체 가능한 구현체.
          상위 계층은 추상 타입만 알면 되고 이 구현체로 안전하게 치환된다.
    [OCP] DB 저장소로 교체할 경우 이 클래스만 새로 작성하면 된다.

    내부 저장소: Dict[str, Todo]
    """

    def __init__(self) -> None:
        # [SRP] 이 클래스는 '저장' 책임만 담당한다.
        self._store: dict[str, Todo] = {}

    def get_all(self) -> List[Todo]:
        """저장된 모든 할일을 리스트로 반환한다."""
        return list(self._store.values())

    def get_by_id(self, todo_id: str) -> Optional[Todo]:
        """id로 할일을 조회한다. 존재하지 않으면 None을 반환한다."""
        return self._store.get(todo_id)

    def save(self, todo: Todo) -> Todo:
        """할일을 저장한다. 같은 id가 있으면 갱신, 없으면 신규 추가."""
        self._store[todo.id] = todo
        return todo

    def delete(self, todo_id: str) -> bool:
        """id에 해당하는 할일을 삭제한다.

        Returns:
            삭제에 성공하면 True, 대상이 없으면 False.
        """
        if todo_id in self._store:
            del self._store[todo_id]
            return True
        return False
