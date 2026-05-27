import { useEffect, useState } from "react";

import { TodoRow } from "./components/TodoRow";
import { buildSummary, loadDemoState, persistDemoState } from "./demoStorage";

type TodoItem = {
  id: string;
  title: string;
  completed: boolean;
  is_favorite: boolean;
};

type TodoState = {
  items: TodoItem[];
  summary: {
    total_count: number;
    completed_count: number;
  };
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const initialState: TodoState = {
  items: [],
  summary: {
    total_count: 0,
    completed_count: 0,
  },
};

export default function App() {
  const [state, setState] = useState<TodoState>(initialState);
  const [draft, setDraft] = useState("");
  const [isDemoMode, setIsDemoMode] = useState(false);

  useEffect(() => {
    void loadTodos();
  }, []);

  async function loadTodos() {
    if (!API_BASE_URL) {
      setState(loadDemoState());
      setIsDemoMode(true);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/todos`);
      const nextState: TodoState = await response.json();
      setState(nextState);
      setIsDemoMode(false);
    } catch {
      setState(loadDemoState());
      setIsDemoMode(true);
    }
  }

  async function toggleTodo(id: string) {
    if (isDemoMode) {
      setState((currentState) => {
        const items = currentState.items.map((item) =>
          item.id === id ? { ...item, completed: !item.completed } : item,
        );
        const nextState = {
          items,
          summary: buildSummary(items),
        };
        persistDemoState(nextState);
        return nextState;
      });
      return;
    }

    const response = await fetch(`${API_BASE_URL}/api/todos/${id}/toggle`, {
      method: "POST",
    });
    const nextState: TodoState = await response.json();
    setState(nextState);
  }

  async function favoriteTodo(id: string) {
    if (isDemoMode) {
      setState((currentState) => {
        const nextState = {
          ...currentState,
          items: currentState.items.map((item) =>
          item.id === id ? { ...item, is_favorite: !item.is_favorite } : item,
          ),
        };
        persistDemoState(nextState);
        return nextState;
      });
      return;
    }

    const response = await fetch(`${API_BASE_URL}/api/todos/${id}/favorite`, {
      method: "POST",
    });
    const nextState: TodoState = await response.json();
    setState(nextState);
  }

  async function addTodo() {
    const title = draft.trim();
    if (!title) {
      return;
    }

    if (isDemoMode) {
      setState((currentState) => {
        const items = [
          {
            id: String(currentState.items.length + 1),
            title,
            completed: false,
            is_favorite: false,
          },
          ...currentState.items,
        ];
        const nextState = {
          items,
          summary: buildSummary(items),
        };
        persistDemoState(nextState);
        return nextState;
      });
      setDraft("");
      return;
    }

    const response = await fetch(`${API_BASE_URL}/api/todos`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title }),
    });
    const nextState: TodoState = await response.json();
    setState(nextState);
    setDraft("");
  }

  return (
    <main className="page-shell">
      <section className="app-card">
        <header className="app-header">
          <div className="header-left">
            <div className="title-group">
              <h1>Groceries</h1>
              <span>
                {state.summary.completed_count}/{state.summary.total_count}
              </span>
            </div>
            {isDemoMode ? <p className="demo-badge">Static demo mode</p> : null}
          </div>

          <div className="header-actions" aria-hidden="true">
            <button className="ghost-icon" type="button">
              ✎
            </button>
            <button className="ghost-icon" type="button">
              ⋯
            </button>
          </div>
        </header>

        <form
          className="composer-card"
          onSubmit={(event) => {
            event.preventDefault();
            void addTodo();
          }}
        >
          <span className="composer-plus">+</span>
          <input
            className="composer-input"
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Add a task..."
            value={draft}
          />
        </form>

        <div className="list-stack">
          {state.items.map((item) => (
            <TodoRow
              completed={item.completed}
              id={item.id}
              isFavorite={item.is_favorite}
              key={item.id}
              onFavorite={(nextId) => {
                void favoriteTodo(nextId);
              }}
              onToggle={(nextId) => {
                void toggleTodo(nextId);
              }}
              title={item.title}
            />
          ))}
        </div>
      </section>
    </main>
  );
}
