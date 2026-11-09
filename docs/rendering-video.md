# Rendering Video

## Overview

The `DEMO_VIDEO` variable makes a narrated run write `video.mp4`, frame by frame in a headless browser. The `limelight-render` command turns the run into its deliverables.

## Render A Demo

1. Render one demo. Select it with `-k`, because a test that builds no `Demo` fails in a video run.

    ```sh
    DEMO_MODE=narrate DEMO_VIDEO=1 pytest -k order_approval_demo
    ```

2. Make the deliverables.

    ```sh
    limelight-render .demos/order-approval --title "Order Approval" --subtitles --gif
    ```

A render needs the `narrate` mode, the pytest plugin, Chromium, and `ffmpeg` on your `PATH`.

## How It Works

The `DEMO_VIDEO` variable does not record the screen. The browser runs headless under Chrome's begin-frame control, and the renderer asks the compositor for each frame at a timestamp it chooses. The page runs on virtual time that moves one interval per frame, so each hold, glide, and transition is measured in frames rather than wall time, and a slow machine lengthens the render instead of dropping frames from it.

## Quality

The `DEMO_VIDEO_QUALITY` variable picks one of these.

| Quality | Output | Use |
|---------|--------|-----|
| `low` | The frames are 1920x1080 at 24 fps. | The level suits a pacing pass, where only the timing is read back. |
| `medium` | The frames are 1920x1080 at 30 fps. | The default level is sharp enough to read the interface. |
| `high` | The frames are 3840x2160 at 60 fps. | The level suits a released demo, which is rendered once. |

A `high` render carries eight times the pixels per second of `medium`, so measure it on your own page before a long take.

## The Command

The `limelight-render` command takes the directory of a demo and writes its files there. The command always writes `chapters.txt` and `walkthrough.md`, and each option adds to them.

| Option | Description |
|--------|-------------|
| `--title TITLE` | The option sets the heading the walkthrough opens with. |
| `--subtitles` | The option writes `subtitles.vtt` and burns it into `render.mp4`. |
| `--audio AUDIO` | The option mixes an audio file into `render.mp4`. |
| `--gif` | The option converts `video.mp4` to `video.gif`. |

## Add A Voiceover

The library generates no speech, so bring a synthesizer or recorded clips.

1. Run the demo with `DEMO_MODE=narrate DEMO_SPEED=turbo` to record what it says.
2. Read the lines with [`voiceover_cues`][limelight.export.voiceover_cues], and speak each one.
3. Write `holds.json`, which maps the text of each line to its length in whole milliseconds.
4. Render with `DEMO_HOLDS=holds.json` added to the command above.
5. Mix the clips with [`VoiceoverExport`][limelight.export.VoiceoverExport], and pass the result to `limelight-render` with `--audio`.

A line that is not in the file falls back to the step, so regenerate the file when the script changes. The `examples/voiceover_holds.py` program measures the holds this way.
