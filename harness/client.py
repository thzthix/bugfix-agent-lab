from __future__ import annotations

import os
from typing import Any, Callable

from harness.config import HarnessLoopError


def create_client(
    client_factory: Callable[..., Any] | None = None,
) -> Any:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HarnessLoopError("OPENAI_API_KEY is not set.")

    if client_factory is None:
        from openai import OpenAI

        client_factory = OpenAI

    return client_factory(api_key=api_key)
