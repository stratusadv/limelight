from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.servers.basehttp import ThreadedWSGIServer
from django.test.testcases import LiveServerThread, QuietWSGIRequestHandler

if TYPE_CHECKING:
    from socket import socket


class SequentialWSGIRequestHandler(QuietWSGIRequestHandler):
    protocol_version = 'HTTP/1.0'


class SequentialWSGIServer(ThreadedWSGIServer):
    def process_request(  # ty: ignore[missing-override-decorator]
        self,
        request: socket | tuple[bytes, socket],
        client_address: str | tuple[str, int],
    ) -> None:
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


class SequentialLiveServerThread(LiveServerThread):
    def _create_server(  # ty: ignore[missing-override-decorator]
        self,
        connections_override: dict[str, object] | None = None,
    ) -> SequentialWSGIServer:
        return SequentialWSGIServer(
            (self.host, self.port),
            SequentialWSGIRequestHandler,
            allow_reuse_address=False,
            connections_override=connections_override,
        )
