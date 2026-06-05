"""할일(Todo) 비즈니스 로직을 담당하는 서비스 계층 모듈."""

from typing import List, Optional

from errors import TodoNotFoundError
from events.event_names import TodoEvent
from events.event_system import EventBus
from interfaces.repository import AbstractTodoRepository
from models.enums import Category, Priority
from models.todo import Todo, TodoCreate


class TodoService:
    """할일 관련 비즈니스 로직을 담당하는 서비스.

    [SRP] 비즈니스 로직만 담당하며, 실제 저장/삭제는 repository에 위임한다.
    [DIP] 구체 클래스(MemoryTodoRepository)가 아니라 추상
          (AbstractTodoRepository)에 의존한다. 따라서 저장소 구현이
          바뀌어도 이 클래스는 영향을 받지 않는다.
    """

    def __init__(self, repository: AbstractTodoRepository, bus: EventBus) -> None:
        """서비스를 생성한다.

        Args:
            repository: 추상 저장소(의존성 주입).
            bus: 이벤트 버스(의존성 주입).
        """
        # [DIP] 생성자 주입으로 의존성을 외부에서 받는다.
        self._repo = repository
        self._bus = bus

    def create_todo(self, data: TodoCreate) -> Todo:
        """할일을 생성하고 'todo.created' 이벤트를 발행한다.

        Args:
            data: 생성 요청 데이터.

        Returns:
            저장된 Todo 객체.
        """
        todo = Todo(**data.model_dump())
        saved = self._repo.save(todo)
        self._bus.emit(TodoEvent.CREATED, saved)
        return saved

    def get_todos(
        self,
        category: Optional[Category] = None,
        priority: Optional[Priority] = None,
        done: Optional[bool] = None,
        search: Optional[str] = None,  # 검색어 파라미터 추가
    ) -> List[Todo]:
        """필터 + 검색 조건에 맞는 할일 목록을 반환한다.

        모든 인자가 None이면 전체 목록을 반환한다.

        [리팩터링] 초기에는 이 메서드 내부에 모든 필터 조건이 인라인으로
            나열되어 있었으나(아래 '리팩터링 이전' 참고), 검색 조건이
            추가되면서 함수가 길어지고 각 필터의 책임이 불분명해졌다.
            이를 _apply_filters() + 각 _filter_by_*() private 메서드로
            분리하여 파이프라인 구조로 만들었다.
        [캡슐화] 호출자는 내부 필터 구현 세부사항을 알 필요가 없다.

        리팩터링 이전(Bad)::

            todos = self._repo.get_all()
            if category: todos = [t for t in todos if t.category == category]
            if priority: todos = [t for t in todos if t.priority == priority]
            if done is not None: todos = [t for t in todos if t.done == done]
            if search: todos = [t for t in todos if search in t.title]
            return todos

        Args:
            category: 카테고리 필터.
            priority: 우선순위 필터.
            done: 완료 여부 필터.
            search: 제목·설명 검색 키워드.

        Returns:
            조건에 부합하는 Todo 리스트.
        """
        todos = self._repo.get_all()
        return self._apply_filters(todos, category, priority, done, search)

    def toggle_done(self, todo_id: str) -> Todo:
        """완료 상태를 토글하고 'todo.completed' 이벤트를 발행한다.

        Args:
            todo_id: 토글할 할일의 id.

        Returns:
            갱신된 Todo 객체.

        Raises:
            TodoNotFoundError: 해당 id의 할일이 없을 때.
        """
        todo = self._repo.get_by_id(todo_id)
        if todo is None:
            raise TodoNotFoundError(todo_id)

        todo.done = not todo.done
        saved = self._repo.save(todo)
        self._bus.emit(TodoEvent.COMPLETED, saved)
        return saved

    def delete_todo(self, todo_id: str) -> None:
        """할일을 삭제하고 'todo.deleted' 이벤트를 발행한다.

        Args:
            todo_id: 삭제할 할일의 id.

        Raises:
            TodoNotFoundError: 해당 id의 할일이 없을 때.
        """
        deleted = self._repo.delete(todo_id)
        if not deleted:
            raise TodoNotFoundError(todo_id)

        self._bus.emit(TodoEvent.DELETED, todo_id)

    # ── Private (캡슐화된 내부 필터 로직) ──────────────────────────
    # [캡슐화] 아래 메서드들은 '_' prefix로 외부 노출을 막는다.
    # [리팩터링] get_todos()의 인라인 필터를 단계별 메서드로 분리한 결과.

    def _apply_filters(
        self,
        todos: List[Todo],
        category: Optional[Category],
        priority: Optional[Priority],
        done: Optional[bool],
        search: Optional[str],
    ) -> List[Todo]:
        """필터·검색 파이프라인을 순차 적용한다.

        [캡슐화] 필터·검색 구현 세부사항을 외부에 은닉한다.
        [리팩터링] 각 필터 조건을 독립 private 메서드로 분리하여,
            조건 추가/변경 시 해당 메서드만 수정하면 된다. (OCP 지향)

        Args:
            todos: 필터링 대상 전체 목록.
            category: 카테고리 필터.
            priority: 우선순위 필터.
            done: 완료 여부 필터.
            search: 검색 키워드.

        Returns:
            모든 조건을 통과한 Todo 리스트.
        """
        todos = self._filter_by_category(todos, category)
        todos = self._filter_by_priority(todos, priority)
        todos = self._filter_by_done(todos, done)
        todos = self._filter_by_search(todos, search)
        return todos

    def _filter_by_category(
        self, todos: List[Todo], category: Optional[Category]
    ) -> List[Todo]:
        """[캡슐화] 카테고리 필터 — 내부 전용. None이면 통과시킨다."""
        if category is None:
            return todos
        return [t for t in todos if t.category == category]

    def _filter_by_priority(
        self, todos: List[Todo], priority: Optional[Priority]
    ) -> List[Todo]:
        """[캡슐화] 우선순위 필터 — 내부 전용. None이면 통과시킨다."""
        if priority is None:
            return todos
        return [t for t in todos if t.priority == priority]

    def _filter_by_done(
        self, todos: List[Todo], done: Optional[bool]
    ) -> List[Todo]:
        """[캡슐화] 완료 여부 필터 — 내부 전용. None이면 통과시킨다."""
        if done is None:
            return todos
        return [t for t in todos if t.done == done]

    def _filter_by_search(
        self, todos: List[Todo], search: Optional[str]
    ) -> List[Todo]:
        """[캡슐화] 검색 필터 — title과 description에서 키워드를 찾는다.

        [리팩터링] 초기에는 get_todos() 내부 인라인 코드였으나 독립
            메서드로 분리하여 가독성·재사용성을 높였다.
        대소문자를 구분하지 않도록 casefold()를 적용한다.

        Args:
            todos: 검색 대상 목록.
            search: 검색 키워드(빈 문자열/None이면 전체 통과).

        Returns:
            제목 또는 설명에 키워드를 포함하는 Todo 리스트.
        """
        if not search:
            return todos
        keyword = search.casefold()
        return [
            t
            for t in todos
            if keyword in t.title.casefold()
            or keyword in t.description.casefold()
        ]
