from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


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
                "favorite": True,
            },
        ]
    }
    data_file.write_text(json.dumps(payload), encoding="utf-8")


def test_get_todos_returns_summary_payload(tmp_path: Path) -> None:
    data_file = tmp_path / "todos.json"
    _write_seed(data_file)
    client = TestClient(create_app(data_file))

    response = client.get("/api/todos")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_count"] == 2
    assert payload["items"][0]["title"] == "Manuka honey"
