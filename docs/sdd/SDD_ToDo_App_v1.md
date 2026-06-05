# Software Design Document (SDD)
## To-Do List Management App

> Claude Code 작업 지시서 | OOP 과제용 | 작성일: 2026-06-06

---

## 0. Claude Code 작업 지침

이 문서를 기반으로 `todo-app/` 프로젝트를 생성한다.

- 언어: Python 3.11 (백엔드), HTML5/CSS3/Vanilla JS (프론트엔드)
- 프레임워크: FastAPI + Uvicorn
- OOP 원칙: SOLID 5원칙, Observer 패턴, 추상 클래스, 단위 테스트 **반드시 적용**
- 모든 클래스/메서드에 **docstring** 작성
- OOP 원칙 적용 위치에 **인라인 주석** 명시 (예: `# [SRP]`, `# [DIP]`)
- 코드는 **가독성** 우선, 과도한 압축 금지

---

## 1. 프로젝트 구조

아래 구조를 그대로 생성할 것.

```
todo-app/
├── backend/
│   ├── main.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── todo.py
│   │   └── enums.py
│   ├── interfaces/
│   │   ├── __init__.py
│   │   └── repository.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── todo_repository.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── todo_service.py
│   ├── events/
│   │   ├── __init__.py
│   │   └── event_system.py
│   └── tests/
│       ├── __init__.py
│       └── test_todo.py
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
└── README.md
```

---

## 2. 의존성

### requirements.txt
```
fastapi==0.111.0
uvicorn==0.29.0
pydantic==2.7.0
pytest==8.2.0
httpx==0.27.0
```

---

## 3. 백엔드 상세 설계

### 3.1 `backend/models/enums.py`

```python
from enum import Enum

class Category(str, Enum):
    WORK = "work"          # 업무
    PERSONAL = "personal"  # 개인
    STUDY = "study"        # 학습
    OTHER = "other"        # 기타

class Priority(str, Enum):
    HIGH = "high"      # 높음
    MEDIUM = "medium"  # 중간
    LOW = "low"        # 낮음
```

---

### 3.2 `backend/models/todo.py`

Pydantic BaseModel 사용. 아래 필드를 포함할 것.

| 필드 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `id` | `str` | `uuid4()` | 고유 식별자 |
| `title` | `str` | 필수 | 할일 제목 |
| `description` | `str` | `""` | 상세 설명 |
| `category` | `Category` | `Category.OTHER` | 카테고리 |
| `priority` | `Priority` | `Priority.MEDIUM` | 우선순위 |
| `due_date` | `Optional[datetime]` | `None` | 마감일 |
| `done` | `bool` | `False` | 완료 여부 |
| `created_at` | `datetime` | `now()` | 생성일시 |

**추가 모델:**
- `TodoCreate`: 생성 요청용 (id, done, created_at 제외)
- `TodoUpdate`: 수정 요청용 (모든 필드 Optional)

---

### 3.3 `backend/interfaces/repository.py`

**[ISP 적용]** 읽기/쓰기 인터페이스를 분리한다.

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from models.todo import Todo, TodoCreate

class IReadable(ABC):
    """[ISP] 읽기 전용 인터페이스"""

    @abstractmethod
    def get_all(self) -> List[Todo]: ...

    @abstractmethod
    def get_by_id(self, todo_id: str) -> Optional[Todo]: ...

class IWritable(ABC):
    """[ISP] 쓰기 전용 인터페이스"""

    @abstractmethod
    def save(self, todo: Todo) -> Todo: ...

    @abstractmethod
    def delete(self, todo_id: str) -> bool: ...

class AbstractTodoRepository(IReadable, IWritable, ABC):
    """[OCP] 확장을 위한 추상 저장소. 새 구현체 추가 시 이 클래스만 상속."""
    pass
```

---

### 3.4 `backend/repositories/todo_repository.py`

**[OCP, LSP 적용]** `AbstractTodoRepository`를 상속하는 인메모리 구현체.

```python
class MemoryTodoRepository(AbstractTodoRepository):
    """
    [LSP] AbstractTodoRepository를 완전히 대체 가능한 구현체.
    [OCP] DB 저장소로 교체 시 이 클래스만 새로 작성하면 됨.
    내부 저장소: Dict[str, Todo]
    """

    def __init__(self):
        self._store: dict[str, Todo] = {}  # [SRP] 저장 책임만 담당

    def get_all(self) -> List[Todo]: ...
    def get_by_id(self, todo_id: str) -> Optional[Todo]: ...
    def save(self, todo: Todo) -> Todo: ...
    def delete(self, todo_id: str) -> bool: ...
```

---

### 3.5 `backend/events/event_system.py`

**[Observer 패턴 적용]**

```python
from typing import Callable, Dict, List, Any

class EventBus:
    """
    Observer 패턴 구현체.
    발행자(Publisher)와 구독자(Subscriber)를 느슨하게 연결한다.

    사용 이벤트:
      - "todo.created"   : 할일 생성 시
      - "todo.completed" : 완료 토글 시
      - "todo.deleted"   : 삭제 시
    """

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable) -> None:
        """이벤트 구독 등록"""
        self._listeners.setdefault(event, []).append(callback)

    def emit(self, event: str, data: Any = None) -> None:
        """이벤트 발행 — 등록된 모든 콜백 실행"""
        for callback in self._listeners.get(event, []):
            callback(data)

# 싱글턴 인스턴스 (앱 전역 공유)
event_bus = EventBus()
```

---

### 3.6 `backend/services/todo_service.py`

**[SRP, DIP 적용]** 비즈니스 로직만 담당. 저장소는 주입받는다.

```python
class TodoService:
    """
    [SRP] 비즈니스 로직만 담당. 저장/삭제는 repository에 위임.
    [DIP] 구체 클래스(MemoryTodoRepository)가 아닌
          추상(AbstractTodoRepository)에 의존.
    """

    def __init__(self, repository: AbstractTodoRepository, bus: EventBus):
        # [DIP] 생성자 주입
        self._repo = repository
        self._bus = bus

    def create_todo(self, data: TodoCreate) -> Todo:
        """할일 생성 후 todo.created 이벤트 발행"""
        ...

    def get_todos(
        self,
        category: Optional[Category] = None,
        priority: Optional[Priority] = None,
        done: Optional[bool] = None
    ) -> List[Todo]:
        """필터 조건에 맞는 할일 목록 반환"""
        ...

    def toggle_done(self, todo_id: str) -> Todo:
        """완료 상태 토글 후 todo.completed 이벤트 발행"""
        ...

    def delete_todo(self, todo_id: str) -> None:
        """할일 삭제 후 todo.deleted 이벤트 발행"""
        ...
```

---

### 3.7 `backend/main.py`

FastAPI 앱 설정. 아래 사항을 반드시 포함할 것.

- `CORSMiddleware` 설정 (프론트엔드 연동용, `allow_origins=["*"]`)
- `lifespan` 이벤트로 EventBus 구독자 등록 (로깅 콜백)
- `Depends()`로 `TodoService` 의존성 주입
- 라우터 prefix: `/todos`

**엔드포인트:**

| Method | Path | 함수명 | 설명 |
|---|---|---|---|
| GET | `/todos` | `get_todos` | 목록 조회 (query: category, priority, done) |
| POST | `/todos` | `create_todo` | 생성 |
| PATCH | `/todos/{todo_id}` | `toggle_todo` | 완료 토글 |
| DELETE | `/todos/{todo_id}` | `delete_todo` | 삭제, 204 반환 |

---

### 3.8 `backend/tests/test_todo.py`

pytest 단위 테스트. **MockRepository**를 직접 정의하여 실제 저장소 없이 테스트.

아래 테스트 케이스를 반드시 구현할 것:

```python
# 테스트 케이스 목록
def test_create_todo()           # 할일 생성 후 목록에 존재하는지 확인
def test_create_todo_defaults()  # 기본값(done=False, priority=MEDIUM) 확인
def test_toggle_done()           # 완료 토글 True/False 전환 확인
def test_toggle_done_twice()     # 두 번 토글 시 원래 상태로 복귀 확인
def test_delete_todo()           # 삭제 후 목록에서 제거 확인
def test_delete_nonexistent()    # 존재하지 않는 id 삭제 시 예외 확인
def test_filter_by_category()    # 카테고리 필터 동작 확인
def test_filter_by_done()        # 완료 여부 필터 동작 확인
def test_event_emitted_on_create()    # 생성 시 이벤트 발행 확인
def test_event_emitted_on_delete()    # 삭제 시 이벤트 발행 확인
```

MockRepository 구현 예시:
```python
class MockTodoRepository(AbstractTodoRepository):
    """테스트용 인메모리 Mock 저장소"""
    def __init__(self):
        self._store: dict[str, Todo] = {}
    # AbstractTodoRepository 메서드 전부 구현
```

---

## 4. 프론트엔드 상세 설계

### 4.1 UI 레이아웃 (`frontend/index.html`)

전체 레이아웃 구조:

```
┌─────────────────────────────────────┐
│           Header (앱 제목)            │
├──────────────────┬──────────────────┤
│   Sidebar        │   Main Content   │
│  ┌────────────┐  │  ┌────────────┐  │
│  │ + 할일추가  │  │  │ 필터 바    │  │
│  │  폼        │  │  ├────────────┤  │
│  │ - 제목     │  │  │ Todo 카드  │  │
│  │ - 설명     │  │  │ Todo 카드  │  │
│  │ - 카테고리 │  │  │ Todo 카드  │  │
│  │ - 우선순위 │  │  │  ...       │  │
│  │ - 마감일   │  │  └────────────┘  │
│  │ [추가버튼] │  │                  │
│  └────────────┘  │                  │
└──────────────────┴──────────────────┘
```

**Todo 카드 요소:**
- 체크박스 (완료 토글)
- 제목 (완료 시 취소선)
- 카테고리 뱃지 (색상 구분)
- 우선순위 뱃지 (색상 구분)
- 마감일 + D-day 표시
- 삭제 버튼

---

### 4.2 디자인 명세 (`frontend/style.css`)

**컬러 팔레트:**

| 용도 | 색상 코드 |
|---|---|
| Primary | `#4F46E5` (인디고) |
| 완료 상태 | `#10B981` (에메랄드) |
| 삭제/위험 | `#EF4444` (레드) |
| 배경 | `#F8FAFC` |
| 카드 배경 | `#FFFFFF` |
| 텍스트 기본 | `#1E293B` |
| 텍스트 보조 | `#64748B` |

**우선순위 뱃지 색상:**

| 우선순위 | 배경 | 텍스트 |
|---|---|---|
| HIGH | `#FEE2E2` | `#DC2626` |
| MEDIUM | `#FEF3C7` | `#D97706` |
| LOW | `#DCFCE7` | `#16A34A` |

**카테고리 뱃지 색상:**

| 카테고리 | 배경 | 텍스트 |
|---|---|---|
| WORK | `#DBEAFE` | `#2563EB` |
| PERSONAL | `#F3E8FF` | `#7C3AED` |
| STUDY | `#FFEDD5` | `#EA580C` |
| OTHER | `#F1F5F9` | `#475569` |

**디자인 규칙:**
- 폰트: `'Pretendard', 'Noto Sans KR', sans-serif` (CDN)
- 카드 border-radius: `12px`
- 카드 box-shadow: `0 1px 3px rgba(0,0,0,0.1)`
- transition: `all 0.2s ease`
- 완료된 카드: `opacity: 0.6`, 제목에 `text-decoration: line-through`

---

### 4.3 JavaScript 설계 (`frontend/app.js`)

**OOP 클래스 구조로 작성할 것.**

```javascript
// [SRP] API 통신만 담당
class TodoAPI {
  constructor(baseURL = 'http://localhost:8000') { ... }
  async getAll(filters = {}) { ... }   // GET /todos?category=&priority=&done=
  async create(data) { ... }           // POST /todos
  async toggleDone(id) { ... }         // PATCH /todos/{id}
  async delete(id) { ... }             // DELETE /todos/{id}
}

// [Observer 패턴] 프론트엔드 이벤트 버스
class FrontEventBus {
  on(event, callback) { ... }
  emit(event, data) { ... }
}

// [SRP] DOM 렌더링만 담당
class TodoRenderer {
  constructor(containerId, eventBus) { ... }
  render(todos) { ... }          // 전체 목록 렌더링
  createCard(todo) { ... }       // 카드 DOM 생성
  getDdayText(dueDate) { ... }   // D-day 계산 및 텍스트 반환
}

// [SRP] 필터 UI 상태 관리
class FilterManager {
  constructor(eventBus) { ... }
  getFilters() { ... }           // 현재 필터 값 반환
  bindEvents() { ... }           // 필터 변경 이벤트 바인딩
}

// [SRP] 앱 전체 조율 (Facade)
class TodoApp {
  constructor() {
    this.api = new TodoAPI()
    this.bus = new FrontEventBus()
    this.renderer = new TodoRenderer('todo-list', this.bus)
    this.filter = new FilterManager(this.bus)
  }
  async init() { ... }           // 초기 데이터 로드
  async refresh() { ... }        // 필터 적용 후 재렌더링
  bindFormEvents() { ... }       // 추가 폼 이벤트 바인딩
}

// 앱 진입점
const app = new TodoApp()
app.init()
```

**프론트 이벤트 목록:**

| 이벤트명 | 발생 시점 | 처리 |
|---|---|---|
| `filter.changed` | 필터 드롭다운 변경 | 목록 재조회 |
| `todo.added` | 폼 제출 | 목록 갱신 |
| `todo.toggled` | 체크박스 클릭 | 카드 UI 갱신 |
| `todo.deleted` | 삭제 버튼 클릭 | 카드 제거 |

---

## 5. 실행 방법 (README.md 내용)

```markdown
## 실행 방법

### 1. 의존성 설치
pip install -r requirements.txt

### 2. 서버 실행
cd backend
uvicorn main:app --reload --port 8000

### 3. 프론트엔드 실행
frontend/index.html을 브라우저로 열기
(또는 Live Server 확장 사용)

### 4. 테스트 실행
cd backend
pytest tests/ -v
```

---

## 6. 구현 시 주의사항

1. **주석 필수**: 모든 클래스/메서드 docstring + OOP 원칙 인라인 주석
2. **타입 힌트**: 모든 함수 파라미터와 반환값에 타입 힌트 작성
3. **예외 처리**: 존재하지 않는 todo_id 접근 시 `404 HTTPException` 반환
4. **CORS**: 프론트-백 연동을 위해 반드시 CORSMiddleware 설정
5. **이벤트 로깅**: EventBus 구독자로 콘솔 로깅 콜백 등록 (Observer 패턴 시연)
6. **필터**: 프론트에서 query string으로 전달, 백엔드에서 처리
7. **D-day**: 프론트에서 `due_date`와 오늘 날짜 차이 계산하여 표시
