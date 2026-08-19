from __future__ import annotations

import pytest

from limelight.timing import FAST_MS_MIN, DemoTiming


def test_scale_factor_below_one_scales_and_floors() -> None:
    timing = DemoTiming(step_ms=4000, scale_factor=0.5)

    assert timing.scale(4000) == 2000
    assert timing.scale(10) == FAST_MS_MIN


def test_scale_factor_one_returns_ms_unchanged() -> None:
    timing = DemoTiming()

    assert timing.scale(1234) == 1234


def test_scale_rejects_negative_ms() -> None:
    timing = DemoTiming()

    with pytest.raises(ValueError, match='non-negative'):
        timing.scale(-1)


def test_scale_factor_zero_rejected() -> None:
    with pytest.raises(ValueError, match='scale_factor'):
        DemoTiming(scale_factor=0)


def test_step_ms_zero_rejected() -> None:
    with pytest.raises(ValueError, match='step_ms'):
        DemoTiming(step_ms=0)
