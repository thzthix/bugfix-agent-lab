import { useEffect, useState } from "react";

import { TodoRow } from "./components/TodoRow";

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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

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

  useEffect(() => {
    void loadTodos();
  }, []);

  async function loadTodos() {
    const response = await fetch(`${API_BASE_URL}/api/todos`);
    const nextState: TodoState = await response.json();
    setState(nextState);
  }

  async function toggleTodo(id: string) {
    const response = await fetch(`${API_BASE_URL}/api/todos/${id}/toggle`, {
      method: "POST",
    });
    const nextState: TodoState = await response.json();
    setState(nextState);
  }

  async function favoriteTodo(id: string) {
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
          <div className="title-group">
            <h1>Groceries</h1>
            <span>
              {state.summary.completed_count}/{state.summary.total_count}
            </span>
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
