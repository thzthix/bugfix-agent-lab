from __future__ import annotations

from app.models import TodoItem, TodoListState, TodoSummary
from app.repository import TodoRepository


class TodoService:
    def __init__(self, repository: TodoRepository) -> None:
        self._repository = repository

    def get_state(self) -> TodoListState:
        items = self._repository.list_items()
        return TodoListState(items=items, summary=self._build_summary(items))

    def add_item(self, title: str) -> TodoListState:
        items = self._repository.list_items()
        next_item = TodoItem(
            id=str(len(items) + 1),
            title=title.strip(),
            completed=False,
            is_favorite=False,
        )
        updated_items = [next_item, *items]
        self._repository.save_items(updated_items)
        return self.get_state()

    def toggle_item(self, item_id: str) -> TodoListState:
        items = self._repository.list_items()
        updated_items = [
            item.toggled() if item.id == item_id else item for item in items
        ]
        self._repository.save_items(updated_items)
        return self.get_state()

    def toggle_favorite(self, item_id: str) -> TodoListState:
        items = self._repository.list_items()
        updated_items = [
            item.toggled_favorite() if item.id == item_id else item for item in items
        ]
        self._repository.save_items(updated_items)
        return self.get_state()

    def _build_summary(self, items: list[TodoItem]) -> TodoSummary:
        completed_count = sum(1 for item in items if item.completed)
        return TodoSummary(total_count=len(items), completed_count=completed_count)
