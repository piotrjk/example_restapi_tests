from typing import Callable
from conftest import ID_LIMIT


def do_endpoint_assertions(endpoint: str, send_request_fn: Callable):
    """The same flow is used for each endpoint, so this is extracted for brevity."""
    response = send_request_fn(endpoint)  # the path variable is mandatory, so this will return 404
    assert response.status_code == 404, \
        f"Unexpected status code {response.status_code} " \
        f"for {response.url} (expected 404)"
    for i in range(ID_LIMIT + 1):
        response = send_request_fn(f"{endpoint}/{i}")
        assert response.status_code == 200, (
            f"Unexpected status code {response.status_code} "
            f"for {response.url} (expected 200)"
        )
        response_json = response.json()
        expected_response_json = {"item_id": i}
        assert response_json == expected_response_json, (
            f"Unexpected response JSON {response_json!r} for "
            f"{response.url} (expected {expected_response_json!r})"
        )
    response = send_request_fn(f"{endpoint}/{ID_LIMIT + 1}")
    assert response.status_code == 404, (
        f"Unexpected status code {response.status_code} "
        f"for {response.url} (expected 404)"
    )
    response_json = response.json()
    expected_response_json = {"detail": f"Item {ID_LIMIT + 1} was not found."}
    assert response_json == expected_response_json, (
        f"Unexpected response JSON {response_json!r} "
        f"for {response.url} (expected {expected_response_json!r})"
    )


def test_endpoint_people(serve_api_0ms_delay):
    do_endpoint_assertions("people", serve_api_0ms_delay)


def test_endpoint_planets(serve_api_0ms_delay):
    do_endpoint_assertions("planets", serve_api_0ms_delay)


def test_endpoint_starships(serve_api_0ms_delay):
    do_endpoint_assertions("starships", serve_api_0ms_delay)
