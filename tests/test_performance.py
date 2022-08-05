import time
import statistics
from conftest import console, SERVER_WORKERS
from typing import Callable, List, Tuple, Iterable, Iterator
import concurrent.futures
from itertools import zip_longest
from rich.console import Group

TEST_DURATION = 60
ENDPOINT_PATH = "people/0"
TEST_CONCURRENCY = SERVER_WORKERS + 1

SOLID_BLOCK_CHARACTER = '\u2588'
SHADED_BLOCK_CHARACTER = '\u2591'


def chunker(iterable: Iterable[int], n: int) -> Iterator[Tuple[int, ...]]:
    """Based on 'grouper' recipe from itertools."""
    args = [iter(iterable)] * n
    for chunk in zip_longest(*args, fillvalue=None):
        yield tuple(i for i in chunk if i is not None)


def sequential_load_function(send_request_fn: Callable, test_ends_at: float) -> List[Tuple[float, float, bool]]:
    """This will just make requests one by one, until time limit.

    Returns a list of tuples:
        * monotonic time for the request start
        * time in seconds it took for a response
        * status of the response, True is success, False otherwise
    """
    timings = []
    while True:
        now = time.monotonic()
        if now > test_ends_at:
            break
        response = send_request_fn(ENDPOINT_PATH)
        took = time.monotonic() - now
        if response is None or not response.ok:  # request timed out or otherwise failed
            timings.append((now, took, False))
        else:
            timings.append((now, response.elapsed.total_seconds(), True))
    return timings


def concurrent_load_function(send_request_fn: Callable, test_ends_at: float) -> List[Tuple[float, float, bool]]:
    """This will run 'sequential_load_function' concurrently, using multithreading.

    This is not truly parallel because of GIL, but for IO load / HTTP requests it doesn't really matter.

    The 'Session' object from requests is not thread safe in all conditions (e.g. with cookies involved),
    but it is safe enough for this simple example.

    Next steps would be to use aiohttp / asyncio and multiprocessing.
    """
    timings = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=TEST_CONCURRENCY) as executor:
        futures = []
        for _ in range(TEST_CONCURRENCY):
            futures.append(executor.submit(sequential_load_function, send_request_fn, test_ends_at))
        for future in futures:
            timings.extend(future.result())
    return sorted(timings, key=lambda i: i[0])


def do_performance_test(send_request_fn: Callable, load_fn: Callable, duration: float) -> Tuple[int, int]:
    """Common 'performance' function, will return total number of requests made and how many failed."""
    test_ends_at = time.monotonic() + duration
    console.log(
        "The test will now continuously send GET requests to "
        f"{ENDPOINT_PATH!r} for {duration} seconds..."
    )
    timings = load_fn(send_request_fn, test_ends_at)
    took = timings[-1][0] + timings[-1][1] - timings[0][0]
    elapsed_times = tuple(t[1] for t in timings)
    # failed requests have the third item set to False
    failed_requests = sum(int(not t[2]) for t in timings)

    console.log(f"Made {len(timings)} requests in {took:.02f} seconds")
    console.log(f"{failed_requests} requests got error responses")
    console.log(f"Arithmetic mean of response times: {statistics.mean(elapsed_times):.05f}")
    console.log(f"Standard deviation of response times: {statistics.stdev(elapsed_times):.05f}")
    console.log(visualize_requests(timings))
    return len(timings), failed_requests


def visualize_requests(timings: List[Tuple[float, float, bool]], columns: int = 10) -> Group:
    """This will produce a chart that will help to visualize the status of requests, per second."""
    requests_per_second = {}
    for r_time, r_duration, r_status in timings:
        int_r_time = int(r_time)
        try:
            requests_per_second[int_r_time].append(int(r_status))
        except KeyError:
            requests_per_second[int_r_time] = [int(r_status)]
    most_requests_in_second = max((len(v) for v in requests_per_second.values()))
    max_requests_in_column = round(most_requests_in_second / columns)
    renderables = [f"\nThis chart is a visualization of the requests made, each row represents a second,\n"
                   f"and each cell represents up to {max_requests_in_column} requests.\n"
                   f"If a cell is solid / green, it means that more than a half of its requests passed."]

    for i, requests_in_second in enumerate(requests_per_second.values()):
        row = []
        for chunk in chunker(requests_in_second, max_requests_in_column):
            if sum(chunk) / len(chunk) >= 0.5:  # if there is more than half passed request in this slice
                row.append(f"[green]{SOLID_BLOCK_CHARACTER}[/]")
            else:
                row.append(f"[red]{SHADED_BLOCK_CHARACTER}[/]")
        ok = sum(requests_in_second)
        nok = len(requests_in_second) - ok
        renderables.append(f't+{i:<2} {ok:>4}:white_check_mark: {nok:>4}:cross_mark: {"".join(row)}')
    renderables.append('\n')
    return Group(*renderables)


def test_endpoint_performance_0ms_delay_sequential(serve_api_0ms_delay):
    total_requests, failed_requests = do_performance_test(
        send_request_fn=serve_api_0ms_delay,
        load_fn=sequential_load_function,
        duration=TEST_DURATION
    )
    assert failed_requests == 0, f"{failed_requests}/{total_requests} requests failed"


def test_endpoint_performance_10ms_delay_sequential(serve_api_10ms_delay):
    total_requests, failed_requests = do_performance_test(
        send_request_fn=serve_api_10ms_delay,
        load_fn=sequential_load_function,
        duration=TEST_DURATION
    )
    assert failed_requests == 0, f"{failed_requests}/{total_requests} requests failed"


def test_endpoint_performance_100ms_delay_sequential(serve_api_100ms_delay):
    total_requests, failed_requests = do_performance_test(
        send_request_fn=serve_api_100ms_delay,
        load_fn=sequential_load_function,
        duration=TEST_DURATION
    )
    assert failed_requests == 0, f"{failed_requests}/{total_requests} requests failed"


def test_endpoint_performance_0ms_delay_concurrent(serve_api_0ms_delay):
    total_requests, failed_requests = do_performance_test(
        send_request_fn=serve_api_0ms_delay,
        load_fn=concurrent_load_function,
        duration=TEST_DURATION
    )
    assert failed_requests == 0, f"{failed_requests}/{total_requests} requests failed"


def test_endpoint_performance_10ms_delay_concurrent(serve_api_10ms_delay):
    total_requests, failed_requests = do_performance_test(
        send_request_fn=serve_api_10ms_delay,
        load_fn=concurrent_load_function,
        duration=TEST_DURATION
    )
    assert failed_requests == 0, f"{failed_requests}/{total_requests} requests failed"


def test_endpoint_performance_100ms_delay_concurrent(serve_api_100ms_delay):
    total_requests, failed_requests = do_performance_test(
        send_request_fn=serve_api_100ms_delay,
        load_fn=concurrent_load_function,
        duration=TEST_DURATION
    )
    assert failed_requests == 0, f"{failed_requests}/{total_requests} requests failed"
