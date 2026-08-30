<p align="center">
    <picture>
        <source media="(prefers-color-scheme: dark)" srcset="assets/png/limelight-wordmark-1567x404.png">
        <source media="(prefers-color-scheme: light)" srcset="assets/png/limelight-wordmark-1567x404.png">
        <img alt="limelight" src="assets/png/limelight-wordmark-1567x404.png" width="320">
    </picture>
</p>

&nbsp;

<p align="center">
    A narration layer for Playwright that turns end-to-end tests into demos.
</p>

## Overview

A limelight test is written once and runs in two modes. The silent mode is a plain headless e2e test, where each narration call is a no-op. The narrated mode runs the same test headed with an overlay of caption cards, spotlights, an animated cursor, screenshots, and video. A test body never branches on the mode. The `Demo` facade is the whole API.

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
from limelight import Demo
from limelight.django import DjangoApplication


def test_order_approval_demo(page, live_server, admin_user):
    application = DjangoApplication(live_server=live_server)
    demo = Demo(page, application, name='order-approval', user=admin_user)

    demo.goto('home:dashboard')
    demo.title('Order Approval')
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
DEMO_MODE=narrate DEMO_VIDEO=1 pytest -k order_approval_demo
limelight-render .demos/order-approval --title "Order Approval"
```

`DEMO_VIDEO` does not record the screen. The browser runs headless under Chrome's begin-frame control, and limelight advances the compositor one frame at a time, screenshotting each one and piping it into ffmpeg. Every hold, glide and transition is measured in frames rather than wall time, so `video.mp4` comes out with one distinct frame per interval no matter how slow the machine is. It needs `ffmpeg` on the PATH.

`DEMO_VIDEO_QUALITY` picks what that costs:

| Quality | Output | Use |
|---|---|---|
| `low` | 1920x1080, 24 fps | Iterating on pacing, where only the timing is being read back. |
| `medium` | 1920x1080, 30 fps | The default. Sharp enough to read the interface, and the cheapest of the three to produce. |
| `high` | 3840x2160, 60 fps | A released demo, where the render is done once and the file size does not matter. |

The cost is carried by the frame count and the pixel count together. Each frame is one
round trip to the compositor, so `high` asks for twice as many as `medium`, and each of
those frames covers four times the pixels at a device scale factor of 2. A `high` render
therefore takes around eight times the work of a `medium` one and leaves a file several
times larger.

## Page objects

A `Scene` is one screen of the application. The subclass names the route, proves the screen
has loaded, and offers one method per action a viewer would take, so a test reads as a list
of steps rather than a list of selectors.

```python
from limelight import Scene
from playwright.sync_api import expect


class OrderScene(Scene):
    route = 'sales:order:page:list'

    def expect_ready(self) -> None:
        expect(self.search_field).to_be_visible()

    @property
    def search_field(self):
        return self.demo.page.get_by_placeholder('Search orders')

    def search(self, text: str) -> None:
        self._teach_focus(self.search_field, headline='Search the orders', label='Search')

        self._fill(self.search_field, text)
```

The protected helpers are the vocabulary a scene is written in. `_click`, `_fill`, `_select`,
`_check`, `_press`, and `_hover` each perform the action through the demo and then hold, so a
narrated run shows the drawn pointer land before the next step begins and a silent run pays
nothing for the hold. `_tab` opens a tab by its name. `_teach_focus` waits for an element,
narrates it, and spotlights it in one step, which makes it a barrier in silent mode as well
as a caption in a narrated one; `_teach_click` does the same and then clicks.

A scene never calls a Playwright locator method directly, because a bare click moves the real
mouse without moving the drawn one, and the click lands with the pointer somewhere else on
screen.

## Components

A widget that appears on many screens is a component rather than a method on each scene. Each
one carries its selectors as class attributes, so markup that differs is a subclass overriding
a selector rather than a fork of the driver.

| Component | What it drives |
|---|---|
| `Modal` | A dialog: opening it from its control, filling it by label, and submitting it. |
| `Dropdown` | A menu that opens from a trigger and lists its actions. |
| `Confirm` | The inline prompt that stands between an action and its effect. |
| `SearchAndSelect` | A dropdown field that filters a long list and picks one choice. |
| `Navigator` | A navigation menu, addressed by the text a viewer reads on its links. |

```python
from limelight import Confirm, Dropdown


class RowMenu(Dropdown):
    trigger_selector = '.bi-three-dots-vertical'


class DestructiveConfirm(Confirm):
    button_selector = '.btn-danger'


RowMenu(demo, row).choose('Delete')
DestructiveConfirm(demo).accept('Delete')
```

`Dropdown` scopes its trigger, its menu, and its actions to the region it is given, so a page
holding one menu per row can address a single row without a menu left open elsewhere
answering for it. `Confirm` leaves its click unbarriered on purpose, because a prompt sits in
front of anything from a form post to a background write, so the caller wraps the accept in
the barrier that proves its own effect landed.

## Barriers

Silent mode removes every time cushion, so correctness rests on retrying barriers rather than
on holds. `trigger_until_navigation`, `trigger_until_response`, and `trigger_until_visible`
each repeat a trigger until its effect arrives, because a click can land before the handler
that listens for it is bound and a lost click leaves the page where it was with no error to
catch. `trigger_until_response` matches by a substring of the response URL, by the method its
request was made with, or by a predicate, exactly one at a time.

```python
trigger_until_response(page, lambda: demo.click(submit), method='POST')
```

`Demo.follow` is the barriered form of clicking a link: it spotlights the link, clicks it with
the drawn pointer, and waits out the page it leads to.

## Configuration

| Variable | Description | Default |
|---|---|---|
| `DEMO_MODE` | The narration and viewport policy, one of `silent`, `narrate`, or `present`. | `silent` |
| `DEMO_SPEED` | The playback speed the demo starts at, one of `normal`, `fast`, `faster`, or `turbo`. | `normal` |
| `DEMO_STEP_MS` | The base hold length in milliseconds. | `4500` |
| `DEMO_SHOTS` | Whether a narrated run writes screenshots. | off |
| `DEMO_VIDEO` | Whether a narrated run renders `video.mp4` frame by frame in a headless browser. | off |
| `DEMO_VIDEO_QUALITY` | The resolution, frame rate and encoder settings, one of `low`, `medium`, or `high`. | `medium` |
| `DEMO_CURSOR_HIDDEN` | Whether the drawn pointer is left off a narrated run. | off |
