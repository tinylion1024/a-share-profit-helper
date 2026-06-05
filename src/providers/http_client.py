"""Retrying HTTP helpers for live market data providers."""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request

from src.providers.base import OnlineDataError


class RetryingHttpClient:
    """Minimal HTTP client with retry and consistent error wrapping."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_retries: int,
        urlopen_impl: Callable[..., Any],
        subprocess_run_impl: Callable[..., Any],
        sleep_impl: Callable[[float], None] = time.sleep,
    ):
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.urlopen_impl = urlopen_impl
        self.subprocess_run_impl = subprocess_run_impl
        self.sleep_impl = sleep_impl

    def request_with_retries(self, label: str, operation: Callable[[], Any]) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return operation()
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                self.sleep_impl(0.15 * attempt)
        if isinstance(last_error, HTTPError):
            detail = f"HTTP {last_error.code}"
        elif isinstance(last_error, URLError):
            detail = f"network error: {last_error.reason}"
        elif isinstance(last_error, subprocess.CalledProcessError):
            detail = f"curl failed with exit code {last_error.returncode}"
        else:
            detail = str(last_error) if last_error else "unknown error"
        raise OnlineDataError(f"{label} failed after {self.max_retries} attempts: {detail}") from last_error

    def get_text(
        self,
        url: str,
        *,
        encoding: str = "gbk",
        headers: dict[str, str] | None = None,
    ) -> str:
        def run() -> str:
            request = Request(url, headers=headers or {})
            with self.urlopen_impl(request, timeout=self.timeout_seconds) as response:
                return response.read().decode(encoding, errors="ignore")

        return self.request_with_retries(f"GET text {url}", run)

    def get_json(self, url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            request = Request(url, headers=headers or {})
            with self.urlopen_impl(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="ignore")
            return json.loads(raw)

        return self.request_with_retries(f"GET json {url}", run)

    def curl_get_json(self, url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            command = ["curl", "-L", "--max-time", str(int(max(self.timeout_seconds, 1)))]
            for key, value in (headers or {}).items():
                command.extend(["-H", f"{key}: {value}"])
            command.append(url)
            completed = self.subprocess_run_impl(command, check=True, capture_output=True, text=True)
            return json.loads(completed.stdout)

        return self.request_with_retries(f"curl json {url}", run)

    def post_form_json(
        self,
        url: str,
        *,
        form_data: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            payload = urlencode(form_data).encode("utf-8")
            request = Request(url, data=payload, headers=headers or {}, method="POST")
            with self.urlopen_impl(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="ignore")
            return json.loads(raw)

        return self.request_with_retries(f"POST form json {url}", run)

    def post_json(
        self,
        url: str,
        *,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        def run() -> dict[str, Any]:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            request = Request(url, data=body, headers=headers or {}, method="POST")
            with self.urlopen_impl(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="ignore")
            return json.loads(raw)

        return self.request_with_retries(f"POST json {url}", run)
