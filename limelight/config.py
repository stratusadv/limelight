from __future__ import annotations

import json
import os

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from limelight.ffmpeg import FRAMES_CRF_DEFAULT, FRAMES_PRESET_DEFAULT
from limelight.limits import HOLD_MS_MAX, SPEED_FACTOR_MAX, SPEED_FACTOR_MIN


DemoMode = Literal['narrate', 'present', 'silent']
VideoQualityName = Literal['high', 'low', 'medium']

DEMO_MODE_NARRATE: DemoMode = 'narrate'
DEMO_MODE_PRESENT: DemoMode = 'present'
DEMO_MODE_SILENT: DemoMode = 'silent'
DEMO_MODES: tuple[DemoMode, ...] = (DEMO_MODE_NARRATE, DEMO_MODE_PRESENT, DEMO_MODE_SILENT)
DEMO_MODES_NARRATED: tuple[DemoMode, ...] = (DEMO_MODE_NARRATE, DEMO_MODE_PRESENT)

FLAG_TRUTHY = ('1', 'true', 'yes', 'on')

HOLDS_NONE: Mapping[str, int] = MappingProxyType[str, int]({})

SPEED_DEFAULT = 'normal'

SPEED_FACTORS = MappingProxyType(
    {
        'normal': 1.0,
        'fast': 2.0,
        'faster': 4.0,
        'turbo': 1000.0,
    },
)

STEP_MS_DEFAULT = 4500

VIDEO_QUALITY_DEFAULT: VideoQualityName = 'medium'


@dataclass(frozen=True)
class VideoQuality:
    """
    A bundle of the encoder and capture settings for one quality level.

    This class carries the values that have to agree with each other: the frame
    rate the timeline is built at, the scale the page is rendered at, and the
    constant rate factor and preset handed to the encoder.
    """

    crf: int
    device_scale_factor: int
    fps: int
    preset: str
    screenshot_quality: int


VIDEO_QUALITIES: Mapping[VideoQualityName, VideoQuality] = MappingProxyType(
    {
        'low': VideoQuality(
            crf=30,
            device_scale_factor=1,
            fps=24,
            preset='veryfast',
            screenshot_quality=75,
        ),
        'medium': VideoQuality(
            crf=23,
            device_scale_factor=1,
            fps=30,
            preset=FRAMES_PRESET_DEFAULT,
            screenshot_quality=90,
        ),
        'high': VideoQuality(
            crf=FRAMES_CRF_DEFAULT,
            device_scale_factor=2,
            fps=60,
            preset=FRAMES_PRESET_DEFAULT,
            screenshot_quality=100,
        ),
    },
)


def _flag_from_env(name: str) -> bool:
    """
    A function that reads a boolean flag from the environment.

    :param name: The name of the environment variable.
    :return: True if the variable holds a truthy word, False otherwise.
    """

    return _text_from_env(name) in FLAG_TRUTHY


def _holds_from_env() -> Mapping[str, int]:
    """
    A function that reads the per-cue hold lengths from the environment.

    :return: The hold in milliseconds for each spoken cue, keyed by its text, or an
        empty mapping if DEMO_HOLDS is unset.
    :raises ValueError: If DEMO_HOLDS names a missing file or one that is not a JSON
        object of positive whole numbers.
    """

    path_text = (os.environ.get('DEMO_HOLDS') or '').strip()

    if not path_text:
        return HOLDS_NONE

    path = Path(path_text)

    if not path.is_file():
        message = f'DEMO_HOLDS must name a JSON file (got "{path_text}")'
        raise ValueError(message)

    return holds_validate(json.loads(path.read_text(encoding='utf-8')), source=path_text)


def _mode_from_env() -> DemoMode:
    """
    A function that reads the demo mode from the environment.

    :return: The mode named by DEMO_MODE, or silent if it is unset.
    :raises ValueError: If DEMO_MODE names an unknown mode.
    """

    mode_text = _text_from_env('DEMO_MODE') or DEMO_MODE_SILENT

    for mode in DEMO_MODES:
        if mode == mode_text:
            return mode

    options = ', '.join(DEMO_MODES)

    message = f'DEMO_MODE must be one of: {options} (got "{mode_text}")'
    raise ValueError(message)


def _quality_from_env() -> VideoQualityName:
    """
    A function that reads the video quality from the environment.

    :return: The quality named by DEMO_VIDEO_QUALITY, or the default if it is unset.
    :raises ValueError: If DEMO_VIDEO_QUALITY names an unknown quality.
    """

    quality_text = _text_from_env('DEMO_VIDEO_QUALITY') or VIDEO_QUALITY_DEFAULT

    for quality in VIDEO_QUALITIES:
        if quality == quality_text:
            return quality

    options = ', '.join(VIDEO_QUALITIES)

    message = f'DEMO_VIDEO_QUALITY must be one of: {options} (got "{quality_text}")'
    raise ValueError(message)


def _speed_factor_from_env() -> float:
    """
    A function that reads the playback speed from the environment.

    :return: The multiplier the step duration is divided by.
    :raises ValueError: If DEMO_SPEED names an unknown speed.
    """

    speed = _text_from_env('DEMO_SPEED') or SPEED_DEFAULT

    if speed not in SPEED_FACTORS:
        options = ', '.join(SPEED_FACTORS)

        message = f'DEMO_SPEED must be one of: {options} (got "{speed}")'
        raise ValueError(message)

    return SPEED_FACTORS[speed]


def _step_ms_from_env() -> int:
    """
    A function that reads the default step duration from the environment.

    :return: The number of milliseconds a step holds for.
    :raises ValueError: If DEMO_STEP_MS is not a whole number.
    """

    step_ms_text = _text_from_env('DEMO_STEP_MS')

    if not step_ms_text:
        return STEP_MS_DEFAULT

    if not step_ms_text.isdigit():
        message = f'DEMO_STEP_MS must be a whole number of milliseconds (got "{step_ms_text}")'
        raise ValueError(message)

    return int(step_ms_text)


def holds_validate(value: object, *, source: str) -> Mapping[str, int]:
    """
    A function that checks a hold mapping and returns it as text to milliseconds.

    :param value: The decoded mapping to check.
    :param source: The origin of the mapping, named in the failure.
    :return: A read-only copy of the hold in milliseconds for each cue text.
    :raises TypeError: If the value is not a mapping.
    :raises ValueError: If a hold is not a whole number of milliseconds between one
        and the hold limit, keyed by non-empty text.
    """

    if not isinstance(value, Mapping):
        message = f'{source}: holds must be a JSON object of cue text to milliseconds'
        raise TypeError(message)

    holds: dict[str, int] = {}

    for text, hold_ms in value.items():
        message = (
            f'{source}: hold for {text!r} must be a positive whole number of milliseconds '
            f'up to {HOLD_MS_MAX}'
        )

        if not _hold_text_is_valid(text):
            raise ValueError(message)

        if not _hold_ms_is_valid(hold_ms):
            raise ValueError(message)

        holds[text] = hold_ms

    return MappingProxyType(holds)


def _hold_ms_is_valid(hold_ms: object) -> bool:
    """
    A function that reports whether a hold is a whole number of milliseconds a demo can play.

    A boolean is rejected even though Python counts it as an int, because a JSON
    true would otherwise pass as a one millisecond hold.

    :param hold_ms: The decoded hold to check.
    :return: True if the hold is an int from one to the hold limit, False otherwise.
    """

    if not isinstance(hold_ms, int):
        return False

    if isinstance(hold_ms, bool):
        return False

    return 1 <= hold_ms <= HOLD_MS_MAX


def _hold_text_is_valid(text: object) -> bool:
    """
    A function that reports whether a hold is keyed by non-empty text.

    :param text: The decoded key to check.
    :return: True if the key is a non-empty string, False otherwise.
    """

    if not isinstance(text, str):
        return False

    return bool(text)


def _text_from_env(name: str) -> str:
    """
    A function that reads an environment variable as trimmed lowercase text.

    :param name: The name of the environment variable.
    :return: The value of the variable, or an empty string if it is unset.
    """

    return (os.environ.get(name) or '').strip().lower()


@dataclass(frozen=True)
class DemoConfig:
    """
    A configuration for a single demo run.

    This class holds the mode, the pacing, and the artifacts a run produces. The
    values come either from the environment or from a test that builds one
    directly.
    """

    cursor_hidden: bool = False
    holds: Mapping[str, int] = field(default_factory=dict)
    mode: DemoMode = DEMO_MODE_SILENT
    quality: VideoQualityName = VIDEO_QUALITY_DEFAULT
    shots: bool = False
    speed_factor: float = 1.0
    step_ms: int = STEP_MS_DEFAULT
    video: bool = False

    def __post_init__(self) -> None:
        """
        A method that rejects a configuration whose fields disagree.

        :raises TypeError: If the holds are not a mapping.
        :raises ValueError: If the mode, quality, speed factor, step duration, or a
            hold is invalid, or if video is asked for in present or silent mode.
        """

        if self.mode not in DEMO_MODES:
            options = ', '.join(DEMO_MODES)

            message = f'mode must be one of: {options} (got "{self.mode}")'
            raise ValueError(message)

        if self.quality not in VIDEO_QUALITIES:
            options = ', '.join(VIDEO_QUALITIES)

            message = f'quality must be one of: {options} (got "{self.quality}")'
            raise ValueError(message)

        if not SPEED_FACTOR_MIN <= self.speed_factor <= SPEED_FACTOR_MAX:
            message = (
                f'speed_factor must be from {SPEED_FACTOR_MIN} to {SPEED_FACTOR_MAX}: '
                f'{self.speed_factor}'
            )

            raise ValueError(message)

        if not 1 <= self.step_ms <= HOLD_MS_MAX:
            message = f'step_ms must be from 1 to {HOLD_MS_MAX}: {self.step_ms}'
            raise ValueError(message)

        holds = holds_validate(self.holds, source='holds')

        object.__setattr__(self, 'holds', holds)

        if self.video:
            if self.mode == DEMO_MODE_PRESENT:
                message = 'present mode waits for a keypress per step; it cannot record video'
                raise ValueError(message)

            if self.mode == DEMO_MODE_SILENT:
                message = 'silent mode starts no renderer; video needs narrate mode'
                raise ValueError(message)

    @classmethod
    def from_env(cls) -> DemoConfig:
        """
        A method that builds a configuration from the DEMO_ environment variables.

        :return: The configuration described by the environment.
        :raises ValueError: If any of the variables carries an unknown value.
        """

        return cls(
            cursor_hidden=_flag_from_env('DEMO_CURSOR_HIDDEN'),
            holds=_holds_from_env(),
            mode=_mode_from_env(),
            quality=_quality_from_env(),
            shots=_flag_from_env('DEMO_SHOTS'),
            speed_factor=_speed_factor_from_env(),
            step_ms=_step_ms_from_env(),
            video=_flag_from_env('DEMO_VIDEO'),
        )

    def hold_ms_for(self, text: str) -> int | None:
        """
        A method that looks up the hold a spoken cue asks for.

        :param text: The spoken text of the cue, as the voiceover renders it.
        :return: The hold in milliseconds, or None if the cue has no hold of its own.
        """

        return self.holds.get(text)

    @property
    def controls(self) -> bool:
        """
        A property that reports whether the on-screen playback controls are drawn.

        The controls are hidden while recording because they would be baked into the
        frames, so they appear in each mode except video.

        :return: True if the controls are drawn, False otherwise.
        """

        return not self.video

    @property
    def narrated(self) -> bool:
        """
        A property that reports whether the run draws the overlay and records a transcript.

        :return: True if the mode is narrate or present, False otherwise.
        """

        return self.mode in DEMO_MODES_NARRATED

    @property
    def present(self) -> bool:
        """
        A property that reports whether the run waits for a keypress per step.

        :return: True if the mode is present, False otherwise.
        """

        return self.mode == DEMO_MODE_PRESENT

    @property
    def video_quality(self) -> VideoQuality:
        """
        A property that resolves the quality name into its settings.

        :return: The encoder and capture settings for the configured quality.
        """

        return VIDEO_QUALITIES[self.quality]
