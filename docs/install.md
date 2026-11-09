# Install

## Overview

The package is published on PyPI as `playwright-limelight`, and it needs Python 3.11 or later. The `pytest` extra installs `pytest` and `pytest-playwright` for the plugin, and the `django` extra installs Django and `pytest-django` for the Django adapter.

## Install It

1. Install the package. Drop `django` for a project that does not use Django.

    ```sh
    pip install "playwright-limelight[django,pytest]"
    ```

2. Install a browser. A silent or narrated run works in Chromium, Firefox, or WebKit, and a render needs Chromium.

    ```sh
    playwright install chromium
    ```

3. Install `ffmpeg` if you plan to render video. The `ffmpeg` binary has to be on your `PATH`.
4. Check the install.

    ```sh
    limelight-render --help
    ```
