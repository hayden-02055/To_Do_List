// ============================================================
//  To-Do List 프론트엔드 (OOP 구조)
//  [SRP] 각 클래스는 하나의 책임만 담당한다.
//  [Observer 패턴] FrontEventBus로 컴포넌트 간 느슨한 결합을 구현한다.
// ============================================================

// 카테고리/우선순위 한글 라벨 매핑
const CATEGORY_LABEL = { work: '업무', personal: '개인', study: '학습', other: '기타' };
const PRIORITY_LABEL = { high: '높음', medium: '중간', low: '낮음' };

/**
 * [SRP] 백엔드 API 통신만 담당한다.
 * [캡슐화] baseURL은 #private 필드로 외부에 노출하지 않는다.
 */
class TodoAPI {
  #baseURL; // [캡슐화] private 필드 — 외부에서 직접 접근 불가

  /** @param {string} baseURL - 백엔드 서버 주소 */
  constructor(baseURL = 'http://localhost:5050') {
    this.#baseURL = baseURL;
  }

  /**
   * 필터·검색 조건에 맞는 할일 목록을 조회한다. (GET /todos)
   * @param {{category?:string, priority?:string, done?:string, search?:string}} filters
   * @returns {Promise<Array>}
   */
  async getAll(filters = {}) {
    const params = new URLSearchParams();
    if (filters.category) params.append('category', filters.category);
    if (filters.priority) params.append('priority', filters.priority);
    if (filters.done !== undefined && filters.done !== '') {
      params.append('done', filters.done);
    }
    if (filters.search) params.append('search', filters.search);
    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${this.#baseURL}/todos${query}`);
    if (!res.ok) throw new Error('할일 목록 조회 실패');
    return res.json();
  }

  /**
   * 새 할일을 생성한다. (POST /todos)
   * @param {object} data
   * @returns {Promise<object>}
   */
  async create(data) {
    const res = await fetch(`${this.#baseURL}/todos`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('할일 생성 실패');
    return res.json();
  }

  /**
   * 완료 상태를 토글한다. (PATCH /todos/{id})
   * @param {string} id
   * @returns {Promise<object>}
   */
  async toggleDone(id) {
    const res = await fetch(`${this.#baseURL}/todos/${id}`, { method: 'PATCH' });
    if (!res.ok) throw new Error('완료 토글 실패');
    return res.json();
  }

  /**
   * 할일을 삭제한다. (DELETE /todos/{id})
   * @param {string} id
   * @returns {Promise<void>}
   */
  async delete(id) {
    const res = await fetch(`${this.#baseURL}/todos/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('할일 삭제 실패');
  }
}

/**
 * [Observer 패턴] 프론트엔드 이벤트 버스.
 * 컴포넌트끼리 직접 참조하지 않고 이벤트로 통신한다.
 * [캡슐화] 구독자 목록(#listeners)은 외부에서 직접 접근할 수 없다.
 */
class FrontEventBus {
  #listeners = {}; // [캡슐화] private 필드 — 직접 접근 방지

  /**
   * 이벤트를 구독한다.
   * @param {string} event
   * @param {Function} callback
   */
  on(event, callback) {
    (this.#listeners[event] ||= []).push(callback);
  }

  /**
   * 이벤트를 발행하여 등록된 콜백을 모두 실행한다.
   * @param {string} event
   * @param {*} data
   */
  emit(event, data) {
    (this.#listeners[event] || []).forEach((cb) => cb(data));
  }
}

/**
 * [SRP] DOM 렌더링만 담당한다.
 */
class TodoRenderer {
  /**
   * @param {string} containerId - 목록을 그릴 컨테이너 id
   * @param {FrontEventBus} eventBus
   */
  constructor(containerId, eventBus) {
    this.container = document.getElementById(containerId);
    this.bus = eventBus;
  }

  /**
   * 전체 목록을 렌더링한다.
   * @param {Array} todos
   */
  render(todos) {
    this.container.innerHTML = '';

    if (!todos.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = '할 일이 없습니다. 새로운 할 일을 추가해 보세요! 🎉';
      this.container.appendChild(empty);
      return;
    }

    todos.forEach((todo) => this.container.appendChild(this.#createCard(todo)));
  }

  /**
   * [캡슐화] 할일 한 건의 카드 DOM을 생성한다. (#private — 내부 전용)
   * 외부에서 개별 카드 생성을 호출할 수 없도록 막는다.
   * @param {object} todo
   * @returns {HTMLElement}
   */
  #createCard(todo) {
    const card = document.createElement('div');
    card.className = `todo-card${todo.done ? ' done' : ''}`;
    card.dataset.id = todo.id;

    // 체크박스 (완료 토글)
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'todo-checkbox';
    checkbox.checked = todo.done;
    checkbox.addEventListener('change', () => {
      // [Observer] 토글 이벤트 발행 → 앱이 받아서 처리
      this.bus.emit('todo.toggled', todo.id);
    });

    // 본문
    const body = document.createElement('div');
    body.className = 'todo-body';

    const title = document.createElement('div');
    title.className = 'todo-title';
    title.textContent = todo.title;
    body.appendChild(title);

    if (todo.description) {
      const desc = document.createElement('div');
      desc.className = 'todo-description';
      desc.textContent = todo.description;
      body.appendChild(desc);
    }

    // 메타 영역 (뱃지 + D-day)
    const meta = document.createElement('div');
    meta.className = 'todo-meta';

    const catBadge = document.createElement('span');
    catBadge.className = `badge category-${todo.category}`;
    catBadge.textContent = CATEGORY_LABEL[todo.category] ?? todo.category;
    meta.appendChild(catBadge);

    const priBadge = document.createElement('span');
    priBadge.className = `badge priority-${todo.priority}`;
    priBadge.textContent = PRIORITY_LABEL[todo.priority] ?? todo.priority;
    meta.appendChild(priBadge);

    if (todo.due_date) {
      const dday = document.createElement('span');
      const { text, cssClass } = this.#getDdayText(todo.due_date);
      dday.className = `todo-dday ${cssClass}`;
      dday.textContent = text;
      meta.appendChild(dday);
    }

    body.appendChild(meta);

    // 삭제 버튼
    const delBtn = document.createElement('button');
    delBtn.className = 'btn-delete';
    delBtn.textContent = '🗑';
    delBtn.title = '삭제';
    delBtn.addEventListener('click', () => {
      // [Observer] 삭제 이벤트 발행
      this.bus.emit('todo.deleted', todo.id);
    });

    card.append(checkbox, body, delBtn);
    return card;
  }

  /**
   * [캡슐화] 마감일과 오늘 날짜 차이로 D-day 텍스트를 계산한다. (#private — 내부 전용)
   * @param {string} dueDate - ISO 날짜 문자열
   * @returns {{text:string, cssClass:string}}
   */
  #getDdayText(dueDate) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const due = new Date(dueDate);
    due.setHours(0, 0, 0, 0);

    const diffDays = Math.round((due - today) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return { text: 'D-Day', cssClass: 'today' };
    if (diffDays > 0) return { text: `D-${diffDays}`, cssClass: '' };
    return { text: `D+${Math.abs(diffDays)} (지남)`, cssClass: 'overdue' };
  }
}

/**
 * [SRP] 필터·검색 UI 상태 관리만 담당한다.
 * [리팩터링] 초기에는 TodoApp 안에 섞여 있던 필터 로직을 별도 클래스로 분리.
 * [캡슐화] 이벤트 버스(#bus)는 외부에서 직접 접근할 수 없다.
 */
class FilterManager {
  #bus; // [캡슐화] private 필드

  /** @param {FrontEventBus} eventBus */
  constructor(eventBus) {
    this.#bus = eventBus;
    this.categoryEl = document.getElementById('filter-category');
    this.priorityEl = document.getElementById('filter-priority');
    this.doneEl = document.getElementById('filter-done');
    this.searchEl = document.getElementById('search-input');
  }

  /**
   * 현재 필터·검색 값을 반환한다.
   * @returns {{category:string, priority:string, done:string, search:string}}
   */
  getFilters() {
    return {
      category: this.categoryEl.value,
      priority: this.priorityEl.value,
      done: this.doneEl.value,
      search: this.searchEl.value.trim(),
    };
  }

  /**
   * 필터·검색 변경 이벤트를 바인딩한다.
   * - 드롭다운 변경 시 'filter.changed' 발행
   * - 검색창 입력(oninput) 시 'search.changed' 발행 → 실시간 검색
   */
  bindEvents() {
    [this.categoryEl, this.priorityEl, this.doneEl].forEach((el) => {
      el.addEventListener('change', () => {
        this.#bus.emit('filter.changed', this.getFilters());
      });
    });

    // [실시간 검색] oninput으로 입력 즉시 목록 재조회
    this.searchEl.addEventListener('input', () => {
      this.#bus.emit('search.changed', this.getFilters());
    });
  }
}

/**
 * [SRP] 앱 전체를 조율하는 Facade.
 * 각 컴포넌트를 생성/연결하고 이벤트 흐름을 관리한다.
 */
class TodoApp {
  constructor() {
    this.api = new TodoAPI();
    this.bus = new FrontEventBus();
    this.renderer = new TodoRenderer('todo-list', this.bus);
    this.filter = new FilterManager(this.bus);
  }

  /**
   * 초기화: 이벤트 바인딩 후 첫 데이터를 로드한다.
   */
  async init() {
    this.filter.bindEvents();
    this.bindFormEvents();
    this.bindBusEvents();
    await this.refresh();
  }

  /**
   * [Observer] 버스 이벤트와 실제 동작을 연결한다.
   */
  bindBusEvents() {
    this.bus.on('filter.changed', () => this.refresh());
    this.bus.on('search.changed', () => this.refresh());
    this.bus.on('todo.added', () => this.refresh());

    this.bus.on('todo.toggled', async (id) => {
      await this.api.toggleDone(id);
      await this.refresh();
    });

    this.bus.on('todo.deleted', async (id) => {
      await this.api.delete(id);
      await this.refresh();
    });
  }

  /**
   * 현재 필터를 적용해 목록을 다시 조회/렌더링한다.
   */
  async refresh() {
    try {
      const filters = this.filter.getFilters();
      const todos = await this.api.getAll(filters);
      this.renderer.render(todos);
    } catch (err) {
      console.error(err);
      alert('서버와 통신할 수 없습니다. 백엔드가 실행 중인지 확인하세요.');
    }
  }

  /**
   * 추가 폼 제출 이벤트를 바인딩한다.
   */
  bindFormEvents() {
    const form = document.getElementById('todo-form');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const dueRaw = form['due_date'].value;
      const data = {
        title: form['title'].value.trim(),
        description: form['description'].value.trim(),
        category: form['category'].value,
        priority: form['priority'].value,
        // 날짜만 입력되므로 ISO datetime 형태로 변환
        due_date: dueRaw ? new Date(dueRaw).toISOString() : null,
      };

      if (!data.title) return;

      try {
        await this.api.create(data);
        form.reset();
        // [Observer] 추가 완료 이벤트 발행 → 목록 갱신
        this.bus.emit('todo.added');
      } catch (err) {
        console.error(err);
        alert('할일 추가에 실패했습니다.');
      }
    });
  }
}

// 앱 진입점
const app = new TodoApp();
app.init();
