from __future__ import annotations

import pytest

from typing import TYPE_CHECKING, cast

from limelight import limits
from limelight.config import (
    DEMO_MODE_NARRATE,
    DEMO_MODE_PRESENT,
    DEMO_MODE_SILENT,
    SPEED_FACTORS,
    DemoConfig,
    VIDEO_QUALITIES,
    VIDEO_QUALITY_DEFAULT,
)

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


ENVIRONMENT_VARIABLES = (
    'DEMO_MODE',
    'DEMO_SHOTS',
    'DEMO_SPEED',
    'DEMO_STEP_MS',
    'DEMO_VIDEO',
    'DEMO_VIDEO_QUALITY',
)


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)

    return monkeypatch


@pytest.mark.usefixtures('environment')
def test_defaults_are_silent() -> None:
    config = DemoConfig.from_env()

    assert config.mode == DEMO_MODE_SILENT
    assert config.narrated is False
    assert config.shots is False
    assert config.video is False
    assert config.speed_factor == pytest.approx(1.0)


def test_mode_narrate(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_MODE', 'narrate')

    config = DemoConfig.from_env()

    assert config.mode == DEMO_MODE_NARRATE
    assert config.narrated is True


def test_mode_present(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_MODE', 'present')

    config = DemoConfig.from_env()

    assert config.mode == DEMO_MODE_PRESENT
    assert config.narrated is True
    assert config.present is True


def test_present_with_video_rejected(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_MODE', 'present')
    environment.setenv('DEMO_VIDEO', '1')

    with pytest.raises(ValueError, match='present'):
        DemoConfig.from_env()


def test_silent_with_video_rejected(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_VIDEO', '1')

    with pytest.raises(ValueError, match='video needs narrate mode'):
        DemoConfig.from_env()


def test_mode_invalid_rejected(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_MODE', 'loud')

    with pytest.raises(ValueError, match='DEMO_MODE'):
        DemoConfig.from_env()


def test_speed_sets_the_playback_factor(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_SPEED', 'fast')

    config = DemoConfig.from_env()

    assert config.speed_factor == SPEED_FACTORS['fast']


def test_speed_invalid_rejected(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_SPEED', 'ludicrous')

    with pytest.raises(ValueError, match='DEMO_SPEED'):
        DemoConfig.from_env()


def test_step_ms_from_environment(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_STEP_MS', '2500')

    config = DemoConfig.from_env()

    assert config.step_ms == 2500


def test_step_ms_non_numeric_rejected(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_STEP_MS', 'slow')

    with pytest.raises(ValueError, match='DEMO_STEP_MS'):
        DemoConfig.from_env()


def test_step_ms_zero_rejected(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_STEP_MS', '0')

    with pytest.raises(ValueError, match='step_ms'):
        DemoConfig.from_env()


def test_shots_and_video_truthy(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_MODE', 'narrate')
    environment.setenv('DEMO_SHOTS', 'yes')
    environment.setenv('DEMO_VIDEO', 'true')

    config = DemoConfig.from_env()

    assert config.shots is True
    assert config.video is True


def test_constructor_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match='mode'):
        DemoConfig(mode=cast('Any', 'loud'))


def test_constructor_rejects_speed_factor_zero() -> None:
    with pytest.raises(ValueError, match='speed_factor'):
        DemoConfig(speed_factor=0)


def test_constructor_rejects_step_ms_zero() -> None:
    with pytest.raises(ValueError, match='step_ms'):
        DemoConfig(step_ms=0)


def test_video_disables_controls() -> None:
    assert DemoConfig(mode='narrate').controls is True
    assert DemoConfig(mode='narrate', video=True).controls is False


@pytest.mark.usefixtures('environment')
def test_quality_defaults_to_medium() -> None:
    config = DemoConfig.from_env()

    assert config.quality == VIDEO_QUALITY_DEFAULT
    assert config.video_quality == VIDEO_QUALITIES['medium']


def test_quality_from_the_environment(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_VIDEO_QUALITY', 'low')

    config = DemoConfig.from_env()

    assert config.quality == 'low'
    assert config.video_quality == VIDEO_QUALITIES['low']


def test_an_unknown_quality_from_the_environment_is_refused(
    environment: pytest.MonkeyPatch,
) -> None:
    environment.setenv('DEMO_VIDEO_QUALITY', 'cinematic')

    with pytest.raises(ValueError, match='DEMO_VIDEO_QUALITY must be one of'):
        DemoConfig.from_env()


def test_constructor_rejects_an_unknown_quality() -> None:
    with pytest.raises(ValueError, match='quality must be one of'):
        DemoConfig(quality=cast('Any', 'cinematic'))


def test_every_quality_falls_within_the_encoder_bounds() -> None:
    for quality in VIDEO_QUALITIES.values():
        assert quality.crf >= 0
        assert quality.device_scale_factor >= 1
        assert quality.fps >= 1
        assert quality.preset
        assert 0 <= quality.screenshot_quality <= 100


def test_lower_qualities_cost_less_than_higher_ones() -> None:
    low = VIDEO_QUALITIES['low']
    medium = VIDEO_QUALITIES['medium']
    high = VIDEO_QUALITIES['high']

    assert low.crf > medium.crf > high.crf
    assert low.screenshot_quality < medium.screenshot_quality < high.screenshot_quality
    assert low.device_scale_factor <= medium.device_scale_factor <= high.device_scale_factor


def test_the_cursor_is_drawn_unless_the_environment_hides_it(
    environment: pytest.MonkeyPatch,
) -> None:
    assert DemoConfig.from_env().cursor_hidden is False

    environment.setenv('DEMO_CURSOR_HIDDEN', 'true')

    assert DemoConfig.from_env().cursor_hidden is True


def test_holds_from_environment(environment: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / 'holds.json'
    path.write_text('{"Open the order Navigate to it.": 6200}', encoding='utf-8')
    environment.setenv('DEMO_HOLDS', str(path))

    config = DemoConfig.from_env()

    assert config.hold_ms_for('Open the order Navigate to it.') == 6200
    assert config.hold_ms_for('Unknown') is None


def test_holds_missing_file_rejected(environment: pytest.MonkeyPatch, tmp_path: Path) -> None:
    environment.setenv('DEMO_HOLDS', str(tmp_path / 'absent.json'))

    with pytest.raises(ValueError, match='DEMO_HOLDS'):
        DemoConfig.from_env()


def test_holds_non_positive_rejected() -> None:
    with pytest.raises(ValueError, match='positive whole number'):
        DemoConfig(holds={'Open the order': 0})


def test_constructor_rejects_speed_factor_outside_the_playable_range() -> None:
    with pytest.raises(ValueError, match=r'speed_factor must be from 0\.1 to 1000\.0: 0\.05'):
        DemoConfig(speed_factor=0.05)

    with pytest.raises(ValueError, match=r'speed_factor must be from 0\.1 to 1000\.0: 1000\.5'):
        DemoConfig(speed_factor=1000.5)


def test_constructor_accepts_the_speed_factor_limits() -> None:
    assert DemoConfig(speed_factor=limits.SPEED_FACTOR_MIN).speed_factor == limits.SPEED_FACTOR_MIN
    assert DemoConfig(speed_factor=limits.SPEED_FACTOR_MAX).speed_factor == limits.SPEED_FACTOR_MAX


def test_constructor_rejects_step_ms_past_the_hold_limit() -> None:
    with pytest.raises(ValueError, match=f'step_ms must be from 1 to {limits.HOLD_MS_MAX}'):
        DemoConfig(step_ms=limits.HOLD_MS_MAX + 1)

    assert DemoConfig(step_ms=limits.HOLD_MS_MAX).step_ms == limits.HOLD_MS_MAX


def test_holds_past_the_hold_limit_rejected() -> None:
    with pytest.raises(ValueError, match=f'up to {limits.HOLD_MS_MAX}'):
        DemoConfig(holds={'Open the order': limits.HOLD_MS_MAX + 1})

    config = DemoConfig(holds={'Open the order': limits.HOLD_MS_MAX})

    assert config.hold_ms_for('Open the order') == limits.HOLD_MS_MAX


def test_holds_are_a_read_only_copy_of_the_mapping_given() -> None:
    holds = {'Open the order': 900}
    config = DemoConfig(holds=holds)

    holds['Open the order'] = 1

    assert config.hold_ms_for('Open the order') == 900

    with pytest.raises(TypeError):
        cast('dict[str, int]', config.holds)['Open the order'] = 1
