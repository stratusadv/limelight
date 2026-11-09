# limelight

## Overview

The limelight library is a narration layer for Playwright that turns end-to-end tests into demos. A test is written once and runs either as a plain test or with caption cards, a spotlight, and a drawn pointer over the page, so the test that checks a flow in your suite also walks a viewer through it.

There are three modes, and the `DEMO_MODE` variable picks one.

| Mode | Description |
|------|-------------|
| `silent` | The test runs with no overlay and no holds, and it writes no files. This is the default. |
| `narrate` | The overlay draws each step and holds it on screen, and the run records a transcript. |
| `present` | The overlay draws each step and waits for a key press before the next one, and the run records a transcript. |

## Get Started

1. [Install limelight](install.md).
2. [Run your first test](quick-start.md).
3. [Write a demo](writing-a-demo.md).
4. [Browse the API reference](reference/limelight/index.md).
