# Quick Start

## Overview

This page takes one test through a silent run, a narrated run, and a render. The test answers its own requests, so it needs no server.

## Run A Test

1. Add the plugin to the root `conftest.py`.

    ```python title="conftest.py"
    pytest_plugins = ['limelight.pytest_plugin']
    ```

2. Copy this test into your project.

    ```python title="examples/test_order_approval.py"
    --8<-- "examples/test_order_approval.py"
    ```

3. Run it silent. A silent run has no holds and writes nothing.

    ```sh
    pytest -k order_approval_demo
    ```

4. Run it narrated. The `--headed` flag opens the window, because `DEMO_MODE` does not open one on its own.

    ```sh
    DEMO_MODE=narrate pytest -k order_approval_demo --headed
    ```

5. Render a video. The render needs `ffmpeg`.

    ```sh
    DEMO_MODE=narrate DEMO_VIDEO=1 pytest -k order_approval_demo
    limelight-render .demos/order-approval --title "Order Approval" --subtitles
    ```

A narrated run writes to `.demos/order-approval/`, relative to the directory you ran it from. The `name` argument of the [`Demo`][limelight.Demo] names that directory.

The plugin fails a test whose page logs a `console.error` or throws an uncaught exception. The [Configuration](configuration.md#console-errors) page shows how to allow one.
