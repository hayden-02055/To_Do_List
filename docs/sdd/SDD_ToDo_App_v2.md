# Software Design Document (SDD)
## To-Do List Management App

> Claude Code 작업 지시서 | OOP 과제용 | 작성일: 2026-06-06

---

## 0. Claude Code 작업 지침

이 문서를 기반으로 `todo-app/` 프로젝트를 생성한다.

- 언어: Python 3.11 (백엔드), HTML5/CSS3/Vanilla JS (프론트엔드)
- 프레임워크: FastAPI + Uvicorn
- OOP 원칙: SOLID 5원칙, Observer 패턴, 캡슐화, 리팩터링 **반드시 적용 및 주석 명시**
- 모든 클래스/메서드에 **docstring** 작성
- OOP 원칙 적용 위치에 **인라인 주석** 명시 (예: `# [SRP]`, `# [캡슐화]`, `# [리팩터링]`)
- 코드는 **가독성** 우선, 과도한 압축 금지

---

## 1. 적용 OOP 개념 전체 목록

| 개념 | 적용 위치 | 설명 |
|---|---|---|
| SRP | `TodoService`, `TodoRepository` | 서비스는 로직만, 저장소는 저장만 |
| OCP | `AbstractTodoRepository` | 새 저장소 추가 시 기존 코드 수정 없이 확장 |
| LSP | `MemoryRepository → AbstractRepo` | 추상 클래스를 완전히 대체 가능한 구현체 |
| ISP | `IReadable / IWritable` | 읽기·쓰기 인터페이스 분리 |
| DIP | `Service → Abstract 의존` | 구체 클래스가 아닌 추상에 의존 |
| Observer | `EventBus (on/emit)` | 할일 추가·완료·삭제 시 이벤트 발행/구독 |
| **캡슐화** | `TodoService._apply_filters()` | 검색·필터 구현 세부사항을 외부에 은닉 |
| **리팩터링** | `TodoService.get_todos()` | 필터 파이프라인을 단계별 private 메서드로 분리 |
| Unit Test | `pytest (test_todo.py)` | 리팩터링 전후 동작 보장 |

---

## 2. 프로젝트 구조

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

## 3. 의존성

### requirements.txt
```
fastapi==0.111.0
uvicorn==0.29.0
pydantic==2.7.0
pytest==8.2.0
httpx==0.27.0
```

---

## 4. 백엔드 상세 설계

### 4.1 `backend/models/enums.py`

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

### 4.2 `backend/models/todo.py`

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

### 4.3 `backend/interfaces/repository.py`

**[ISP 적용]** 읽기/쓰기 인터페이스를 분리한다.

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from models.todo import Todo

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

### 4.4 `backend/repositories/todo_repository.py`

**[OCP, LSP 적용]** `AbstractTodoRepository`를 상속하는 인메모리 구현체.

```python
class MemoryTodoRepository(AbstractTodoRepository):
    """
    [LSP] AbstractTodoRepository를 완전히 대체 가능한 구현체.
    [OCP] DB 저장소로 교체 시 이 클래스만 새로 작성하면 됨.
    내부 저장소: Dict[str, Todo]
    """

    def __init__(self):
        self._store: dict[str, Todo] = {}  # [캡슐화] 외부에서 직접 접근 불가

    def get_all(self) -> List[Todo]: ...
    def get_by_id(self, todo_id: str) -> Optional[Todo]: ...
    def save(self, todo: Todo) -> Todo: ...
    def delete(self, todo_id: str) -> bool: ...
```

---

### 4.5 `backend/events/event_system.py`

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
        self._listeners: Dict[str, List[Callable]] = {}  # [캡슐화] 외부 직접 접근 차단

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

### 4.6 `backend/services/todo_service.py` ⭐ 핵심

**[SRP, DIP, 캡슐화, 리팩터링 적용]**

검색 및 필터 로직은 외부에 노출하지 않고 `_apply_filters()` private 메서드로 캡슐화한다.
초기에는 `get_todos()` 안에 모든 로직이 있었으나, 필터 조건 증가로 인해 단계별 private 메서드로 **리팩터링**하였다.

```python
class TodoService:
    """
    [SRP] 비즈니스 로직만 담당. 저장/삭제는 repository에 위임.
    [DIP] 구체 클래스가 아닌 추상(AbstractTodoRepository)에 의존.
    """

    def __init__(self, repository: AbstractTodoRepository, bus: EventBus):
        # [DIP] 생성자 주입
        self._repo = repository   # [캡슐화] private 속성
        self._bus = bus           # [캡슐화] private 속성

    # ── Public API ──────────────────────────────────────

    def create_todo(self, data: TodoCreate) -> Todo:
        """할일 생성 후 todo.created 이벤트 발행"""
        ...

    def get_todos(
        self,
        category: Optional[Category] = None,
        priority: Optional[Priority] = None,
        done: Optional[bool] = None,
        search: Optional[str] = None,       # 검색어 파라미터 추가
    ) -> List[Todo]:
        """
        필터 + 검색 조건에 맞는 할일 목록 반환.
        [리팩터링] 초기 단일 함수였던 필터 로직을 _apply_filters()로 분리.
        호출자는 내부 필터 구현을 알 필요 없음. [캡슐화]
        """
        todos = self._repo.get_all()
        return self._apply_filters(todos, category, priority, done, search)

    def toggle_done(self, todo_id: str) -> Todo:
        """완료 상태 토글 후 todo.completed 이벤트 발행"""
        ...

    def delete_todo(self, todo_id: str) -> None:
        """할일 삭제 후 todo.deleted 이벤트 발행"""
        ...

    # ── Private (캡슐화된 내부 로직) ────────────────────

    def _apply_filters(
        self,
        todos: List[Todo],
        category: Optional[Category],
        priority: Optional[Priority],
        done: Optional[bool],
        search: Optional[str],
    ) -> List[Todo]:
        """
        [캡슐화] 필터·검색 구현 세부사항을 외부에 은닉.
        [리팩터링] 각 필터 조건을 독립 private 메서드로 분리하여
                   조건 추가/변경 시 해당 메서드만 수정하면 됨. (OCP)
        """
        todos = self._filter_by_category(todos, category)
        todos = self._filter_by_priority(todos, priority)
        todos = self._filter_by_done(todos, done)
        todos = self._filter_by_search(todos, search)
        return todos

    def _filter_by_category(self, todos: List[Todo], category: Optional[Category]) -> List[Todo]:
        """[캡슐화] 카테고리 필터 — 외부 노출 없이 내부에서만 사용"""
        if category is None:
            return todos
        return [t for t in todos if t.category == category]

    def _filter_by_priority(self, todos: List[Todo], priority: Optional[Priority]) -> List[Todo]:
        """[캡슐화] 우선순위 필터"""
        if priority is None:
            return todos
        return [t for t in todos if t.priority == priority]

    def _filter_by_done(self, todos: List[Todo], done: Optional[bool]) -> List[Todo]:
        """[캡슐화] 완료 여부 필터"""
        if done is None:
            return todos
        return [t for t in todos if t.done == done]

    def _filter_by_search(self, todos: List[Todo], search: Optional[str]) -> List[Todo]:
        """
        [캡슐화] 검색 필터 — title과 description에서 키워드 검색.
        [리팩터링] 초기에는 get_todos() 내부 인라인 코드였으나
                   독립 메서드로 분리하여 가독성·재사용성 향상.
        대소문자 구분 없이 검색 (casefold 적용).
        """
        if not search:
            return todos
        keyword = search.casefold()
        return [
            t for t in todos
            if keyword in t.title.casefold()
            or keyword in t.description.casefold()
        ]
```

> **리팩터링 포인트 설명**
>
> 초기 버전의 `get_todos()`는 아래처럼 하나의 함수 안에 모든 필터 조건이 인라인으로 작성되어 있었다.
>
> ```python
> # 리팩터링 이전 (Bad)
> def get_todos(self, category, priority, done, search):
>     todos = self._repo.get_all()
>     if category: todos = [t for t in todos if t.category == category]
>     if priority: todos = [t for t in todos if t.priority == priority]
>     if done is not None: todos = [t for t in todos if t.done == done]
>     if search: todos = [t for t in todos if search in t.title or search in t.description]
>     return todos
> ```
>
> 검색 조건이 추가될수록 함수 길이가 늘어나고, 각 필터 로직의 책임이 불분명해진다.
> 이를 `_apply_filters()` + 각 `_filter_by_*()` 메서드로 분리하여:
> - **가독성**: `get_todos()`가 파이프라인 구조로 한눈에 파악 가능
> - **유지보수성**: 검색 로직 변경 시 `_filter_by_search()`만 수정
> - **캡슐화**: 필터 구현 세부사항이 외부에 노출되지 않음
> - **테스트 용이성**: 각 필터를 독립적으로 단위 테스트 가능

---

### 4.7 `backend/main.py`

FastAPI 앱 설정.

- `CORSMiddleware` 설정 (`allow_origins=["*"]`)
- `lifespan` 이벤트로 EventBus 구독자 등록 (로깅 콜백)
- `Depends()`로 `TodoService` 의존성 주입
- 라우터 prefix: `/todos`

**엔드포인트:**

| Method | Path | 설명 | Query Params |
|---|---|---|---|
| GET | `/todos` | 목록 조회 | `category`, `priority`, `done`, `search` |
| POST | `/todos` | 생성 | - |
| PATCH | `/todos/{todo_id}` | 완료 토글 | - |
| DELETE | `/todos/{todo_id}` | 삭제, 204 반환 | - |

---

### 4.8 `backend/tests/test_todo.py`

pytest 단위 테스트. `MockRepository`로 실제 저장소 없이 테스트.
**리팩터링 전후 동작이 동일함을 보장하는 역할**도 명시할 것.

```python
# MockRepository
class MockTodoRepository(AbstractTodoRepository):
    """[DIP] 테스트용 Mock 저장소 — 실제 저장소 없이 Service 테스트 가능"""
    def __init__(self):
        self._store: dict[str, Todo] = {}
    # AbstractTodoRepository 전체 메서드 구현

# 테스트 케이스
def test_create_todo()                  # 생성 후 목록 존재 확인
def test_create_todo_defaults()         # 기본값 확인 (done=False, priority=MEDIUM)
def test_toggle_done()                  # 완료 토글 True 전환
def test_toggle_done_twice()            # 두 번 토글 시 원래 상태 복귀
def test_delete_todo()                  # 삭제 후 목록 제거 확인
def test_delete_nonexistent()           # 없는 id 삭제 시 404 예외
def test_filter_by_category()           # 카테고리 필터 동작
def test_filter_by_done()               # 완료 여부 필터 동작
def test_search_by_title()              # 제목 키워드 검색
def test_search_by_description()        # 설명 키워드 검색
def test_search_case_insensitive()      # 대소문자 구분 없이 검색
def test_search_no_result()             # 검색 결과 없을 때 빈 리스트
def test_filter_and_search_combined()   # 필터 + 검색 동시 적용
def test_event_emitted_on_create()      # 생성 이벤트 발행 확인
def test_event_emitted_on_delete()      # 삭제 이벤트 발행 확인
```

---

## 5. 프론트엔드 상세 설계

### 5.1 UI 레이아웃 (`frontend/index.html`)

```
┌─────────────────────────────────────┐
│           Header (앱 제목)            │
├──────────────────┬──────────────────┤
│   Sidebar        │   Main Content   │
│  ┌────────────┐  │  ┌────────────┐  │
│  │ + 할일추가  │  │  │🔍 검색창   │  │
│  │  폼        │  │  ├────────────┤  │
│  │ - 제목     │  │  │ 필터 바    │  │
│  │ - 설명     │  │  ├────────────┤  │
│  │ - 카테고리 │  │  │ Todo 카드  │  │
│  │ - 우선순위 │  │  │ Todo 카드  │  │
│  │ - 마감일   │  │  │  ...       │  │
│  │ [추가버튼] │  │  └────────────┘  │
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

### 5.2 디자인 명세 (`frontend/style.css`)

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

**우선순위 뱃지:**

| 우선순위 | 배경 | 텍스트 |
|---|---|---|
| HIGH | `#FEE2E2` | `#DC2626` |
| MEDIUM | `#FEF3C7` | `#D97706` |
| LOW | `#DCFCE7` | `#16A34A` |

**카테고리 뱃지:**

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

### 5.3 JavaScript 설계 (`frontend/app.js`)

**[SRP, 캡슐화, Observer 패턴 적용] OOP 클래스 구조로 작성할 것.**

```javascript
// [SRP] API 통신만 담당 / [캡슐화] baseURL을 외부에 노출하지 않음
class TodoAPI {
  #baseURL  // private 필드 (캡슐화)

  constructor(baseURL = 'http://localhost:8000') {
    this.#baseURL = baseURL
  }

  async getAll(filters = {}) { ... }  // GET /todos?category=&priority=&done=&search=
  async create(data) { ... }          // POST /todos
  async toggleDone(id) { ... }        // PATCH /todos/{id}
  async delete(id) { ... }            // DELETE /todos/{id}
}

// [Observer 패턴] 프론트엔드 이벤트 버스
// [캡슐화] _listeners를 외부에서 직접 접근 불가
class FrontEventBus {
  #listeners = {}

  on(event, callback) { ... }
  emit(event, data) { ... }
}

// [SRP] DOM 렌더링만 담당
class TodoRenderer {
  constructor(containerId, eventBus) { ... }
  render(todos) { ... }           // 전체 목록 렌더링
  #createCard(todo) { ... }       // [캡슐화] 카드 DOM 생성 — 내부 전용
  #getDdayText(dueDate) { ... }   // [캡슐화] D-day 계산 — 내부 전용
}

// [SRP] 필터·검색 UI 상태 관리
// [리팩터링] 초기에는 TodoApp 안에 있던 필터 로직을 별도 클래스로 분리
class FilterManager {
  #eventBus   // [캡슐화]

  constructor(eventBus) { ... }
  getFilters() { ... }      // { category, priority, done, search } 반환
  bindEvents() { ... }      // 필터·검색창 변경 이벤트 바인딩
}

// [SRP] 앱 전체 조율 (Facade 패턴)
class TodoApp {
  constructor() {
    this.api      = new TodoAPI()
    this.bus      = new FrontEventBus()
    this.renderer = new TodoRenderer('todo-list', this.bus)
    this.filter   = new FilterManager(this.bus)
  }

  async init() { ... }          // 초기 데이터 로드
  async refresh() { ... }       // 필터·검색 적용 후 재렌더링
  bindFormEvents() { ... }      // 추가 폼 이벤트 바인딩
}

const app = new TodoApp()
app.init()
```

**프론트 이벤트 목록:**

| 이벤트명 | 발생 시점 | 처리 |
|---|---|---|
| `filter.changed` | 필터 드롭다운 변경 | 목록 재조회 |
| `search.changed` | 검색창 입력 (`oninput`) | 목록 재조회 |
| `todo.added` | 폼 제출 | 목록 갱신 |
| `todo.toggled` | 체크박스 클릭 | 카드 UI 갱신 |
| `todo.deleted` | 삭제 버튼 클릭 | 카드 제거 |

---

## 6. 리팩터링 이력

> 보고서 작성 시 이 섹션을 그대로 활용할 것.

| 대상 | 리팩터링 전 | 리팩터링 후 | 이유 |
|---|---|---|---|
| `TodoService.get_todos()` | 필터 조건 전부 인라인 | `_apply_filters()` + `_filter_by_*()` 분리 | 가독성·유지보수성·캡슐화 향상 |
| `app.js` 필터 로직 | `TodoApp` 내부에 혼재 | `FilterManager` 클래스로 분리 | SRP 위반 해소 |
| `TodoRenderer.createCard()` | public 메서드 | `#createCard()` private 전환 | 외부 호출 차단, 캡슐화 강화 |
| `FrontEventBus._listeners` | 일반 속성 | `#listeners` private 필드 | 직접 접근 방지, 캡슐화 강화 |

---

## 7. 실행 방법 (README.md 내용)

```markdown
## 실행 방법

### 1. 의존성 설치
pip install -r requirements.txt

### 2. 서버 실행
cd backend
uvicorn main:app --reload --port 8000

### 3. 프론트엔드 실행
frontend/index.html을 브라우저로 열기 (또는 Live Server 사용)

### 4. 테스트 실행
cd backend
pytest tests/ -v
```

---

## 8. 구현 시 주의사항

1. **주석 필수**: 모든 클래스/메서드 docstring + OOP 원칙 인라인 주석
2. **타입 힌트**: 모든 함수 파라미터와 반환값에 타입 힌트 작성
3. **예외 처리**: 존재하지 않는 todo_id 접근 시 `404 HTTPException` 반환
4. **CORS**: 프론트-백 연동을 위해 반드시 `CORSMiddleware` 설정
5. **이벤트 로깅**: EventBus 구독자로 콘솔 로깅 콜백 등록 (Observer 패턴 시연)
6. **검색**: `oninput` 이벤트로 실시간 검색, `casefold()`로 대소문자 무시
7. **D-day**: 프론트에서 `due_date`와 오늘 날짜 차이 계산하여 표시
8. **캡슐화 명시**: Python은 `_` prefix, JS는 `#` private 필드로 구분
9. **리팩터링 주석**: 리팩터링된 메서드에 `# [리팩터링]` 주석과 이유 명시
