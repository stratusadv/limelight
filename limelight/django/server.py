from __future__ import annotations

import socketserver

from typing import TYPE_CHECKING
from typing_extensions import override

from django.core.servers.basehttp import ThreadedWSGIServer
from django.test.testcases import LiveServerThread, QuietWSGIRequestHandler

if TYPE_CHECKING:
    from socket import socket


class SequentialWSGIRequestHandler(QuietWSGIRequestHandler):
    """
    A request handler that closes the connection after each response.

    The protocol is pinned to HTTP/1.0 so the browser cannot hold a connection open
    across requests, because a kept-alive connection occupies a server thread that
    an in-memory database has no second connection to spare.
    """

    protocol_version = 'HTTP/1.0'


class SequentialWSGIServer(ThreadedWSGIServer):
    """
    A live server that handles one request at a time.

    This class serves each request on the calling thread, so each query reaches
    the same connection and an in-memory SQLite database stays visible to the test
    that created it.
    """

    @override
    def process_request(
        self,
        request: socket | tuple[bytes, socket],
        client_address: str | tuple[str, int],
    ) -> None:
        """
        A method that handles a request on the calling thread.

        :param request: The socket the request arrived on.
        :param client_address: The address the request came from.
        """

        socketserver.ThreadingMixIn.process_request_thread(self, request, client_address)


class SequentialLiveServerThread(LiveServerThread):
    """A live server thread that serves requests sequentially."""

    @override
    def _create_server(
        self,
        connections_override: dict[str, object] | None = None,
    ) -> SequentialWSGIServer:
        """
        A method that builds the sequential server the thread runs.

        :param connections_override: The connections the server uses instead of its own.
        :return: The server the thread runs.
        """

        return SequentialWSGIServer(
            (self.host, self.port),
            SequentialWSGIRequestHandler,
            allow_reuse_address=False,
            connections_override=connections_override,
        )
