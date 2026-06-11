"""FileRepository 파일 I/O 단위 테스트 (v3 선택 추가, v4 확장).

기존 test_todo.py는 MockRepository를 주입하므로 저장소 교체와 무관하다(DIP).
이 파일은 FileRepository 자체의 영구 저장 동작을 직접 검증한다.
임시 디렉터리(tmp_path)를 사용해 실제 데이터 파일을 건드리지 않는다.

[v4 추가] FileIOError 발생/폴백 경로를 검증한다.
"""

import builtins
import os

import pytest

from errors import FileIOError
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


def test_load_returns_empty_on_corrupt_json(tmp_path) -> None:
    """손상된 JSON 파일을 읽으면 빈 dict를 반환한다 (폴백 정책 검증).

    [v4] _read_raw()의 JSONDecodeError 폴백 — 데이터 유실보다 서비스 지속 우선.
    """
    path = tmp_path / "todos.json"
    path.write_text("{ invalid json }", encoding="utf-8")
    repo = FileRepository(path=str(path))
    assert repo.get_all() == []


def test_save_raises_on_permission_error(tmp_path, monkeypatch) -> None:
    """파일 쓰기 권한이 없으면 FileIOError를 발생시킨다.

    [v4] _save()의 OSError → FileIOError 변환 — 쓰기 실패는 폴백 없이 명시적 전파.
    """
    path = tmp_path / "todos.json"
    repo = FileRepository(path=str(path))

    # open()을 가로채 쓰기 모드일 때만 OSError를 던지도록 한다.
    original_open = builtins.open

    def mock_open(file, mode="r", **kwargs):
        if "w" in mode and str(path) in str(file):
            raise OSError("Permission denied")
        return original_open(file, mode, **kwargs)

    monkeypatch.setattr(builtins, "open", mock_open)

    with pytest.raises(FileIOError):
        repo.save(Todo(title="test"))
