from __future__ import annotations

import socket

from urllib.parse import urlsplit


ENDPOINT_HOST = '127.0.0.1'

LAUNCH_ARGUMENTS_FRAME_CONTROL = (
    '--disable-checker-imaging',
    '--disable-image-animation-resync',
    '--disable-threaded-animation',
    '--disable-threaded-scrolling',
    '--enable-begin-frame-control',
    '--hide-scrollbars',
    '--run-all-compositor-stages-before-draw',
)


def endpoint_free() -> str:
    """
    A function that reserves a free local port for the debugging endpoint.

    The socket is bound and closed rather than held, so the port is only known
    to be free at the moment it is picked: Chrome has to be launched onto it
    before something else takes it.

    :return: The URL of the debugging endpoint.
    """

    with socket.socket() as listener:
        listener.bind((ENDPOINT_HOST, 0))

        port = listener.getsockname()[1]

    return f'http://{ENDPOINT_HOST}:{port}'


def endpoint_port(endpoint: str) -> int:
    """
    A function that reads the port out of a debugging endpoint URL.

    :param endpoint: The URL of the debugging endpoint.
    :return: The port the endpoint listens on.
    :raises ValueError: If the endpoint carries no port.
    """

    port = urlsplit(endpoint).port

    if port is None:
        message = f'the endpoint carries no port: {endpoint}'
        raise ValueError(message)

    return port


def launch_arguments_frame_control(endpoint: str, *, device_scale_factor: int = 1) -> list[str]:
    """
    A function that builds the Chrome arguments for frame-by-frame capture.

    The switches hand the compositor to the driver: animation and scrolling are
    pulled off their own threads, every compositor stage runs before a draw, and
    begin-frame control lets the renderer produce one frame per request rather
    than on a wall clock, so a slow screenshot cannot skew the timeline.

    :param endpoint: The URL of the debugging endpoint Chrome listens on.
    :param device_scale_factor: The pixel ratio the page is rendered at.
    :return: The command-line arguments to launch Chrome with.
    :raises ValueError: If the device scale factor is not positive.
    """

    if device_scale_factor < 1:
        message = f'device_scale_factor must be positive: {device_scale_factor}'
        raise ValueError(message)

    return [
        *LAUNCH_ARGUMENTS_FRAME_CONTROL,
        f'--force-device-scale-factor={device_scale_factor}',
        f'--remote-debugging-port={endpoint_port(endpoint)}',
    ]
