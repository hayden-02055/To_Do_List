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

# 데이터 파일 기본 경로: backend/data/todos.json
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
        self._path = path  # [캡슐화] 파일 경로를 외부에 노출하지 않는다.
        self._ensure_file()  # 파일이 없으면 빈 JSON으로 초기화한다.

    # ── Public (AbstractTodoRepository 구현) ──────────────────────

    def get_all(self) -> List[Todo]:
        """저장된 모든 할일을 리스트로 반환한다."""
        return list(self._load().values())

    def get_by_id(self, todo_id: str) -> Optional[Todo]:
        """id로 할일 한 건을 조회한다. 없으면 None을 반환한다."""
        return self._load().get(todo_id)

    def save(self, todo: Todo) -> Todo:
        """할일을 저장한다(신규 생성·갱신 모두 처리).

        같은 id가 있으면 갱신, 없으면 신규 추가한 뒤 파일에 기록한다.

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

        data/ 디렉토리가 없으면 자동 생성하고, 파일이 없으면 빈 JSON({})으로
        초기화한다.
        """
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        if not os.path.exists(self._path):
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load(self) -> dict[str, Todo]:
        """[캡슐화] JSON 파일에서 데이터를 로드하고 Todo 객체로 변환한다.

        외부에서 직접 호출하지 않으며, get_all()/get_by_id()를 통해서만 접근한다.

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

        외부에서 직접 호출하지 않으며, save()/delete()를 통해서만 호출된다.
        datetime·Enum 타입은 model_dump(mode="json")으로 직렬화하고,
        한글이 깨지지 않도록 ensure_ascii=False를 명시한다.

        [v4 업데이트] OSError를 FileIOError로 변환해서 던진다.
        조용히 실패하는 것보다 명시적으로 실패하는 것이 데이터 유실 방지에 낫다.

        리팩터링 이전(Bad):
            예외처리 없음 — 디스크 꽉 참, 권한 없음 등의 상황에서
            조용히 실패하고 데이터가 유실될 수 있음.

        리팩터링 이후(Good):
            OSError → FileIOError로 변환해서 상위로 전파.
            상위 계층(API)이 503 에러와 메시지를 사용자에게 전달할 수 있음.

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
