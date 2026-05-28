import os
import re
import time
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai.errors import ClientError

from harness.config import DEFAULT_API_RETRIES, DEFAULT_RETRY_DELAY_SECONDS


def create_client() -> genai.Client:
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=api_key)


def generate_content_with_backoff(
    client: genai.Client,
    *,
    model: str,
    contents: str,
    config: Any,
    max_retries: int = DEFAULT_API_RETRIES,
    default_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> Any:
    attempt = 0
    while True:
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except ClientError as error:
            attempt += 1
            retry_delay = extract_retry_delay_seconds(error)
            if retry_delay is None or attempt > max_retries:
                raise
            time.sleep(max(retry_delay, default_delay_seconds))


def extract_retry_delay_seconds(error: ClientError) -> float | None:
    payload = getattr(error, "details", None)
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            retry_delay = item.get("retryDelay")
            seconds = _parse_retry_delay_seconds(retry_delay)
            if seconds is not None:
                return seconds

    payload_text = str(error)
    match = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", payload_text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _parse_retry_delay_seconds(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)s", value.strip())
    if not match:
        return None
    return float(match.group(1))
