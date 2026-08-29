from __future__ import annotations

import os

from dataclasses import dataclass

from limelight.ffmpeg import FRAMES_CRF_DEFAULT, FRAMES_PRESET_DEFAULT


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

STEP_MS_DEFAULT = 4500

VIDEO_QUALITY_DEFAULT = 'medium'


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


VIDEO_QUALITIES = {
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
}


def _flag_from_env(name: str) -> bool:
    """
    A function that reads a boolean flag from the environment.

    :param name: The name of the environment variable.
    :return: True if the variable holds a truthy word, False otherwise.
    """

    return _text_from_env(name) in FLAG_TRUTHY


def _mode_from_env() -> str:
    """
    A function that reads the demo mode from the environment.

    :return: The mode named by DEMO_MODE, or silent if it is unset.
    :raises ValueError: If DEMO_MODE names an unknown mode.
    """

    mode = _text_from_env('DEMO_MODE') or DEMO_MODE_SILENT

    if mode not in DEMO_MODES:
        options = ', '.join(DEMO_MODES)

        message = f'DEMO_MODE must be one of: {options} (got "{mode}")'
        raise ValueError(message)

    return mode


def _quality_from_env() -> str:
    """
    A function that reads the video quality from the environment.

    :return: The quality named by DEMO_VIDEO_QUALITY, or the default if it is unset.
    :raises ValueError: If DEMO_VIDEO_QUALITY names an unknown quality.
    """

    quality = _text_from_env('DEMO_VIDEO_QUALITY') or VIDEO_QUALITY_DEFAULT

    if quality not in VIDEO_QUALITIES:
        options = ', '.join(VIDEO_QUALITIES)

        message = f'DEMO_VIDEO_QUALITY must be one of: {options} (got "{quality}")'
        raise ValueError(message)

    return quality


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
    mode: str = DEMO_MODE_SILENT
    quality: str = VIDEO_QUALITY_DEFAULT
    shots: bool = False
    speed_factor: float = 1.0
    step_ms: int = STEP_MS_DEFAULT
    video: bool = False

    def __post_init__(self) -> None:
        """
        A method that rejects a configuration whose fields disagree.

        :raises ValueError: If the mode, quality, speed factor, or step duration is
            invalid, or if video is asked for in present mode.
        """

        if self.mode not in DEMO_MODES:
            options = ', '.join(DEMO_MODES)

            message = f'mode must be one of: {options} (got "{self.mode}")'
            raise ValueError(message)

        if self.quality not in VIDEO_QUALITIES:
            options = ', '.join(VIDEO_QUALITIES)

            message = f'quality must be one of: {options} (got "{self.quality}")'
            raise ValueError(message)

        if self.speed_factor <= 0:
            message = f'speed_factor must be positive: {self.speed_factor}'
            raise ValueError(message)

        if self.step_ms <= 0:
            message = f'step_ms must be positive: {self.step_ms}'
            raise ValueError(message)

        if self.video:
            if self.mode == DEMO_MODE_PRESENT:
                message = 'present mode waits for a keypress per step; it cannot record video'
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
            mode=_mode_from_env(),
            quality=_quality_from_env(),
            shots=_flag_from_env('DEMO_SHOTS'),
            speed_factor=_speed_factor_from_env(),
            step_ms=_step_ms_from_env(),
            video=_flag_from_env('DEMO_VIDEO'),
        )

    @property
    def controls(self) -> bool:
        """
        A property that reports whether the on-screen playback controls are drawn.

        The controls are hidden while recording because they would be baked into the
        frames, so they appear in every mode except video.

        :return: True if the controls are drawn, False otherwise.
        """

        return not self.video

    @property
    def narrated(self) -> bool:
        """
        A property that reports whether the run speaks its captions.

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
