from __future__ import annotations

import json
from pathlib import Path

from app.repository import TodoRepository
from app.service import TodoService


def _write_seed(data_file: Path) -> None:
    payload = {
        "items": [
            {
                "id": "1",
                "title": "Manuka honey",
                "completed": "false",
                "favorite": False,
            },
            {
                "id": "2",
                "title": "Peanut butter",
                "completed": "true",
                "favorite": False,
            },
        ]
    }
    data_file.write_text(json.dumps(payload), encoding="utf-8")


def test_toggle_item_preserves_other_completion_states(tmp_path: Path) -> None:
    data_file = tmp_path / "todos.json"
    _write_seed(data_file)

    service = TodoService(TodoRepository(data_file))

    state = service.toggle_item("1")

    assert [item.completed for item in state.items] == [True, True]
    assert state.summary.completed_count == 2


def test_initial_reload_keeps_false_values_false(tmp_path: Path) -> None:
    data_file = tmp_path / "todos.json"
    _write_seed(data_file)

    service = TodoService(TodoRepository(data_file))

    state = service.get_state()

    assert state.items[0].completed is False
