"""할일(Todo) 관련 Pydantic 모델 정의 모듈.

- Todo:       저장/응답에 사용하는 핵심 도메인 모델
- TodoCreate: 생성 요청 본문 모델 (서버가 채우는 필드는 제외)
- TodoUpdate: 수정 요청 본문 모델 (모든 필드 Optional)
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from models.enums import Category, Priority


class Todo(BaseModel):
    """할일 한 건을 표현하는 핵심 도메인 모델.

    Attributes:
        id: 고유 식별자(UUID 문자열). 기본값으로 자동 생성된다.
        title: 할일 제목(필수).
        description: 상세 설명.
        category: 카테고리.
        priority: 우선순위.
        due_date: 마감일(없을 수 있음).
        done: 완료 여부.
        created_at: 생성 일시.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str = ""
    category: Category = Category.OTHER
    priority: Priority = Priority.MEDIUM
    due_date: Optional[datetime] = None
    done: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


class TodoCreate(BaseModel):
    """할일 생성 요청 모델.

    id, done, created_at은 서버에서 채우므로 제외한다.
    """

    title: str
    description: str = ""
    category: Category = Category.OTHER
    priority: Priority = Priority.MEDIUM
    due_date: Optional[datetime] = None


class TodoUpdate(BaseModel):
    """할일 수정 요청 모델.

    부분 수정을 지원하기 위해 모든 필드를 Optional로 둔다.
    """

    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[Category] = None
    priority: Optional[Priority] = None
    due_date: Optional[datetime] = None
    done: Optional[bool] = None
