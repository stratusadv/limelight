# Configuration

## Overview

A run reads these `DEMO_` environment variables. A test can build a [`DemoConfig`][limelight.DemoConfig] and pass it as `config` instead, and a [`Theme`][limelight.Theme] passed as `theme` sets the overlay colors and font.

| Variable | Description | Default |
|----------|-------------|---------|
| `DEMO_MODE` | The mode: `narrate`, `present`, or `silent`. | `silent` |
| `DEMO_SPEED` | The starting speed: `normal`, `fast`, `faster`, or `turbo`, which run at 1x, 2x, 4x, and 1000x. | `normal` |
| `DEMO_STEP_MS` | The default hold in whole milliseconds, up to [`HOLD_MS_MAX`][limelight.limits.HOLD_MS_MAX]. | `4500` |
| `DEMO_HOLDS` | The path of a JSON file that maps the text of each cue to its hold in whole milliseconds, up to [`HOLD_MS_MAX`][limelight.limits.HOLD_MS_MAX]. | Unset. |
| `DEMO_SHOTS` | The flag that makes a narrated run write screenshots. | Off. |
| `DEMO_VIDEO` | The flag that makes a narrated run render `video.mp4`. | Off. |
| `DEMO_VIDEO_QUALITY` | The render settings: `low`, `medium`, or `high`. | `medium` |
| `DEMO_CURSOR_HIDDEN` | The flag that leaves the pointer off a narrated run. | Off. |

A flag such as `DEMO_VIDEO` is on for `1`, `true`, `yes`, or `on`. The text of a cue is its title, subtitle, and body joined by spaces, which is the line a voiceover speaks. The pytest plugin reads these variables when pytest starts, so a value outside its range raises `ValueError` before the first test runs.

## Fixtures

The pytest plugin reads these session fixtures, and a project overrides one by defining a fixture of the same name in its `conftest.py`. Each size fixture returns a mapping of `width` and `height`.

| Fixture | Description | Default |
|---------|-------------|---------|
| `demo_viewport` | The viewport a silent run uses. | `1920x954` |
| `demo_viewport_video` | The viewport a recorded run uses. | `1920x1080` |
| `demo_window_size` | The window a Chromium run opens, which a narrated page fills. | `1920x1080` |
| `demo_console_error_ignored_fragments_extra` | The text of each console error the project tolerates. | None. |
| `demo_navigation_timeout_ms` | The time a navigation is allowed to take, from the Django plugin. | `60000` |

The plugin also turns on `--screenshot=only-on-failure` and `--tracing=retain-on-failure` unless you pass your own value, and it leaves tracing off for a recorded run.

## The Control Bar

A narrated run draws a control bar in the corner of the page, unless it is rendering video.

| Key | Action |
|-----|--------|
| ++space++ | The key pauses the demo, or resumes it. |
| ++arrow-right++ | The key ends the current hold. |
| ++arrow-up++ | The key moves up one speed. |
| ++arrow-down++ | The key moves down one speed. |
| ++end++ | The key jumps to turbo. |
| ++home++ | The key jumps to 0.1x. |

The `present` mode replaces each timed hold with a wait for the viewer, so run it with `--headed`. Press ++space++ or ++arrow-right++ to advance.

## Console Errors

The plugin fails a test whose page logs a `console.error` or throws an uncaught exception. Allow a console error you expect with a marker.

```python
@pytest.mark.console_error_expected('broken widget')
```

Override the `demo_console_error_ignored_fragments_extra` fixture to allow one across a project. An uncaught exception fails the test whatever you list.

## Limits

The [`limelight.limits`][limelight.limits] namespace holds the bounds a caller can read.

| Constant | Description |
|----------|-------------|
| `ELEMENT_WAIT_TIMEOUT_MS` | The wait most components give an element. |
| `HOLD_MS_MAX` | The longest hold a step can ask for. |
| `SPEED_FACTOR_MIN` | The slowest playback speed. |
| `SPEED_FACTOR_MAX` | The fastest playback speed. |
| `FRAME_COUNT_MAX` | The frame count at which a render aborts. |
