from __future__ import annotations

import pytest

from limelight.capture.browser import (
    LAUNCH_ARGUMENTS_FRAME_CONTROL,
    endpoint_free,
    endpoint_port,
    launch_arguments_frame_control,
)


def test_endpoint_free_is_local_with_a_port() -> None:
    endpoint = endpoint_free()

    assert endpoint.startswith('http://127.0.0.1:')
    assert endpoint_port(endpoint) > 0


def test_endpoint_port_requires_a_port() -> None:
    with pytest.raises(ValueError, match='port'):
        endpoint_port('http://127.0.0.1')


def test_launch_arguments_carry_frame_control_scale_and_the_port() -> None:
    arguments = launch_arguments_frame_control('http://127.0.0.1:9333', device_scale_factor=2)

    assert arguments[:-2] == list(LAUNCH_ARGUMENTS_FRAME_CONTROL)
    assert arguments[-2:] == ['--force-device-scale-factor=2', '--remote-debugging-port=9333']


def test_launch_arguments_reject_a_zero_scale_factor() -> None:
    with pytest.raises(ValueError, match='device_scale_factor'):
        launch_arguments_frame_control('http://127.0.0.1:9333', device_scale_factor=0)
