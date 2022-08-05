import os
import signal
import subprocess
import time
from subprocess import Popen, PIPE
import socket
from pathlib import Path
from contextlib import contextmanager
from typing import ContextManager, Optional
import atexit
from rich.console import Console

import requests
from requests import Session

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
REQUEST_TIMEOUT = 1
ID_LIMIT = 10
SERVER_WORKERS = 2

console = Console()


def pytest_report_teststatus(report, config):
    """This will override pytest logging so that it won't interrupt log calls made from test."""
    color = 'green' if report.outcome == 'passed' else 'red'
    console.log(f"\n[{color}]{report.nodeid} {report.when} {report.outcome}[/]\n")
    return '', '', ''


@contextmanager
def serve_api(**server_environmental_variables) -> ContextManager:
    # Get unused port.
    with socket.socket() as a_socket:
        a_socket.bind(("", 0))
        port_to_use = a_socket.getsockname()[1]

    # Make a copy of the current environmental variables, add what we want to it.
    env = os.environ.copy()
    env.update({k: str(v) for k, v in server_environmental_variables.items()})

    console.log(
        f"Starting API server on localhost:{port_to_use} with settings: {server_environmental_variables}"
    )
    # Start the server in a subprocess.
    # See https://fastapi.tiangolo.com/deployment/server-workers/
    server_process = Popen(
        args=(
            "gunicorn", "api.main:app",
            "--worker-class", "uvicorn.workers.UvicornWorker",
            "--bind", f"0.0.0.0:{port_to_use}",
            "--access-logfile", "-",
            "--access-logformat", '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"',
            "--timeout", "10"
        ),
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        cwd=ROOT_DIR,
        env=env,
    )
    # Just in case the parent process will be abruptly ended.
    atexit.register(
        server_process.kill
    )

    # Wait for the server to fully start before proceeding.
    timeout = 10
    timeout_at = time.monotonic() + 10
    initial_output = ""
    workers_ready = 0
    while True:
        if time.monotonic() > timeout_at:
            raise TimeoutError(
                f"API server did not fully start within {timeout} seconds"
            )
        initial_output += server_process.stderr.read(1)
        if initial_output.endswith("Application startup complete.\n"):
            workers_ready += 1
        if workers_ready >= SERVER_WORKERS:
            break
    console.log("API server started successfully!")

    # Create a closure function that will be then used by test code
    requests_session = Session()

    def request_function(path: str, *args, **kwargs) -> Optional[requests.Response]:
        """This closure will be passed on to the test functions to avoid repeating this over and over."""
        nonlocal requests_session, port_to_use
        url = f"http://localhost:{port_to_use}/{path}"
        try:
            return requests_session.get(
                *args, url=url, timeout=REQUEST_TIMEOUT, **kwargs
            )
        except requests.Timeout:
            return None

    try:
        yield request_function
    finally:
        # Disable the atexit hook.
        atexit.unregister(server_process.kill)
        console.log("Stopping API server...")
        # Stop the server process.
        server_process.send_signal(signal.SIGINT)
        try:
            # Retrieve stdout / stderr from the process.
            stdout, stderr = server_process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            # If the server did not respond to SIGINT for any reason, kill it.
            server_process.kill()
            stdout, stderr = server_process.communicate()
        console.log("Stopped API server!")
        console.log(f"Error log from the API server instance:\n{initial_output + stderr}")
        # List its access log.
        # The exercise description mentioned saving it to a file, but as it there is no mention what to do with it,
        # I opted to just log it with the rest of the test output - but for sake of readability,
        # it is deduplicated (preserving order).
        access_log = '\n'.join(dict.fromkeys(stdout.splitlines()))
        console.log(f"Unique entries from access log of API server instance:\n{access_log}")


# Each test will get a new instance of the api server with scope set to "function", but this can be easily changed.
@pytest.fixture(scope="function")
def serve_api_0ms_delay():
    with serve_api(WEB_CONCURRENCY=SERVER_WORKERS, ID_LIMIT=ID_LIMIT, MAX_DELAY=0) as request_function:
        yield request_function


@pytest.fixture(scope="function")
def serve_api_10ms_delay():
    with serve_api(WEB_CONCURRENCY=SERVER_WORKERS, ID_LIMIT=ID_LIMIT, MAX_DELAY=0.01) as request_function:
        yield request_function


@pytest.fixture(scope="function")
def serve_api_100ms_delay():
    with serve_api(WEB_CONCURRENCY=SERVER_WORKERS, ID_LIMIT=ID_LIMIT, MAX_DELAY=0.1) as request_function:
        yield request_function
