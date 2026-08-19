from __future__ import annotations

import pytest

from limelight.config import DEMO_MODE_NARRATE, DEMO_MODE_PRESENT, DEMO_MODE_SILENT, SPEED_FACTORS, DemoConfig


ENVIRONMENT_VARIABLES = (
    'DEMO_FAST',
    'DEMO_MODE',
    'DEMO_SHOTS',
    'DEMO_SPEED',
    'DEMO_STEP_MS',
    'DEMO_VIDEO',
)


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)

    return monkeypatch


def test_defaults_are_silent(environment: pytest.MonkeyPatch) -> None:
    config = DemoConfig.from_env()

    assert config.mode == DEMO_MODE_SILENT
    assert config.narrated is False
    assert config.shots is False
    assert config.video is False
    assert config.speed_factor == 1.0


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


def test_fast_flag_means_turbo(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_FAST', '1')

    config = DemoConfig.from_env()

    assert config.speed_factor == SPEED_FACTORS['turbo']


def test_fast_flag_accepts_any_truthy_spelling(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_FAST', 'yes')

    config = DemoConfig.from_env()

    assert config.speed_factor == SPEED_FACTORS['turbo']


def test_step_ms_from_environment(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_STEP_MS', '2500')

    config = DemoConfig.from_env()

    assert config.timing.step_ms == 2500


def test_step_ms_non_numeric_rejected(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_STEP_MS', 'slow')

    with pytest.raises(ValueError, match='DEMO_STEP_MS'):
        DemoConfig.from_env()


def test_step_ms_zero_rejected(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_STEP_MS', '0')

    with pytest.raises(ValueError, match='DEMO_STEP_MS'):
        DemoConfig.from_env()


def test_shots_and_video_truthy(environment: pytest.MonkeyPatch) -> None:
    environment.setenv('DEMO_SHOTS', 'yes')
    environment.setenv('DEMO_VIDEO', 'true')

    config = DemoConfig.from_env()

    assert config.shots is True
    assert config.video is True


def test_constructor_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match='mode'):
        DemoConfig(mode='loud')
