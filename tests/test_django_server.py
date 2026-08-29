from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from limelight.django.server import (
    SequentialLiveServerThread,
    SequentialWSGIRequestHandler,
    SequentialWSGIServer,
)

if TYPE_CHECKING:
    from typing import Any


def server_stub(calls: list[tuple[str, object]], *, fails: bool = False) -> Any:
    def finish_request(request: object, client_address: object) -> None:
        calls.append(('finish', request))

        if fails:
            message = 'the handler blew up'
            raise RuntimeError(message)

    return SimpleNamespace(
        finish_request=finish_request,
        handle_error=lambda request, client_address: calls.append(('error', request)),
        shutdown_request=lambda request: calls.append(('shutdown', request)),
    )


def test_a_request_is_served_in_the_calling_thread() -> None:
    calls: list[tuple[str, object]] = []

    process_request = cast('Any', SequentialWSGIServer.process_request)

    process_request(server_stub(calls), 'socket', 'client')

    assert calls == [('finish', 'socket'), ('shutdown', 'socket')]


def test_a_handler_that_raises_is_reported_and_still_shut_down() -> None:
    calls: list[tuple[str, object]] = []

    process_request = cast('Any', SequentialWSGIServer.process_request)

    process_request(server_stub(calls, fails=True), 'socket', 'client')

    assert calls == [('finish', 'socket'), ('error', 'socket'), ('shutdown', 'socket')]


def test_the_thread_builds_a_sequential_server() -> None:
    thread = cast('Any', object.__new__(SequentialLiveServerThread))

    thread.host = 'localhost'
    thread.port = 0

    server = thread._create_server()

    try:
        assert isinstance(server, SequentialWSGIServer)
        assert server.RequestHandlerClass is SequentialWSGIRequestHandler
        assert server.allow_reuse_address is False
    finally:
        server.server_close()


def test_the_request_handler_closes_every_connection() -> None:
    assert SequentialWSGIRequestHandler.protocol_version == 'HTTP/1.0'
