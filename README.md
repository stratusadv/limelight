# limelight

A narration layer for Playwright that turns end-to-end tests into demo videos.

## Overview

A limelight test is written once and runs in two modes. The silent mode is a plain headless e2e test, where each narration call is a no-op. The narrated mode runs the same test headed with an overlay of caption cards, spotlights, an animated cursor, screenshots, and video. A test body never branches on the mode. The `DemoSession` facade is the whole API.

## Installation

Add limelight to your `pyproject.toml`:

```toml
[project.optional-dependencies]
development = [
    "limelight[django,pytest]",
]

[tool.uv.sources]
limelight = { git = "https://github.com/stratusadv/limelight", branch = "main" }
```

The `branch` key resolves to a commit that `uv.lock` pins, so a later commit on `main` reaches the project only after `uv lock --upgrade-package limelight`.

Install it directly with pip instead:

```
pip install "limelight[django,pytest] @ git+https://github.com/stratusadv/limelight@main"
```

The `django` extra installs the `limelight.django` adapter. The `pytest` extra installs `pytest` and `pytest-playwright` for the plugin.

## Usage

Register the plugin in `conftest.py`:

```python
pytest_plugins = ['limelight.pytest_plugin']
```

Write the demo as a test:

```python
from limelight import DemoSession
from limelight.django import DjangoApplication


def test_order_approval_demo(page, live_server, admin_user):
    application = DjangoApplication(live_server=live_server, user=admin_user)
    demo = DemoSession.start(page, application, shot_directory_name='order-approval')

    demo.goto('home:dashboard')
    demo.title_card('Order Approval')
    demo.narrate('Open the order')
    demo.click(page.get_by_role('link', name='Orders'))
```

Run it silent, then narrated:

```
pytest -k order_approval_demo
DEMO_MODE=narrate pytest -k order_approval_demo --headed
```

Turn a narrated run into an mp4, a walkthrough, and subtitles:

```
limelight-render test-results/order-approval --title "Order Approval"
```

## Configuration

| Variable | Description | Default |
|---|---|---|
| `DEMO_MODE` | The presenter and viewport policy, one of `silent`, `narrate`, or `present`. | `silent` |
| `DEMO_SPEED` | The playback speed the demo starts at, one of `normal`, `fast`, `faster`, or `turbo`. | `normal` |
| `DEMO_STEP_MS` | The base hold length in milliseconds. | `4500` |
| `DEMO_SHOTS` | Whether a narrated run writes screenshots. | off |
| `DEMO_VIDEO` | Whether to apply the video viewport and launch args. | off |
