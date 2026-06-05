# To-Do List Management App

OOP 원칙(SOLID 5원칙 + Observer 패턴)을 적용한 할일 관리 애플리케이션입니다.

- **백엔드**: Python 3.11 / FastAPI + Uvicorn
- **프론트엔드**: HTML5 / CSS3 / Vanilla JS (OOP 클래스 구조)

---

## 프로젝트 구조

```
todo-app/
├── backend/
│   ├── main.py                      # FastAPI 앱 진입점
│   ├── models/                      # 도메인 모델 / 열거형
│   ├── interfaces/                  # 저장소 추상 인터페이스 [ISP, OCP]
│   ├── repositories/                # 인메모리 저장소 구현 [LSP]
│   ├── services/                    # 비즈니스 로직 [SRP, DIP]
│   ├── events/                      # 이벤트 버스 [Observer]
│   └── tests/                       # pytest 단위 테스트
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
└── README.md
```

---

## 적용한 OOP 원칙

| 원칙 | 적용 위치 |
|---|---|
| **SRP** (단일 책임) | `TodoService`(로직), `MemoryTodoRepository`(저장), 프론트의 각 클래스 |
| **OCP** (개방-폐쇄) | `AbstractTodoRepository` 상속만으로 저장소 교체 |
| **LSP** (리스코프 치환) | `MemoryTodoRepository` / `MockTodoRepository`가 추상 저장소를 완전 대체 |
| **ISP** (인터페이스 분리) | `IReadable` / `IWritable` 읽기·쓰기 분리 |
| **DIP** (의존 역전) | `TodoService`가 구체 클래스가 아닌 추상에 의존(생성자 주입) |
| **Observer** | 백엔드 `EventBus`, 프론트 `FrontEventBus` |

---

## 실행 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 서버 실행

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API 문서: http://localhost:5050/docs

### 3. 프론트엔드 실행

`frontend/index.html`을 브라우저로 엽니다.
(또는 VS Code의 Live Server 확장 사용)

### 4. 테스트 실행

```bash
cd backend
pytest tests/ -v
```

---

## API 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/todos` | 목록 조회 (query: `category`, `priority`, `done`, `search`) |
| POST | `/todos` | 할일 생성 |
| PATCH | `/todos/{todo_id}` | 완료 상태 토글 |
| DELETE | `/todos/{todo_id}` | 삭제 (204 반환) |
