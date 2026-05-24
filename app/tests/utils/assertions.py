from typing import Any

from httpx import Response


def assert_status(response: Response, expected: int) -> dict[str, Any]:
    assert response.status_code == expected, response.text
    return response.json()


def assert_error(
    response: Response,
    *,
    status_code: int,
    code: str,
) -> dict[str, Any]:
    body = assert_status(response, status_code)
    assert "error" in body
    assert body["error"]["code"] == code
    assert "request_id" in body
    return body
