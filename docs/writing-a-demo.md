# Writing A Demo

## Overview

A demo is a test that also reads as a script. Each step says something to the viewer or does something to the page, through the [`Demo`][limelight.Demo] object.

## Write The Steps

1. Open a page with [`goto`][limelight.Demo.goto]. The call signs the user in first, so keep the `login` callable of a `StaticApplication` safe to repeat.
2. Say something with [`title`][limelight.Demo.title] or [`narrate`][limelight.Demo.narrate].
3. Point at something with [`spotlight`][limelight.Demo.spotlight], or with [`reveal`][limelight.Demo.reveal] to wait for the element first.
4. Act with `click`, `fill`, `select`, `check`, `uncheck`, `hover`, `press`, or `slide`.
5. [Prove the step landed](#prove-it-landed).

Call each action on the `Demo`, not on the locator. A direct call passes in a silent run, but in a narrated run the click lands with the pointer somewhere else on screen, and the step is missing from the transcript. The [`Demo`][limelight.Demo] reference lists each method.

!!! warning "Typed Values Are Recorded"
    A narrated `fill` records its value in the transcript and the walkthrough, and a `password` input records `********` instead. A failed test's trace holds what the test typed, including a password, so pass `--tracing=off` for a demo that signs in with a real credential.

## Hold The Pace

A narrated action already holds for one step after it lands, so a demo needs few holds of its own.

| Call | Silent | Narrated |
|------|--------|----------|
| `demo.pause()` | The call returns at once. | The call holds for one step. |
| `demo.pause(800)` | The call returns at once. | The call holds for 800 milliseconds at the current speed. |
| `demo.wait(800)` | The call waits 800 milliseconds. | The call waits 800 milliseconds at any speed. |

Use `pause` for pacing, and `wait` only where the page needs the time. The `title` and `narrate` cards take a `hold_ms` argument for one long or short hold.

## Prove It Landed

A silent run has no holds, so the next step can arrive before the page has answered. Follow each step that changes the page with something that waits for the change.

| Effect | Wait |
|--------|------|
| An element appears. | Use `expect` from Playwright, or `reveal` to show it as well. |
| A click loads a new page. | Use [`follow`][limelight.Demo.follow]. |
| A click sends a request. | Use a [barrier](barriers.md). |
| A condition outside the page changes. | Use [`wait_until`][limelight.Demo.wait_until]. |

Run the silent mode often while you write, because a missing wait fails there first.

## Errors

A wrong argument raises `ValueError` or `TypeError`, and an element that never appears raises `AssertionError`, as a failed Playwright `expect` does. The operating failures derive from [`Error`][limelight.Error].

| Error | Cause |
|-------|-------|
| [`BarrierError`][limelight.BarrierError] | A barrier never saw its effect. |
| [`OverlayError`][limelight.OverlayError] | The overlay failed in the page. |
| [`RenderError`][limelight.RenderError] | A video render failed. |

## Lifecycle

The page belongs to the test, so a `Demo` never closes it, and a demo writes only under `.demos/<name>/`. The overlay lives as long as its document, so limelight installs a new one after each navigation. A `Demo` stays on the thread that built it, because the sync Playwright API is bound to the thread that started it.

A demo builds the narrator its mode calls for: the overlay for a narrated run, or a silent one otherwise. Pass your own [`Narrator`][limelight.Narrator] as `narrator` to replace it.
