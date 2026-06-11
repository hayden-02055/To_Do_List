# Software Design Document (SDD)
## To-Do List Management App — v4

> Claude Code 작업 지시서 | OOP 과제용 | 작성일: 2026-06-11
> **v4 변경사항**: 예외처리 강화 + 이를 명분으로 한 구조적 리팩터링

---

## v4 변경 요약

| 구분 | 파일 | 내용 |
|---|---|---|
| 수정 | `backend/errors.py` | 도메인 예외 계층 확장 — `FileIOError` 추가 |
| 수정 | `backend/repositories/file_repository.py` | `_load` / `_save` I/O 예외처리 + `_load` 책임 분리 리팩터링 |
| 수정 | `backend/main.py` | `create_todo` 엔드포인트 예외처리 추가 (비대칭 해소) |
| 수정 | `frontend/app.js` | `TODO_TOGGLED` / `TODO_DELETED` try/catch 추가 |
| **변경 없음** | 나머지 모든 파일 | `TodoService`, 인터페이스, 테스트 — 무변경 |

> **리팩터링 의도**: 예외처리 추가는 단순 방어 코드가 아니다.
> I/O 오류를 도메인 언어(`FileIOError`)로 격상시키고,
> `_load()`의 파일 읽기 책임과 역직렬화 책임을 분리함으로써
> SRP와 캡슐화를 한 단계 더 실증한다.

---

## 0. Claude Code 작업 지침

v3에서 아래 내용만 추가/수정한다. 나머지는 v3 그대로 유지.

- 모든 클래스/메서드에 **docstring** 유지
- OOP 원칙 적용 위치에 **인라인 주석** 명시
- 리팩터링 전/후 구조가 코드에 주석으로 드러나야 함
- 코드는 **가독성** 우선

---

## 1. 적용 OOP 개념 전체 목록 (v4 업데이트)

| 개념 | 적용 위치 | 설명 |
|---|---|---|
| SRP | `TodoService`, `TodoRepository` | 서비스는 로직만, 저장소는 저장만 |
| SRP | **`FileRepository._load()` 분리** | **파일 읽기 / 역직렬화 책임을 private 메서드로 각각 분리 (v4 신규)** |
| OCP | `AbstractTodoRepository` | MemoryRepository → FileRepository 교체로 실증 |
| LSP | `MemoryRepository`, `FileRepository` → `AbstractRepo` | 두 구현체 모두 추상 클래스를 완전히 대체 가능 |
| ISP | `IReadable / IWritable` | 읽기·쓰기 인터페이스 분리 |
| DIP | `Service → Abstract 의존` | 저장소 교체 시 Service 코드 무변경 증명 |
| Observer | `EventBus (on/emit)` | 할일 추가·완료·삭제 시 이벤트 발행/구독 |
| 캡슐화 | `TodoService._apply_filters()`, `FileRepository._load()/_save()` | 구현 세부사항 외부 은닉 |
| **도메인 예외** | **`errors.py` — `FileIOError` 추가** | **I/O 오류를 도메인 언어로 격상 (v4 신규)** |
| 리팩터링 | `TodoService.get_todos()`, 저장소 교체, **`_load` 책임 분리** | 기능 변경 없이 구조 개선 |
| Unit Test | `pytest (test_todo.py)` | 저장소 교체 후에도 테스트 무변경 — DIP 증명 |

---

## 2. 프로젝트 구조 (v4 — 변경 없음)

v3와 동일. 파일 추가/삭제 없음.

---

## 3. 수정: `backend/errors.py` — 도메인 예외 계층 확장

`FileIOError`를 추가한다. 파이썬 내장 `OSError`/`JSONDecodeError`를 그대로 노출하지 않고
도메인 언어로 한 번 감싸서 서비스 계층이 저장 매체의 세부사항에 의존하지 않게 한다.

```python
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
```

---

## 4. 수정: `backend/repositories/file_repository.py`

### 변경 포인트 2가지

**① 예외처리 강화**: `_load` / `_save` I/O 예외를 `FileIOError`로 변환  
**② SRP 리팩터링**: `_load`에 뭉쳐 있던 "파일 읽기"와 "역직렬화" 책임을 `_read_raw` / `_deserialize`로 분리

```python
"""JSON 파일 기반 영구 저장소 구현 모듈 (v4 업데이트).

[OCP] AbstractTodoRepository를 상속하므로, 상위 계층(TodoService) 코드를
      수정하지 않고도 MemoryTodoRepository를 이 구현체로 교체할 수 있다.
[캡슐화] 파일 입출력 세부사항(_load/_save)을 private 메서드로 은닉한다.
[v4 리팩터링] _load()의 두 책임(파일 읽기 / 역직렬화)을 _read_raw()와
              _deserialize()로 분리한다. (SRP 강화)
"""

import json
import os
from typing import List, Optional

from errors import FileIOError
from interfaces.repository import AbstractTodoRepository
from models.todo import Todo

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "todos.json")


class FileRepository(AbstractTodoRepository):
    """[OCP] AbstractTodoRepository를 상속한 JSON 파일 기반 저장소.

    MemoryTodoRepository 대신 이 클래스로 교체해도 TodoService는 수정 불필요.

    [LSP] MemoryTodoRepository와 동일한 인터페이스를 제공하므로,
          상위 계층은 추상 타입만 알면 안전하게 치환된다.
    [캡슐화] 파일 읽기/쓰기 구현은 _load(), _save() private 메서드로 은닉한다.
             외부에서는 get_all(), get_by_id(), save(), delete() 만 알면 된다.

    v4 리팩터링 요약:
        Before: _load()가 파일 읽기 + 역직렬화를 동시에 담당 (SRP 위반)
        After:  _read_raw() — 파일 읽기만 담당
                _deserialize() — dict → Todo 변환만 담당
                _load() — 두 메서드를 조율하는 파이프라인 역할
    """

    def __init__(self, path: str = DATA_PATH) -> None:
        """저장소를 초기화한다.

        Args:
            path: JSON 데이터 파일 경로. 기본값은 backend/data/todos.json.
        """
        self._path = path
        self._ensure_file()

    # ── Public (AbstractTodoRepository 구현) ──────────────────────

    def get_all(self) -> List[Todo]:
        """저장된 모든 할일을 리스트로 반환한다."""
        return list(self._load().values())

    def get_by_id(self, todo_id: str) -> Optional[Todo]:
        """id로 할일 한 건을 조회한다. 없으면 None을 반환한다."""
        return self._load().get(todo_id)

    def save(self, todo: Todo) -> Todo:
        """할일을 저장한다(신규 생성·갱신 모두 처리).

        Raises:
            FileIOError: 파일 쓰기에 실패했을 때.
        """
        store = self._load()
        store[todo.id] = todo
        self._save(store)
        return todo

    def delete(self, todo_id: str) -> bool:
        """id에 해당하는 할일을 삭제한다.

        Returns:
            삭제에 성공하면 True, 대상이 없으면 False.

        Raises:
            FileIOError: 파일 쓰기에 실패했을 때.
        """
        store = self._load()
        if todo_id not in store:
            return False
        del store[todo_id]
        self._save(store)
        return True

    # ── Private (캡슐화된 내부 로직) ──────────────────────────────

    def _ensure_file(self) -> None:
        """[캡슐화] 데이터 파일 존재 여부를 확인하고 초기화한다.

        data/ 디렉토리가 없으면 자동 생성하고,
        파일이 없으면 빈 JSON({})으로 초기화한다.
        """
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        if not os.path.exists(self._path):
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load(self) -> dict[str, Todo]:
        """[캡슐화] JSON 파일에서 데이터를 로드하고 Todo 객체로 변환한다.

        [v4 리팩터링 - SRP]
        리팩터링 이전(Bad):
            이 메서드가 '파일 읽기'와 '역직렬화(dict→Todo)'를 동시에 담당.
            두 가지 변경 이유가 존재하므로 SRP 위반.

        리팩터링 이후(Good):
            _read_raw()  — 파일에서 raw dict 읽기만 담당
            _deserialize() — raw dict → Todo 변환만 담당
            _load()      — 두 메서드를 조율하는 파이프라인 역할 (Facade)
        """
        raw = self._read_raw()
        return self._deserialize(raw)

    def _read_raw(self) -> dict:
        """[캡슐화 / SRP] JSON 파일을 읽어 raw dict를 반환한다.

        파일 I/O와 JSON 파싱 실패를 FileIOError로 변환한다.

        리팩터링 이전(Bad):
            _load() 내부에 open()과 json.load()가 try/except 없이 인라인.
            OSError / JSONDecodeError가 서비스 계층까지 그대로 올라옴.

        리팩터링 이후(Good):
            내장 예외를 도메인 예외(FileIOError)로 변환해서 던짐.
            폴백 정책(빈 dict 반환)도 이 메서드 안에서만 결정.

        Returns:
            파일 내용을 담은 raw dict. 읽기 실패 시 빈 dict를 반환한다.
        """
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # 파일이 깨졌을 때 — 빈 dict로 폴백하고 경고 출력
            print(f"[FileRepository] 경고: JSON 파싱 실패, 빈 상태로 복구합니다. ({e})")
            return {}
        except OSError as e:
            # 파일을 아예 읽을 수 없을 때 — 도메인 예외로 변환
            raise FileIOError("load", e) from e

    def _deserialize(self, raw: dict) -> dict[str, Todo]:
        """[캡슐화 / SRP] raw dict를 Todo 객체 dict로 변환한다.

        [v4 신규] _load()에서 분리된 역직렬화 전담 메서드.
        파일 I/O와 완전히 분리되어 있으므로, 역직렬화 로직이 바뀌어도
        _read_raw()를 건드리지 않아도 된다. (SRP)

        Args:
            raw: JSON 파일에서 읽은 raw dict.

        Returns:
            {id: Todo} 형태의 dict.
        """
        return {k: Todo.model_validate(v) for k, v in raw.items()}

    def _save(self, store: dict[str, Todo]) -> None:
        """[캡슐화] Todo 딕셔너리를 JSON 파일로 저장한다.

        [v4 업데이트] OSError를 FileIOError로 변환해서 던진다.
        조용히 실패하는 것보다 명시적으로 실패하는 것이 데이터 유실 방지에 낫다.

        리팩터링 이전(Bad):
            예외처리 없음 — 디스크 꽉 참, 권한 없음 등의 상황에서
            조용히 실패하고 데이터가 유실될 수 있음.

        리팩터링 이후(Good):
            OSError → FileIOError로 변환해서 상위로 전파.
            상위 계층(API)이 500 에러와 메시지를 사용자에게 전달할 수 있음.

        Raises:
            FileIOError: 파일 쓰기에 실패했을 때.
        """
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(
                    {k: v.model_dump(mode="json") for k, v in store.items()},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except OSError as e:
            raise FileIOError("save", e) from e
```

---

## 5. 수정: `backend/main.py` — 예외처리 비대칭 해소

### 변경 포인트

`create_todo` 엔드포인트에 예외처리를 추가한다.
`toggle_done` / `delete_todo`는 이미 감싸져 있는데 `create_todo`만 빠져 있어서
API 계층의 예외처리 패턴이 비대칭이다.

```python
# imports에 FileIOError 추가
from errors import TodoNotFoundError, FileIOError


@app.post("/todos", response_model=Todo, status_code=status.HTTP_201_CREATED)
def create_todo(
    data: TodoCreate,
    service: TodoService = Depends(get_service),
) -> Todo:
    """새 할일을 생성한다.

    [v4] FileIOError 발생 시 503(서비스 불가)을 반환한다.
    toggle_done / delete_todo와 예외처리 패턴을 통일한다.

    리팩터링 이전(Bad):
        예외처리 없음 — FileRepository._save()가 실패하면
        FastAPI가 500을 반환하지만 클라이언트에 아무 메시지도 없음.

    리팩터링 이후(Good):
        FileIOError를 잡아 503으로 번역.
        [SRP] 도메인 예외 → HTTP 상태 코드 번역 책임을 API 계층이 담당.
    """
    try:
        return service.create_todo(data)
    except FileIOError as e:
        # [SRP] 도메인 예외를 HTTP 계층 언어(503)로 번역한다.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"데이터 저장에 실패했습니다: {e}",
        )


@app.patch("/todos/{todo_id}", response_model=Todo)
def toggle_todo(
    todo_id: str,
    service: TodoService = Depends(get_service),
) -> Todo:
    """할일의 완료 상태를 토글한다.

    [v4] FileIOError 예외처리 추가.
    """
    try:
        return service.toggle_done(todo_id)
    except TodoNotFoundError:
        raise HTTPException(status_code=404, detail="Todo not found")
    except FileIOError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"데이터 저장에 실패했습니다: {e}",
        )


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    todo_id: str,
    service: TodoService = Depends(get_service),
) -> None:
    """할일을 삭제한다.

    [v4] FileIOError 예외처리 추가.
    """
    try:
        service.delete_todo(todo_id)
    except TodoNotFoundError:
        raise HTTPException(status_code=404, detail="Todo not found")
    except FileIOError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"데이터 저장에 실패했습니다: {e}",
        )
```

> **주의**: import 라인에 `FileIOError` 추가 잊지 말 것.
> `from errors import TodoNotFoundError, FileIOError`

---

## 6. 수정: `frontend/app.js` — try/catch 비대칭 해소

`TODO_TOGGLED` / `TODO_DELETED` 이벤트 핸들러에 try/catch가 없다.
`TODO_SUBMITTED`와 `refresh()`는 이미 감싸져 있어 패턴이 비대칭이다.

```javascript
bindBusEvents() {
    this.bus.on(FrontEvent.FILTER_CHANGED, () => this.refresh());
    this.bus.on(FrontEvent.SEARCH_CHANGED, () => this.refresh());

    this.bus.on(FrontEvent.TODO_SUBMITTED, async (data) => {
        try {
            await this.api.create(data);
            await this.refresh();
        } catch (err) {
            console.error(err);
            alert('할일 추가에 실패했습니다.');
        }
    });

    // [v4] try/catch 추가 — TODO_SUBMITTED와 패턴 통일
    // 리팩터링 이전(Bad):
    //   await this.api.toggleDone(id);  // 예외 터지면 unhandled rejection
    //   await this.refresh();
    // 리팩터링 이후(Good): 서버 503 등 에러를 잡아 사용자에게 안내
    this.bus.on(FrontEvent.TODO_TOGGLED, async (id) => {
        try {
            await this.api.toggleDone(id);
            await this.refresh();
        } catch (err) {
            console.error(err);
            alert('완료 상태 변경에 실패했습니다.');
        }
    });

    // [v4] try/catch 추가 — TODO_SUBMITTED와 패턴 통일
    this.bus.on(FrontEvent.TODO_DELETED, async (id) => {
        try {
            await this.api.delete(id);
            await this.refresh();
        } catch (err) {
            console.error(err);
            alert('삭제에 실패했습니다.');
        }
    });
}
```

---

## 7. 변경 없는 파일 목록 (v4 — OCP / DIP 증명 계속)

| 파일 | 이유 |
|---|---|
| `interfaces/repository.py` | 추상 인터페이스는 구현체와 무관 |
| `services/todo_service.py` | `FileIOError`는 저장소에서 터지고 API 계층이 잡음 — 서비스 무관 |
| `repositories/todo_repository.py` | MemoryRepository는 그대로 보존 (OCP) |
| `tests/test_todo.py` | MockRepository 사용으로 FileIOError 발생 경로와 무관 |
| `models/`, `events/`, `frontend/index.html`, `style.css` | 변경 범위 밖 |

---

## 8. 리팩터링 이력 (v4 업데이트)

| 버전 | 대상 | 리팩터링 전 | 리팩터링 후 | OOP 원칙 |
|---|---|---|---|---|
| v2 | `TodoService.get_todos()` | 필터 조건 인라인 | `_apply_filters()` + `_filter_by_*()` 분리 | SRP, 캡슐화 |
| v2 | `app.js` 필터 로직 | `TodoApp` 내부에 혼재 | `FilterManager` 클래스로 분리 | SRP |
| v2 | `TodoRenderer.createCard()` | public 메서드 | `#createCard()` private 전환 | 캡슐화 |
| v2 | `FrontEventBus._listeners` | 일반 속성 | `#listeners` private 필드 | 캡슐화 |
| v3 | `main.py` 저장소 주입 | `MemoryRepository` | `FileRepository`로 교체 | OCP |
| v3 | `FileRepository._load/_save` | 신규 구현 | private 메서드로 구현 | 캡슐화 |
| **v4** | **`FileRepository._load()`** | **파일 읽기 + 역직렬화 혼재** | **`_read_raw()` / `_deserialize()` 분리** | **SRP** |
| **v4** | **`FileRepository._read_raw()`** | **예외처리 없음** | **JSONDecodeError → 폴백, OSError → FileIOError** | **도메인 예외** |
| **v4** | **`FileRepository._save()`** | **예외처리 없음** | **OSError → FileIOError로 변환** | **도메인 예외** |
| **v4** | **`errors.py`** | **TodoNotFoundError만 존재** | **FileIOError 추가** | **SRP, DIP** |
| **v4** | **`main.py` 엔드포인트** | **create_todo 예외처리 누락** | **3개 엔드포인트 패턴 통일** | **SRP** |
| **v4** | **`app.js` 이벤트 핸들러** | **toggle/delete 예외처리 누락** | **4개 핸들러 패턴 통일** | **SRP** |

---

## 9. 테스트 전략 (v4)

기존 `test_todo.py` / `test_file_repository.py`는 변경 없다.

FileIOError 발생 경로를 검증하고 싶다면 아래 케이스를 선택적으로 추가한다.

```python
# test_file_repository.py — 선택 추가
def test_load_returns_empty_on_corrupt_json(tmp_path):
    """손상된 JSON 파일을 읽으면 빈 dict를 반환한다 (폴백 정책 검증)."""
    path = tmp_path / "todos.json"
    path.write_text("{ invalid json }", encoding="utf-8")
    repo = FileRepository(path=str(path))
    assert repo.get_all() == []

def test_save_raises_on_permission_error(tmp_path, monkeypatch):
    """파일 쓰기 권한이 없으면 FileIOError를 발생시킨다."""
    import builtins, pytest
    from errors import FileIOError as DomainFileIOError

    path = tmp_path / "todos.json"
    repo = FileRepository(path=str(path))

    original_open = builtins.open
    def mock_open(file, mode="r", **kwargs):
        if "w" in mode and str(path) in str(file):
            raise OSError("Permission denied")
        return original_open(file, mode, **kwargs)

    monkeypatch.setattr(builtins, "open", mock_open)

    from models.todo import Todo
    with pytest.raises(DomainFileIOError):
        repo.save(Todo(title="test"))
```

---

## 10. 구현 시 주의사항 (v4 추가)

1. **import 확인**: `main.py`에 `FileIOError` import 추가 (`from errors import TodoNotFoundError, FileIOError`)
2. **폴백 정책**: `_read_raw()`의 `JSONDecodeError` 폴백은 빈 dict 반환 — 데이터 유실보다 서비스 지속을 우선
3. **`_save` 실패는 폴백 없음**: 데이터 유실 방지를 위해 쓰기 실패는 명시적으로 503 반환
4. **프론트 alert 문구**: 사용자에게 의미 있는 한국어 메시지로 통일
5. **기존 v3 주석 유지**: OCP/DIP 증명 주석 삭제 금지 — 보고서 근거 자료

---

## 11. 실행 확인

```bash
cd backend
pytest tests/ -v
# 기존 21개 테스트 전부 통과해야 함 — 변경 없는 파일 OCP 증명
```
