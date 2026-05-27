from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TodoItem:
    id: str
    title: str
    completed: bool
    is_favorite: bool

    def toggled(self) -> "TodoItem":
        return TodoItem(
            id=self.id,
            title=self.title,
            completed=not self.completed,
            is_favorite=self.is_favorite,
        )

    def toggled_favorite(self) -> "TodoItem":
        return TodoItem(
            id=self.id,
            title=self.title,
            completed=self.completed,
            is_favorite=not self.is_favorite,
        )


@dataclass(slots=True)
class TodoSummary:
    total_count: int
    completed_count: int


@dataclass(slots=True)
class TodoListState:
    items: list[TodoItem]
    summary: TodoSummary
