"""FastAPI 애플리케이션 진입점.

- CORSMiddleware로 프론트엔드 연동을 허용한다.
- lifespan 이벤트에서 EventBus 구독자(로깅 콜백)를 등록한다. (Observer 시연)
- Depends()로 TodoService 의존성을 주입한다. ([DIP])
- 라우터 prefix는 '/todos'.
"""

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from errors import TodoNotFoundError
from events.event_names import TodoEvent
from events.event_system import event_bus
from models.enums import Category, Priority
from models.todo import Todo, TodoCreate
from repositories.file_repository import FileRepository
from services.todo_service import TodoService

# [OCP] 저장소만 FileRepository로 교체한다.
#       TodoService·인터페이스·테스트 코드는 한 줄도 수정하지 않는다 —
#       확장에는 열려 있고 수정에는 닫혀 있음(OCP)을 실증한다.
# [싱글턴] 앱 전역에서 공유하는 단일 인스턴스. 요청마다 새로 만들면
#          파일을 중복으로 읽으므로 전역 인스턴스로 관리한다.
repository = FileRepository()


def get_service() -> TodoService:
    """TodoService 의존성 제공자.

    [DIP] 추상 저장소와 이벤트 버스를 주입하여 서비스를 구성한다.
    """
    return TodoService(repository, event_bus)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시점의 생명주기 관리.

    [Observer 패턴 시연] 시작 시 EventBus에 콘솔 로깅 콜백을 구독시킨다.
    서비스 계층이 이벤트를 발행하면 여기서 등록한 콜백이 자동 실행된다.
    """

    def log_created(todo: Todo) -> None:
        print(f"[EVENT] todo.created   -> id={todo.id} title={todo.title!r}")

    def log_completed(todo: Todo) -> None:
        print(f"[EVENT] todo.completed -> id={todo.id} done={todo.done}")

    def log_deleted(todo_id: str) -> None:
        print(f"[EVENT] todo.deleted   -> id={todo_id}")

    # [SSOT] 매직 스트링 대신 TodoEvent 상수로 구독한다. (P1-3)
    event_bus.on(TodoEvent.CREATED, log_created)
    event_bus.on(TodoEvent.COMPLETED, log_completed)
    event_bus.on(TodoEvent.DELETED, log_deleted)

    print("[lifespan] EventBus 구독자 등록 완료")
    yield
    print("[lifespan] 앱 종료")


app = FastAPI(title="To-Do List Management App", lifespan=lifespan)

# [CORS] 프론트엔드(브라우저)에서 직접 호출할 수 있도록 허용한다.
# allow_origins="*" 와 allow_credentials=True 는 명세상 함께 쓸 수 없다.
# 현재 인증(쿠키/자격증명)을 사용하지 않으므로 credentials=False 가 올바르다.
# 추후 인증 도입 시 allow_origins 를 구체 도메인으로 명시한다. (P0-2)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/todos", response_model=List[Todo])
def get_todos(
    category: Optional[Category] = Query(default=None),
    priority: Optional[Priority] = Query(default=None),
    done: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    service: TodoService = Depends(get_service),
) -> List[Todo]:
    """할일 목록을 조회한다.

    query로 필터(category, priority, done)와 검색어(search)를 받는다.
    제목·설명 검색은 대소문자를 구분하지 않는다.
    """
    return service.get_todos(
        category=category, priority=priority, done=done, search=search
    )


@app.post("/todos", response_model=Todo, status_code=status.HTTP_201_CREATED)
def create_todo(
    data: TodoCreate,
    service: TodoService = Depends(get_service),
) -> Todo:
    """새 할일을 생성한다."""
    return service.create_todo(data)


@app.patch("/todos/{todo_id}", response_model=Todo)
def toggle_todo(
    todo_id: str,
    service: TodoService = Depends(get_service),
) -> Todo:
    """할일의 완료 상태를 토글한다.

    존재하지 않는 id면 404를 반환한다.
    """
    try:
        return service.toggle_done(todo_id)
    except TodoNotFoundError:
        # [SRP] 도메인 예외를 HTTP 계층 언어(404)로 번역한다. (P1-1)
        raise HTTPException(status_code=404, detail="Todo not found")


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: str,
    service: TodoService = Depends(get_service),
) -> None:
    """할일을 삭제한다. 성공 시 204(No Content)를 반환한다.

    존재하지 않는 id면 404를 반환한다.
    """
    try:
        service.delete_todo(todo_id)
    except TodoNotFoundError:
        # [SRP] 도메인 예외를 HTTP 계층 언어(404)로 번역한다. (P1-1)
        raise HTTPException(status_code=404, detail="Todo not found")
