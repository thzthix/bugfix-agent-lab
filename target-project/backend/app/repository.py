from __future__ import annotations

import json
from pathlib import Path

from app.models import TodoItem


class TodoRepository:
    def __init__(self, data_file: Path) -> None:
        self._data_file = data_file

    def list_items(self) -> list[TodoItem]:
        payload = self._read_payload()
        return [self._deserialize_item(raw_item) for raw_item in payload["items"]]

    def save_items(self, items: list[TodoItem]) -> None:
        payload = {"items": [self._serialize_item(item) for item in items]}
        self._data_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_payload(self) -> dict:
        return json.loads(self._data_file.read_text(encoding="utf-8"))

    def _deserialize_item(self, raw_item: dict) -> TodoItem:
        return TodoItem(
            id=raw_item["id"],
            title=raw_item["title"],
            completed=bool(raw_item["completed"]),
            is_favorite=bool(raw_item.get("favorite", False)),
        )

    def _serialize_item(self, item: TodoItem) -> dict:
        return {
            "id": item.id,
            "title": item.title,
            "completed": "true" if item.completed else "false",
            "favorite": item.is_favorite,
        }
