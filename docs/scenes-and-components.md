# Scenes And Components

## Overview

A [`Scene`][limelight.Scene] is one screen of the application, so a test reads as a list of steps rather than a list of selectors. A component drives a widget that appears on many screens, and a [`World`][limelight.World] names the objects a demo has seeded.

## Write A Scene

1. Subclass `Scene` and set `route`.
2. Override `expect_ready` to wait for the screen, which is what makes a silent run safe.
3. Add one method per action a viewer would take, built from the helpers below.
4. Open it with `open()`, which calls `goto` and then `expect_ready`.

The `examples/order_search.py` program is a complete scene.

| Helper | Description |
|--------|-------------|
| `_click`, `_fill`, `_select`, `_check`, `_press`, `_hover` | Each helper performs the action through the demo and then holds. |
| `_tab` | The helper clicks a tab by its name. |
| `_teach_focus` | The helper shows the viewer an element. |
| `_teach_click` | The helper shows the viewer an element and then clicks it. |

A `_teach_focus` with a `headline` waits for the element in both modes, and one with a `label` alone does not. A narrated scene action holds for twice the step, so lower `DEMO_STEP_MS` for a demo built from scenes.

## Name The Seeded Objects

1. Subclass `World`, and keep one registry per kind of object.
2. Add a method that seeds an object under a key, and call `_claim` before it, which refuses a key the registry already holds.
3. Add a method that reads the object back with `_require`, which names the key it could not find.

| Helper | Description |
|--------|-------------|
| `_claim` | The helper raises `ValueError` for a key that was seeded already. |
| `_require` | The helper returns the object under a key, and raises `KeyError` for a key that was never seeded. |

## Use A Component

| Component | Description |
|-----------|-------------|
| [`Modal`][limelight.Modal] | The driver opens a dialog from its control, fills it by label, and submits it. |
| [`Dropdown`][limelight.Dropdown] | The driver opens a menu from a trigger and picks one of its actions. |
| [`Confirm`][limelight.Confirm] | The driver accepts the inline prompt between an action and its effect. |
| [`Navigator`][limelight.Navigator] | The driver moves through a navigation menu by the text on its links. |
| [`SearchAndSelect`][limelight.SearchAndSelect] | The driver picks one choice from a dropdown field. |

Subclass a component and override the selectors that differ, such as `trigger_selector`. The `examples/row_menu.py` program does this for one row of a table.

- **One row of many**: Pass a `root` locator to `Dropdown` or `Confirm`, and each lookup stays inside it.
- **`Confirm`**: The `accept` method has no barrier, so wrap it in [one](barriers.md).
- **`SearchAndSelect`**: The driver draws no pointer and records nothing. Call `open` before `choose`.

## Reference

The protected helpers are the contract between these classes and a subclass, so this page documents them in full.

::: limelight.Scene
    options:
        filters: ["!^__"]
        heading_level: 3

::: limelight.World
    options:
        filters: ["!^__"]
        heading_level: 3
