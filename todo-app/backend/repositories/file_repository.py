"""JSON 파일 기반 영구 저장소 구현 모듈 (v3 신규).

[OCP] AbstractTodoRepository를 상속하므로, 상위 계층(TodoService) 코드를
      수정하지 않고도 MemoryTodoRepository를 이 구현체로 교체할 수 있다.
[캡슐화] 파일 입출력 세부사항(_load/_save)을 private 메서드로 은닉한다.
"""

import json
import os
from typing import List, Optional

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
        """
        store = self._load()
        store[todo.id] = todo
        self._save(store)
        return todo

    def delete(self, todo_id: str) -> bool:
        """id에 해당하는 할일을 삭제한다.

        Returns:
            삭제에 성공하면 True, 대상이 없으면 False.
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
        """[캡슐화] JSON 파일에서 데이터를 로드한다.

        외부에서 직접 호출하지 않으며, get_all()/get_by_id()를 통해서만 접근한다.
        """
        with open(self._path, "r", encoding="utf-8") as f:
            raw: dict = json.load(f)
        return {k: Todo.model_validate(v) for k, v in raw.items()}

    def _save(self, store: dict[str, Todo]) -> None:
        """[캡슐화] Todo 딕셔너리를 JSON 파일로 저장한다.

        외부에서 직접 호출하지 않으며, save()/delete()를 통해서만 호출된다.
        datetime·Enum 타입은 model_dump(mode="json")으로 직렬화하고,
        한글이 깨지지 않도록 ensure_ascii=False를 명시한다.
        """
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.model_dump(mode="json") for k, v in store.items()},
                f,
                ensure_ascii=False,
                indent=2,
            )
