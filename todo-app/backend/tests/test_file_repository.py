"""FileRepository 파일 I/O 단위 테스트 (v3 선택 추가).

기존 test_todo.py는 MockRepository를 주입하므로 저장소 교체와 무관하다(DIP).
이 파일은 FileRepository 자체의 영구 저장 동작을 직접 검증한다.
임시 디렉터리(tmp_path)를 사용해 실제 데이터 파일을 건드리지 않는다.
"""

import os

from repositories.file_repository import FileRepository
from models.todo import Todo


def test_file_repository_init(tmp_path) -> None:
    """파일이 없을 때 자동으로 빈 JSON으로 초기화되는지 확인한다."""
    path = tmp_path / "data" / "todos.json"
    repo = FileRepository(path=str(path))

    # _ensure_file()이 디렉터리와 파일을 생성했어야 한다.
    assert os.path.exists(path)
    assert repo.get_all() == []


def test_file_repository_persist(tmp_path) -> None:
    """저장 후 새 인스턴스로 재로드했을 때 데이터가 유지되는지 확인한다."""
    path = str(tmp_path / "data" / "todos.json")
    repo = FileRepository(path=path)

    saved = repo.save(Todo(title="한글 할일", description="영구 저장 확인"))

    # 새 인스턴스 = 파일에서 다시 읽음 → 영속성 검증
    reloaded = FileRepository(path=path).get_by_id(saved.id)
    assert reloaded is not None
    assert reloaded.title == "한글 할일"
    assert reloaded.description == "영구 저장 확인"


def test_file_repository_delete(tmp_path) -> None:
    """삭제 후 재로드 시 데이터가 제거되는지 확인한다."""
    path = str(tmp_path / "data" / "todos.json")
    repo = FileRepository(path=path)
    saved = repo.save(Todo(title="삭제 대상"))

    assert repo.delete(saved.id) is True
    assert FileRepository(path=path).get_by_id(saved.id) is None
    # 없는 id 삭제 시 False
    assert repo.delete("nonexistent") is False
