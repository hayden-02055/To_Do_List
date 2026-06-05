"""TodoService 단위 테스트.

실제 저장소 대신 MockTodoRepository를 정의하여, 외부 의존성 없이
서비스 계층의 비즈니스 로직을 검증한다. [DIP] 덕분에 저장소를 손쉽게
대체할 수 있어 테스트가 단순해진다.
"""

from typing import List, Optional

import pytest

from errors import TodoNotFoundError
from events.event_names import TodoEvent
from events.event_system import EventBus
from interfaces.repository import AbstractTodoRepository
from models.enums import Category, Priority
from models.todo import Todo, TodoCreate
from repositories.todo_repository import MemoryTodoRepository
from services.todo_service import TodoService


class MockTodoRepository(AbstractTodoRepository):
    """테스트용 인메모리 Mock 저장소.

    [LSP] AbstractTodoRepository의 계약을 그대로 만족하므로 실제 저장소를
          안전하게 대체한다.
    """

    def __init__(self) -> None:
        self._store: dict[str, Todo] = {}

    def get_all(self) -> List[Todo]:
        return list(self._store.values())

    def get_by_id(self, todo_id: str) -> Optional[Todo]:
        return self._store.get(todo_id)

    def save(self, todo: Todo) -> Todo:
        self._store[todo.id] = todo
        return todo

    def delete(self, todo_id: str) -> bool:
        if todo_id in self._store:
            del self._store[todo_id]
            return True
        return False


@pytest.fixture
def bus() -> EventBus:
    """테스트마다 새로운 이벤트 버스를 제공한다."""
    return EventBus()


@pytest.fixture
def service(bus: EventBus) -> TodoService:
    """Mock 저장소를 주입한 TodoService를 제공한다."""
    return TodoService(MockTodoRepository(), bus)


def test_create_todo(service: TodoService) -> None:
    """할일 생성 후 목록에 존재하는지 확인."""
    created = service.create_todo(TodoCreate(title="공부하기"))

    todos = service.get_todos()
    assert len(todos) == 1
    assert todos[0].id == created.id
    assert todos[0].title == "공부하기"


def test_create_todo_defaults(service: TodoService) -> None:
    """기본값(done=False, priority=MEDIUM) 확인."""
    created = service.create_todo(TodoCreate(title="기본값 확인"))

    assert created.done is False
    assert created.priority == Priority.MEDIUM
    assert created.category == Category.OTHER


def test_toggle_done(service: TodoService) -> None:
    """완료 토글 시 True로 전환되는지 확인."""
    created = service.create_todo(TodoCreate(title="토글 대상"))
    assert created.done is False

    toggled = service.toggle_done(created.id)
    assert toggled.done is True


def test_toggle_done_twice(service: TodoService) -> None:
    """두 번 토글 시 원래 상태로 복귀하는지 확인."""
    created = service.create_todo(TodoCreate(title="두 번 토글"))

    service.toggle_done(created.id)
    twice = service.toggle_done(created.id)

    assert twice.done is False


def test_delete_todo(service: TodoService) -> None:
    """삭제 후 목록에서 제거되는지 확인."""
    created = service.create_todo(TodoCreate(title="삭제 대상"))
    assert len(service.get_todos()) == 1

    service.delete_todo(created.id)
    assert len(service.get_todos()) == 0


def test_delete_nonexistent(service: TodoService) -> None:
    """존재하지 않는 id 삭제 시 도메인 예외(TodoNotFoundError) 발생 확인.

    [P1-1] 범용 KeyError가 아니라 도메인 예외를 던지므로 의도가 또렷하다.
    """
    with pytest.raises(TodoNotFoundError):
        service.delete_todo("nonexistent-id")


def test_filter_by_category(service: TodoService) -> None:
    """카테고리 필터 동작 확인."""
    service.create_todo(TodoCreate(title="업무1", category=Category.WORK))
    service.create_todo(TodoCreate(title="개인1", category=Category.PERSONAL))
    service.create_todo(TodoCreate(title="업무2", category=Category.WORK))

    work_todos = service.get_todos(category=Category.WORK)
    assert len(work_todos) == 2
    assert all(t.category == Category.WORK for t in work_todos)


def test_filter_by_done(service: TodoService) -> None:
    """완료 여부 필터 동작 확인."""
    a = service.create_todo(TodoCreate(title="완료될 항목"))
    service.create_todo(TodoCreate(title="미완료 항목"))
    service.toggle_done(a.id)

    done_todos = service.get_todos(done=True)
    not_done_todos = service.get_todos(done=False)

    assert len(done_todos) == 1
    assert done_todos[0].id == a.id
    assert len(not_done_todos) == 1


def test_filter_by_priority(service: TodoService) -> None:
    """우선순위 필터 동작 확인."""
    service.create_todo(TodoCreate(title="긴급", priority=Priority.HIGH))
    service.create_todo(TodoCreate(title="보통", priority=Priority.MEDIUM))
    service.create_todo(TodoCreate(title="급함", priority=Priority.HIGH))

    high_todos = service.get_todos(priority=Priority.HIGH)
    assert len(high_todos) == 2
    assert all(t.priority == Priority.HIGH for t in high_todos)


def test_search_by_title(service: TodoService) -> None:
    """제목 키워드로 검색되는지 확인."""
    service.create_todo(TodoCreate(title="파이썬 공부하기"))
    service.create_todo(TodoCreate(title="장보기"))

    result = service.get_todos(search="파이썬")
    assert len(result) == 1
    assert result[0].title == "파이썬 공부하기"


def test_search_by_description(service: TodoService) -> None:
    """설명 키워드로 검색되는지 확인."""
    service.create_todo(
        TodoCreate(title="회의", description="분기 매출 보고서 검토")
    )
    service.create_todo(TodoCreate(title="운동", description="러닝 30분"))

    result = service.get_todos(search="보고서")
    assert len(result) == 1
    assert result[0].title == "회의"


def test_search_case_insensitive(service: TodoService) -> None:
    """대소문자를 구분하지 않고 검색되는지 확인."""
    service.create_todo(TodoCreate(title="Read FastAPI docs"))

    assert len(service.get_todos(search="fastapi")) == 1
    assert len(service.get_todos(search="FASTAPI")) == 1


def test_search_no_result(service: TodoService) -> None:
    """검색 결과가 없을 때 빈 리스트를 반환하는지 확인."""
    service.create_todo(TodoCreate(title="장보기"))

    result = service.get_todos(search="존재하지않는키워드")
    assert result == []


def test_filter_and_search_combined(service: TodoService) -> None:
    """필터와 검색을 동시에 적용했을 때 교집합이 반환되는지 확인.

    [리팩터링 보장] 필터 파이프라인을 분리한 뒤에도 여러 조건의
        조합 결과가 기대대로 동작함을 검증한다.
    """
    service.create_todo(
        TodoCreate(title="업무 보고서", category=Category.WORK)
    )
    service.create_todo(
        TodoCreate(title="개인 보고서", category=Category.PERSONAL)
    )
    service.create_todo(
        TodoCreate(title="업무 회의", category=Category.WORK)
    )

    result = service.get_todos(category=Category.WORK, search="보고서")
    assert len(result) == 1
    assert result[0].title == "업무 보고서"


def test_event_emitted_on_create(service: TodoService, bus: EventBus) -> None:
    """생성 시 'todo.created' 이벤트가 발행되는지 확인."""
    received: list = []
    bus.on(TodoEvent.CREATED, lambda data: received.append(data))

    created = service.create_todo(TodoCreate(title="이벤트 생성"))

    assert len(received) == 1
    assert received[0].id == created.id


def test_event_emitted_on_delete(service: TodoService, bus: EventBus) -> None:
    """삭제 시 'todo.deleted' 이벤트가 발행되는지 확인."""
    received: list = []
    bus.on(TodoEvent.DELETED, lambda data: received.append(data))

    created = service.create_todo(TodoCreate(title="이벤트 삭제"))
    service.delete_todo(created.id)

    assert len(received) == 1
    assert received[0] == created.id


def test_emit_isolates_subscriber_exception(bus: EventBus) -> None:
    """[P1-4][Observer] 한 구독자가 예외를 던져도 다른 구독자는 실행된다.

    발행자-구독자의 진짜 독립성: 한 구독자의 실패가 전파되지 않아야 한다.
    """
    order: list = []

    def failing(_data) -> None:
        order.append("failing")
        raise RuntimeError("구독자 내부 오류")

    def healthy(_data) -> None:
        order.append("healthy")

    bus.on(TodoEvent.CREATED, failing)
    bus.on(TodoEvent.CREATED, healthy)

    # 예외가 emit 밖으로 새어 나오지 않아야 한다.
    bus.emit(TodoEvent.CREATED, None)

    assert order == ["failing", "healthy"]


def test_memory_repository_get_by_id_returns_copy() -> None:
    """[P1-2][LSP] MemoryTodoRepository.get_by_id는 복사본을 반환한다.

    반환값을 외부에서 수정해도 저장소 내부 상태가 바뀌지 않아야,
    FileRepository와 행동 계약이 동일해진다(안전한 치환).
    """
    repo = MemoryTodoRepository()
    repo.save(Todo(id="x", title="원본"))

    fetched = repo.get_by_id("x")
    fetched.title = "외부에서 변경"  # 반환된 복사본을 수정

    # 저장소 내부는 영향을 받지 않아야 한다.
    assert repo.get_by_id("x").title == "원본"
