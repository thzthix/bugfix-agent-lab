from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.models import TodoListState
from app.repository import TodoRepository
from app.service import TodoService


class CreateTodoRequest(BaseModel):
    title: str


class TodoResponse(BaseModel):
    id: str
    title: str
    completed: bool
    is_favorite: bool


class SummaryResponse(BaseModel):
    total_count: int
    completed_count: int


class TodoListResponse(BaseModel):
    items: list[TodoResponse]
    summary: SummaryResponse


def create_app(data_file: Path | None = None) -> FastAPI:
    app = FastAPI(title="Grocery List Target")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    data_path = data_file or Path(__file__).resolve().parent.parent / "data" / "todos.json"
    service = TodoService(TodoRepository(data_path))

    @app.get("/api/todos", response_model=TodoListResponse)
    def get_todos() -> TodoListResponse:
        return _to_response(service.get_state())

    @app.post("/api/todos", response_model=TodoListResponse)
    def create_todo(request: CreateTodoRequest) -> TodoListResponse:
        return _to_response(service.add_item(request.title))

    @app.post("/api/todos/{item_id}/toggle", response_model=TodoListResponse)
    def toggle_todo(item_id: str) -> TodoListResponse:
        return _to_response(service.toggle_item(item_id))

    @app.post("/api/todos/{item_id}/favorite", response_model=TodoListResponse)
    def favorite_todo(item_id: str) -> TodoListResponse:
        return _to_response(service.toggle_favorite(item_id))

    return app


def _to_response(state: TodoListState) -> TodoListResponse:
    return TodoListResponse(
        items=[
            TodoResponse(
                id=item.id,
                title=item.title,
                completed=item.completed,
                is_favorite=item.is_favorite,
            )
            for item in state.items
        ],
        summary=SummaryResponse(
            total_count=state.summary.total_count,
            completed_count=state.summary.completed_count,
        ),
    )


app = create_app()
