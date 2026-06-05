"""할일(Todo) 도메인에서 사용하는 열거형 정의 모듈."""

from enum import Enum


class Category(str, Enum):
    """할일 카테고리.

    str을 함께 상속하여 JSON 직렬화 시 문자열 값으로 변환되도록 한다.
    """

    WORK = "work"          # 업무
    PERSONAL = "personal"  # 개인
    STUDY = "study"        # 학습
    OTHER = "other"        # 기타


class Priority(str, Enum):
    """할일 우선순위.

    str을 함께 상속하여 JSON 직렬화 시 문자열 값으로 변환되도록 한다.
    """

    HIGH = "high"      # 높음
    MEDIUM = "medium"  # 중간
    LOW = "low"        # 낮음
