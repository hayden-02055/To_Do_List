"""저장소(Repository) 추상 인터페이스 정의 모듈.

[ISP] 읽기/쓰기 인터페이스를 분리하여, 클라이언트가 필요로 하지 않는
      메서드에 의존하지 않도록 한다.
[OCP] AbstractTodoRepository를 상속하면 본문 코드 수정 없이 새 저장소
      구현체를 추가할 수 있다.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from models.todo import Todo


class IReadable(ABC):
    """[ISP] 읽기 전용 인터페이스."""

    @abstractmethod
    def get_all(self) -> List[Todo]:
        """저장된 모든 할일을 반환한다."""
        ...

    @abstractmethod
    def get_by_id(self, todo_id: str) -> Optional[Todo]:
        """id로 할일 한 건을 조회한다. 없으면 None을 반환한다."""
        ...


class IWritable(ABC):
    """[ISP] 쓰기 전용 인터페이스."""

    @abstractmethod
    def save(self, todo: Todo) -> Todo:
        """할일을 저장(신규 생성 또는 갱신)하고 저장된 객체를 반환한다."""
        ...

    @abstractmethod
    def delete(self, todo_id: str) -> bool:
        """id에 해당하는 할일을 삭제한다. 성공 시 True를 반환한다."""
        ...


class AbstractTodoRepository(IReadable, IWritable, ABC):
    """[OCP] 확장을 위한 추상 저장소.

    새 구현체(예: DB 저장소)를 추가할 때 이 클래스만 상속하면 되며,
    이 클래스를 의존하는 상위 계층(서비스)은 수정할 필요가 없다.
    """

    pass
