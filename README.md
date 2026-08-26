<p align="center">
    <picture>
        <source media="(prefers-color-scheme: dark)" srcset="assets/png/limelight-wordmark-on-dark-1567x404.png">
        <source media="(prefers-color-scheme: light)" srcset="assets/png/limelight-wordmark-mono-on-light-1567x404.png">
        <img alt="limelight" src="assets/png/limelight-wordmark-mono-on-light-1567x404.png" width="320">
    </picture>
</p>

&nbsp;

<p align="center">
    A narration layer for Playwright that turns end-to-end tests into demos.
</p>

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
limelight = { git = "https://github.com/stratusadv/limelight", tag = "v0.2.0" }
```

The `tag` key pins the install to one commit, so a later change on `main` reaches the project only after the pin moves to a newer tag and `uv lock --upgrade-package limelight` runs.

Install it directly with pip instead:

```
pip install "limelight[django,pytest] @ git+https://github.com/stratusadv/limelight@v0.2.0"
```

The `django` extra installs the `limelight.django` adapter. The `pytest` extra installs `pytest` and `pytest-playwright` for the plugin.

## Usage

Register the plugins in `conftest.py`. The first is Django-free; the second adds the live server and the page timeout a Django project needs:

```python
pytest_plugins = ['limelight.pytest_plugin', 'limelight.django.pytest_plugin']
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

Render the narrated run to video, then export the walkthrough and subtitles:

```
DEMO_MODE=narrate DEMO_VIDEO=1 pytest -k order_approval_demo
limelight-render test-results/order-approval --title "Order Approval"
```

`DEMO_VIDEO` does not record the screen. The browser runs headless under Chrome's begin-frame control, and limelight advances the compositor one frame at a time, screenshotting each one and piping it into ffmpeg. Every hold, glide and transition is measured in frames rather than wall time, so `video.mp4` comes out at 3840x2160 and 60 fps with one distinct frame per interval no matter how slow the machine is. Frames leave Chrome as JPEG at quality 100 (a lossless PNG takes four times longer to encode at 4K and the H.264 output is 4:2:0 either way); `FrameRenderer` takes `screenshot_format='png'` when the frames themselves are the deliverable. It needs `ffmpeg` on the PATH. `limelight-render` adds the walkthrough, chapters and subtitles beside it; pass `--subtitles` to burn the captions into the picture.

## Public API

The root package exports the names a demo author writes, and nothing else:

```python
from limelight import (
    DEMO_MODE_NARRATE,
    DEMO_MODE_PRESENT,
    DEMO_MODE_SILENT,
    Actor,
    Application,
    DemoConfig,
    DemoSession,
    DemoTiming,
    Ledger,
    LedgerMetric,
    LedgerRow,
    Modal,
    Navigator,
    Scene,
    SearchAndSelect,
    SlideButton,
    StaticApplication,
    Theme,
    WorldBase,
    slide_to_end,
    trigger_until_navigation,
    trigger_until_response,
    trigger_until_visible,
)
```

Everything else is plumbing and stays behind its own module. `Presenter`, `presenter_build`, `Camera`, `Overlay` and `Transcript` belong to the presenter; `FrameRenderer`, `DirectorySink` and `VideoSink` belong to the frame pipeline. A demo that reaches for one of them is doing something the facade should be doing instead.

`DemoSession.start` builds the presenter from the config, so a subclass never names one. Attach scenes by overriding `scenes_prepare`, which `__init__` calls once the navigator exists:

```python
class Demo(DemoSession):
    def scenes_prepare(self) -> None:
        self.orders = OrderScene(self)
```

## Pytest plugins

`limelight.pytest_plugin` owns the browser. It sizes the window and the viewport, registers the frame renderer in video mode, and fails a test that logged a JavaScript error. `limelight.django.pytest_plugin` owns the server: a `live_server` that falls back to a sequential WSGI thread when the database is in-memory sqlite, a `page` carrying a navigation timeout, and `DJANGO_ALLOW_ASYNC_UNSAFE`.

Both are tuned by overriding one fixture rather than rewiring the browser fixtures:

| Fixture | Plugin | Default |
|---|---|---|
| `demo_console_error_ignored_fragments` | `limelight.pytest_plugin` | `('TypeError: Failed to fetch',)` |
| `demo_navigation_timeout_ms` | `limelight.django.pytest_plugin` | `60000` |
| `demo_viewport` | `limelight.pytest_plugin` | `{'width': 1920, 'height': 954}` |
| `demo_viewport_video` | `limelight.pytest_plugin` | `{'width': 1920, 'height': 1080}` |
| `demo_window_size` | `limelight.pytest_plugin` | `{'width': 1920, 'height': 1080}` |

Mark a test that expects a console error with `@pytest.mark.console_error_expected('fragment')`.

## Extending

`DjangoApplication` is meant to be subclassed. A multi-tenant project contributes its slug through `url_kwargs_defaults`, which `url()` merges underneath the caller's kwargs, so the caller can still override it:

```python
class CompanyApplication(DjangoApplication):
    def __init__(self, *, live_server, user, company):
        super().__init__(live_server=live_server, user=user)

        self.company = company

    def url_kwargs_defaults(self):
        return {'company_slug': self.company.uuid}

    def with_user(self, user):
        return CompanyApplication(live_server=self.live_server, user=user, company=self.company)
```

`login` is inherited and needs no reimplementation. `with_user` builds `type(self)`, so a subclass that adds no constructor state inherits it too; the override above exists only because `company` has to survive the user switch.

`Modal` and `SearchAndSelect` read their selectors from class attributes, so different markup is a subclass rather than a rewrite:

| Component | Attribute | Default |
|---|---|---|
| `Modal` | `root_selector` | `''`, meaning the `dialog` role |
| `SearchAndSelect` | `choice_selector` | `.list-group-item` |
| `SearchAndSelect` | `dropdown_selector` | `div.list-group` |
| `SearchAndSelect` | `search_placeholder` | `Search...` |
| `SearchAndSelect` | `toggle_selector` | `button.form-control` |

A `Scene` pairs one route with the wait that proves the page arrived:

```python
class OrderScene(Scene):
    route = 'order:page:list'

    def expect_ready(self):
        expect(self._demo.page.get_by_role('grid')).to_be_visible(timeout=15000)
```

## Configuration

| Variable | Description | Default |
|---|---|---|
| `DEMO_MODE` | The presenter and viewport policy, one of `silent`, `narrate`, or `present`. | `silent` |
| `DEMO_SPEED` | The playback speed the demo starts at, one of `normal`, `fast`, `faster`, or `turbo`. | `normal` |
| `DEMO_STEP_MS` | The base hold length in milliseconds. | `4500` |
| `DEMO_SHOTS` | Whether a narrated run writes screenshots. | off |
| `DEMO_VIDEO` | Whether a narrated run renders `video.mp4` frame by frame in a headless browser. | off |
