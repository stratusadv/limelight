from __future__ import annotations

import os

from dataclasses import dataclass, field

from limelight.timing import STEP_MS_DEFAULT, DemoTiming


DEMO_MODE_NARRATE = 'narrate'
DEMO_MODE_PRESENT = 'present'
DEMO_MODE_SILENT = 'silent'
DEMO_MODES = (DEMO_MODE_NARRATE, DEMO_MODE_PRESENT, DEMO_MODE_SILENT)
DEMO_MODES_NARRATED = (DEMO_MODE_NARRATE, DEMO_MODE_PRESENT)

FLAG_TRUTHY = ('1', 'true', 'yes', 'on')

SPEED_DEFAULT = 'normal'
SPEED_FACTORS = {
    'normal': 1.0,
    'fast': 2.0,
    'faster': 4.0,
    'turbo': 1000.0,
}


def _flag_from_env(name: str) -> bool:
    return _text_from_env(name) in FLAG_TRUTHY


def _mode_from_env() -> str:
    mode = _text_from_env('DEMO_MODE') or DEMO_MODE_SILENT

    if mode not in DEMO_MODES:
        options = ', '.join(DEMO_MODES)

        message = f'DEMO_MODE must be one of: {options} (got "{mode}")'
        raise ValueError(message)

    return mode


def _speed_factor_from_env() -> float:
    return SPEED_FACTORS[_speed_from_env()]


def _speed_from_env() -> str:
    speed = _text_from_env('DEMO_SPEED')

    if not speed and _flag_from_env('DEMO_FAST'):
        speed = 'turbo'

    if not speed:
        speed = SPEED_DEFAULT

    if speed not in SPEED_FACTORS:
        options = ', '.join(SPEED_FACTORS)

        message = f'DEMO_SPEED must be one of: {options} (got "{speed}")'
        raise ValueError(message)

    return speed


def _step_ms_from_env() -> int:
    step_ms_text = _text_from_env('DEMO_STEP_MS')

    if not step_ms_text:
        return STEP_MS_DEFAULT

    if not step_ms_text.isdigit():
        message = f'DEMO_STEP_MS must be a whole number of milliseconds (got "{step_ms_text}")'
        raise ValueError(message)

    step_ms = int(step_ms_text)

    if step_ms < 1:
        message = f'DEMO_STEP_MS must be positive: {step_ms}'
        raise ValueError(message)

    return step_ms


def _text_from_env(name: str) -> str:
    return (os.environ.get(name) or '').strip().lower()


def _timing_from_env() -> DemoTiming:
    return DemoTiming(step_ms=_step_ms_from_env())


@dataclass(frozen=True)
class DemoConfig:
    mode: str = DEMO_MODE_SILENT
    shots: bool = False
    speed_factor: float = 1.0
    timing: DemoTiming = field(default_factory=DemoTiming)
    video: bool = False

    def __post_init__(self) -> None:
        if self.mode not in DEMO_MODES:
            options = ', '.join(DEMO_MODES)

            message = f'mode must be one of: {options} (got "{self.mode}")'
            raise ValueError(message)

        if self.speed_factor <= 0:
            message = f'speed_factor must be positive: {self.speed_factor}'
            raise ValueError(message)

        if self.mode == DEMO_MODE_PRESENT and self.video:
            message = 'present mode waits for a keypress per step; it cannot record video'
            raise ValueError(message)

    @classmethod
    def from_env(cls) -> DemoConfig:
        return cls(
            mode=_mode_from_env(),
            shots=_flag_from_env('DEMO_SHOTS'),
            speed_factor=_speed_factor_from_env(),
            timing=_timing_from_env(),
            video=_flag_from_env('DEMO_VIDEO'),
        )

    @property
    def narrated(self) -> bool:
        return self.mode in DEMO_MODES_NARRATED

    @property
    def present(self) -> bool:
        return self.mode == DEMO_MODE_PRESENT
