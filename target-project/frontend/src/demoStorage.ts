import { demoState } from "./demoData";

const STORAGE_KEY = "bugfix-agent-lab-demo-state";

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

export function loadDemoState(): TodoState {
  const savedState = window.localStorage.getItem(STORAGE_KEY);

  if (!savedState) {
    persistDemoState(demoState);
    return cloneState(demoState);
  }

  try {
    return JSON.parse(savedState) as TodoState;
  } catch {
    persistDemoState(demoState);
    return cloneState(demoState);
  }
}

export function persistDemoState(state: TodoState): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function buildSummary(items: TodoItem[]): TodoState["summary"] {
  return {
    total_count: items.length,
    completed_count: items.filter((item) => item.completed).length,
  };
}

function cloneState(state: TodoState): TodoState {
  return {
    items: state.items.map((item) => ({ ...item })),
    summary: { ...state.summary },
  };
}
