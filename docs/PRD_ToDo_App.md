# Product Requirements Document
## To-Do List Management App (할 일 관리 앱)

> 과목: 객체지향 프로그래밍 (OOP) | 버전: v1.0 | 작성일: 2026-06-06 | 마감일: 2026-06-12

---

## 1. 프로젝트 개요

### 1.1 목적

객체지향 프로그래밍(OOP)의 핵심 원칙인 SOLID, Observer 패턴, 단위 테스트를 실제 애플리케이션에 적용하여 설계 역량을 검증하는 과제이다. Python(FastAPI) 백엔드와 HTML/CSS/JS 프론트엔드를 분리하여 각 레이어의 역할과 책임을 명확히 구분한다.

### 1.2 목표

- SOLID 5원칙을 코드 구조에 명시적으로 적용
- Observer 패턴을 활용한 이벤트 시스템 구현
- pytest 단위 테스트로 핵심 로직 검증
- 추상 클래스 / 인터페이스를 통한 다형성 구현
- 직관적이고 완성도 높은 UI/UX 제공

### 1.3 기술 스택

| 레이어 | 기술 | 선택 이유 |
|---|---|---|
| Backend | Python 3.11 + FastAPI | OOP 구현 메인 언어, 교수님 수업 환경 일치 |
| Backend | Uvicorn | FastAPI ASGI 서버 |
| Backend | Pydantic | 타입 안전 데이터 모델 (LSP 보장) |
| Backend | pytest | 단위 테스트 프레임워크 |
| Frontend | HTML5 / CSS3 / Vanilla JS | 추가 설치 없이 브라우저에서 바로 동작 |
| Storage | In-Memory (Dict) | 과제 범위 적합, DB 없이 OOP 구조 시연 |

---

## 2. 기능 요구사항

> 우선순위 기준: P0 = 필수, P1 = 중요, P2 = 선택

| 카테고리 | 기능 | 구현 방식 | 우선순위 |
|---|---|---|:---:|
| 할일 관리 | 할일 추가 (제목, 설명, 마감일, 카테고리, 우선순위) | POST /todos | P0 |
| 할일 관리 | 할일 삭제 (단건) | DELETE /todos/{id} | P0 |
| 할일 관리 | 완료 체크 / 미완료 토글 | PATCH /todos/{id} | P0 |
| 할일 관리 | 할일 목록 조회 | GET /todos | P0 |
| 분류 | 카테고리 설정 (업무/개인/학습/기타) | Enum + 필터 UI | P1 |
| 분류 | 우선순위 설정 (높음/중간/낮음) | Enum + 색상 뱃지 | P1 |
| 일정 | 마감일 지정 및 표시 | datetime 필드 | P1 |
| 일정 | D-day / 기한 초과 표시 | 프론트 계산 렌더링 | P2 |
| UI/UX | 반응형 레이아웃 | CSS Flexbox/Grid | P1 |
| UI/UX | 필터 (카테고리, 우선순위, 완료 여부) | JS 이벤트 핸들러 | P1 |

---

## 3. OOP 설계 구조

### 3.1 SOLID + 패턴 적용 위치

| 원칙/패턴 | 적용 위치 | 레이어 | 설명 |
|---|---|:---:|---|
| SRP | TodoService / TodoRepository | Backend | 서비스는 로직만, 저장소는 저장만 담당 |
| OCP | AbstractTodoRepository | Backend | 새 저장소 추가 시 기존 코드 수정 없이 확장 |
| LSP | MemoryRepository → AbstractRepo | Backend | 추상 클래스를 완전히 대체 가능한 구현체 |
| ISP | IReadable / IWritable 분리 | Backend | 읽기·쓰기 인터페이스 분리 적용 |
| DIP | Service → Abstract 의존 | Backend | 구체 클래스가 아닌 추상에 의존 |
| Observer | EventSystem (on/emit) | Backend | 할일 추가·완료 시 이벤트 발행/구독 |
| Unit Test | pytest (test_todo.py) | Backend | TodoService 핵심 로직 단위 테스트 |

### 3.2 이벤트 시스템 (Observer 패턴)

`EventBus` 클래스는 이벤트 이름을 키로, 콜백 리스트를 값으로 관리하는 딕셔너리를 내부에 보유한다. 할일 추가(`todo.created`), 완료 토글(`todo.completed`), 삭제(`todo.deleted`) 이벤트를 발행하며, 구독자는 `on()` 메서드로 등록하고 `emit()` 메서드로 수신한다. 이를 통해 서비스 레이어와 로깅/알림 레이어 간의 결합도를 낮춘다.

### 3.3 의존성 주입 구조

- `TodoService`는 생성자에서 `AbstractTodoRepository`를 주입받음 (DIP)
- FastAPI의 `Depends()`를 활용하여 의존성을 런타임에 주입
- 테스트 시 `MockRepository`를 주입하여 실제 저장소 없이 단위 테스트 가능

### 3.4 클래스 다이어그램 (요약)

```
<<abstract>>
IReadable ──┐
            ├──► AbstractTodoRepository ──► MemoryTodoRepository
IWritable ──┘                 ▲
                              │ (DIP)
                         TodoService
                              │ (Observer)
                          EventBus
                         ┌────┴────┐
                     on(event)  emit(event)
```

---

## 4. 프로젝트 파일 구조

```
todo-app/
├── backend/
│   ├── main.py                      # FastAPI 앱 진입점, CORS 설정, 라우터 등록
│   ├── models/
│   │   ├── todo.py                  # Todo 데이터 클래스 (Pydantic BaseModel)
│   │   └── enums.py                 # Category, Priority Enum 정의
│   ├── interfaces/
│   │   └── repository.py            # IReadable / IWritable 추상 인터페이스 (ISP)
│   ├── repositories/
│   │   └── todo_repository.py       # MemoryRepository 구현체 (OCP, LSP)
│   ├── services/
│   │   └── todo_service.py          # 비즈니스 로직 (SRP, DIP)
│   ├── events/
│   │   └── event_system.py          # Observer 패턴 EventBus 구현
│   └── tests/
│       └── test_todo.py             # pytest 단위 테스트
├── frontend/
│   ├── index.html                   # 메인 UI 레이아웃
│   ├── style.css                    # 디자인 스타일시트
│   └── app.js                       # API 통신, 이벤트 핸들러, DOM 조작
├── requirements.txt                 # Python 의존성 패키지 목록
└── README.md                        # 실행 방법, 프로젝트 설명
```

---

## 5. API 명세

| Method | Endpoint | 설명 | 요청/응답 |
|:---:|---|---|---|
| GET | /todos | 전체 할일 목록 조회 (필터 지원) | Query: `category`, `priority`, `done` |
| POST | /todos | 새 할일 생성 | Body: `title`, `description`, `due_date`, `category`, `priority` |
| PATCH | /todos/{id} | 완료 상태 토글 | Response: 업데이트된 Todo 객체 |
| DELETE | /todos/{id} | 할일 삭제 | Response: 204 No Content |

---

## 6. 개발 일정

| 날짜 | 단계 | 작업 내용 |
|:---:|:---:|---|
| 06/06 (오늘) | 설계 | PRD 작성, 프로젝트 구조 확정, OOP 설계 확인 |
| 06/07 ~ 06/08 | 백엔드 | FastAPI 서버, 모델, 서비스, 이벤트 시스템, 단위 테스트 |
| 06/09 ~ 06/10 | 프론트엔드 | HTML/CSS UI 구현, JS API 연동, 필터 기능 |
| 06/11 | 통합 테스트 | E2E 동작 확인, 버그 수정, 실행 화면 캡처 |
| 06/12 | 제출 | PDF 보고서 작성, ZIP 패키징, 이메일 제출 |

---

## 7. 비기능 요구사항

### 7.1 코드 품질

- 모든 클래스/메서드에 docstring 주석 작성
- OOP 원칙 적용 위치를 주석으로 명시 (예: `# [SRP] 비즈니스 로직만 담당`)
- pytest 테스트 커버리지: 핵심 로직 100%

### 7.2 실행 환경

- Python 3.11 이상
- `requirements.txt` 기반 의존성 설치
- `README.md`에 실행 명령어 명시 (uvicorn 포함)

### 7.3 제출 기준 (과제 명세 기반)

- 제출 파일명: `OOP과제_학번_이름_제출일.zip`
- 포함 항목: 코드 원본 + 보고서 PDF
- 보고서 포함: AI Prompt 원문, AI 출력 요약, 본인 수정 사항, 반영 여부
- 보고서 포함: OOP 개념 구성 설명, 실행 화면 캡처 이미지
