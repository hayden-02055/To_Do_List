# Software Design Document (SDD)
## To-Do List Management App — v3

> Claude Code 작업 지시서 | OOP 과제용 | 작성일: 2026-06-06
> **v3 변경사항**: `FileRepository` 추가 (JSON 영구 저장) — OCP 실증

---

## v3 변경 요약

| 구분 | 내용 |
|---|---|
| 신규 파일 | `backend/repositories/file_repository.py` |
| 신규 파일 | `backend/data/todos.json` (자동 생성) |
| 수정 파일 | `backend/main.py` — 주입 저장소를 `FileRepository`로 교체 |
| 수정 파일 | `backend/repositories/__init__.py` — FileRepository export 추가 |
| 리팩터링 이력 | 섹션 6에 항목 추가 |
| **변경 없음** | 나머지 모든 파일 — OCP 원칙 증명 |

> **핵심 포인트**: `TodoService`, `interfaces/repository.py`, `tests/test_todo.py` 등
> 나머지 코드는 **단 한 줄도 수정하지 않는다.**
> 이것이 OCP(개방-폐쇄 원칙)의 실증이다 — 확장에는 열려 있고, 수정에는 닫혀 있다.

---

## 0. Claude Code 작업 지침

v2에서 아래 내용만 추가/수정한다. 나머지는 v2 그대로 유지.

- `file_repository.py` 신규 생성
- `main.py`의 저장소 주입 부분만 `FileRepository`로 교체
- 모든 클래스/메서드에 **docstring** 작성
- OOP 원칙 적용 위치에 **인라인 주석** 명시
- 코드는 **가독성** 우선

---

## 1. 적용 OOP 개념 전체 목록 (v3 업데이트)

| 개념 | 적용 위치 | 설명 |
|---|---|---|
| SRP | `TodoService`, `TodoRepository` | 서비스는 로직만, 저장소는 저장만 |
| **OCP** | `AbstractTodoRepository` | **MemoryRepository → FileRepository 교체로 실증** |
| LSP | `MemoryRepository`, `FileRepository` → `AbstractRepo` | 두 구현체 모두 추상 클래스를 완전히 대체 가능 |
| ISP | `IReadable / IWritable` | 읽기·쓰기 인터페이스 분리 |
| DIP | `Service → Abstract 의존` | 저장소 교체 시 Service 코드 무변경 증명 |
| Observer | `EventBus (on/emit)` | 할일 추가·완료·삭제 시 이벤트 발행/구독 |
| 캡슐화 | `TodoService._apply_filters()`, `FileRepository._load()/_save()` | 구현 세부사항 외부 은닉 |
| 리팩터링 | `TodoService.get_todos()`, 저장소 교체 | 기능 변경 없이 구조 개선 |
| Unit Test | `pytest (test_todo.py)` | 저장소 교체 후에도 테스트 무변경 — DIP 증명 |

---

## 2. 프로젝트 구조 (v3)

```
todo-app/
├── backend/
│   ├── main.py                          # ← FileRepository로 주입 교체
│   ├── models/
│   │   ├── __init__.py
│   │   ├── todo.py
│   │   └── enums.py
│   ├── interfaces/
│   │   ├── __init__.py
│   │   └── repository.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── todo_repository.py           # MemoryRepository — 그대로 유지 (OCP 증명)
│   │   └── file_repository.py           # ← 신규: FileRepository
│   ├── services/
│   │   ├── __init__.py
│   │   └── todo_service.py              # 변경 없음 (OCP, DIP 증명)
│   ├── events/
│   │   ├── __init__.py
│   │   └── event_system.py
│   ├── data/
│   │   └── todos.json                   # ← 자동 생성, 없으면 빈 파일로 초기화
│   └── tests/
│       ├── __init__.py
│       └── test_todo.py                 # 변경 없음 (DIP 증명)
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
└── README.md
```

---

## 3. 신규: `backend/repositories/file_repository.py`

**[OCP, LSP, 캡슐화 적용]**

`AbstractTodoRepository`를 상속하여 JSON 파일 기반 영구 저장소를 구현한다.
`MemoryRepository`와 동일한 인터페이스를 유지하므로 `TodoService` 코드 수정 없이 교체 가능하다.

```python
import json
import os
from typing import List, Optional
from models.todo import Todo
from interfaces.repository import AbstractTodoRepository

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/todos.json")

class FileRepository(AbstractTodoRepository):
    """
    [OCP] AbstractTodoRepository를 상속한 JSON 파일 기반 저장소.
          MemoryRepository 대신 이 클래스로 교체해도 TodoService는 수정 불필요.
    [LSP] MemoryRepository와 동일한 인터페이스 — 완전한 대체 가능.
    [캡슐화] 파일 읽기/쓰기 구현은 _load(), _save() private 메서드로 은닉.
             외부에서는 get_all(), save(), delete() 만 알면 됨.
    """

    def __init__(self, path: str = DATA_PATH):
        self._path = path          # [캡슐화] 파일 경로 외부 노출 차단
        self._ensure_file()        # 파일 없으면 빈 JSON으로 초기화

    # ── Public (AbstractTodoRepository 구현) ────────────

    def get_all(self) -> List[Todo]:
        """전체 할일 목록 반환"""
        return list(self._load().values())

    def get_by_id(self, todo_id: str) -> Optional[Todo]:
        """ID로 단건 조회"""
        return self._load().get(todo_id)

    def save(self, todo: Todo) -> Todo:
        """할일 저장 (신규 생성 / 수정 모두 처리)"""
        store = self._load()
        store[todo.id] = todo
        self._save(store)
        return todo

    def delete(self, todo_id: str) -> bool:
        """할일 삭제. 성공 시 True, 없으면 False 반환"""
        store = self._load()
        if todo_id not in store:
            return False
        del store[todo_id]
        self._save(store)
        return True

    # ── Private (캡슐화된 내부 로직) ────────────────────

    def _ensure_file(self) -> None:
        """
        [캡슐화] 데이터 파일 존재 여부 확인 및 초기화.
        data/ 디렉토리가 없으면 자동 생성.
        """
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        if not os.path.exists(self._path):
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load(self) -> dict[str, Todo]:
        """
        [캡슐화] JSON 파일에서 데이터 로드.
        외부에서 직접 호출 불가 — get_all(), get_by_id()를 통해서만 접근.
        """
        with open(self._path, "r", encoding="utf-8") as f:
            raw: dict = json.load(f)
        return {k: Todo.model_validate(v) for k, v in raw.items()}

    def _save(self, store: dict[str, Todo]) -> None:
        """
        [캡슐화] Todo 딕셔너리를 JSON 파일로 저장.
        외부에서 직접 호출 불가 — save(), delete()를 통해서만 호출됨.
        """
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.model_dump(mode="json") for k, v in store.items()},
                f,
                ensure_ascii=False,
                indent=2,
            )
```

---

## 4. 수정: `backend/main.py` — 저장소 주입 부분만 교체

기존 `MemoryTodoRepository` → `FileRepository`로 교체. **다른 코드는 건드리지 않는다.**

```python
# v2 (변경 전)
from repositories.todo_repository import MemoryTodoRepository

def get_repository():
    return MemoryTodoRepository()  # [OCP 변경 전]

# v3 (변경 후) — 이 두 줄만 바뀜
from repositories.file_repository import FileRepository

# [OCP] TodoService, 인터페이스, 테스트 코드 수정 없이 저장소만 교체
_repository = FileRepository()  # 앱 전역 단일 인스턴스

def get_repository() -> FileRepository:
    return _repository
```

> **주의**: `FileRepository`는 앱 시작 시 단일 인스턴스로 생성한다.
> 요청마다 새 인스턴스를 만들면 파일을 중복 읽게 되므로 싱글턴 패턴으로 관리.

---

## 5. 변경 없는 파일 목록 (OCP / DIP 증명)

아래 파일들은 **v3에서 단 한 줄도 수정하지 않는다.**
이것이 OCP와 DIP가 실제로 동작하고 있음을 증명한다.

| 파일 | 이유 |
|---|---|
| `interfaces/repository.py` | 추상 인터페이스는 구현체와 무관 |
| `services/todo_service.py` | 추상에 의존하므로 구현체 교체 영향 없음 (DIP) |
| `repositories/todo_repository.py` | MemoryRepository는 그대로 보존 (OCP — 기존 코드 수정 없음) |
| `tests/test_todo.py` | MockRepository 사용으로 저장소 교체 무관 (DIP) |
| `models/`, `events/`, `frontend/` | 저장소와 무관한 레이어 |

---

## 6. 리팩터링 이력 (v3 업데이트)

| 버전 | 대상 | 리팩터링 전 | 리팩터링 후 | 이유 |
|---|---|---|---|---|
| v2 | `TodoService.get_todos()` | 필터 조건 전부 인라인 | `_apply_filters()` + `_filter_by_*()` 분리 | 가독성·유지보수성·캡슐화 향상 |
| v2 | `app.js` 필터 로직 | `TodoApp` 내부에 혼재 | `FilterManager` 클래스로 분리 | SRP 위반 해소 |
| v2 | `TodoRenderer.createCard()` | public 메서드 | `#createCard()` private 전환 | 캡슐화 강화 |
| v2 | `FrontEventBus._listeners` | 일반 속성 | `#listeners` private 필드 | 캡슐화 강화 |
| **v3** | **`main.py` 저장소 주입** | **`MemoryRepository` 사용** | **`FileRepository`로 교체** | **OCP 실증 — 기존 코드 수정 없이 기능 확장** |
| **v3** | **`FileRepository._load/_save`** | **해당 없음 (신규)** | **private 메서드로 구현** | **파일 I/O 세부사항 캡슐화** |

---

## 7. 테스트 전략 (v3)

테스트 코드는 v2와 동일하다. `MockRepository`를 주입하므로 `FileRepository`로 교체해도 테스트는 그대로 통과한다. **이것이 DIP의 핵심 이점이다.**

```python
# test_todo.py — v3에서도 변경 없음
@pytest.fixture
def service():
    # [DIP] MockRepository 주입 — FileRepository와 무관하게 테스트 가능
    repo = MockTodoRepository()
    bus = EventBus()
    return TodoService(repo, bus)
```

FileRepository 자체의 파일 I/O 테스트가 필요하다면 아래 케이스를 **선택적으로** 추가한다.

```python
# 선택 추가 테스트 (test_file_repository.py 별도 파일)
def test_file_repository_persist()    # 저장 후 재로드 시 데이터 유지 확인
def test_file_repository_delete()     # 삭제 후 재로드 시 데이터 제거 확인
def test_file_repository_init()       # 파일 없을 때 자동 초기화 확인
```

---

## 8. 실행 방법 (README.md — v3 업데이트)

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

### 참고
- 할일 데이터는 backend/data/todos.json에 자동 저장됩니다.
- 서버를 재시작해도 데이터가 유지됩니다.
- todos.json을 삭제하면 초기화됩니다.
```

---

## 9. 구현 시 주의사항 (v3 추가)

1. **FileRepository 싱글턴**: 요청마다 새 인스턴스 생성 금지 — `main.py`에서 전역 단일 인스턴스 유지
2. **JSON 직렬화**: `datetime`, `Enum` 타입은 `model_dump(mode="json")`으로 직렬화
3. **파일 인코딩**: `encoding="utf-8"` 명시 — 한글 할일 제목 깨짐 방지
4. **data/ 디렉토리**: 서버 시작 시 없으면 자동 생성 (`_ensure_file()`에서 처리)
5. **OCP 주석 필수**: `main.py` 교체 부분에 `# [OCP]` 주석과 함께 변경 이유 명시
6. **MemoryRepository 삭제 금지**: OCP 증명을 위해 기존 구현체는 반드시 보존
