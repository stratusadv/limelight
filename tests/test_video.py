from __future__ import annotations

import pytest

from pathlib import Path

from limelight.video import (
    ffmpeg_arguments_frames,
    ffmpeg_arguments_gif,
    ffmpeg_arguments_mp4,
    ffprobe_arguments_duration,
    trim_lead_ms_from_epochs,
)


def test_mp4_arguments_default() -> None:
    arguments = ffmpeg_arguments_mp4(Path('demo.webm'), Path('demo.mp4'))

    assert arguments[:2] == ['-i', 'demo.webm']
    assert arguments[-1] == 'demo.mp4'
    assert '-ss' not in arguments
    assert '-vf' not in arguments


def test_mp4_arguments_trim_before_input() -> None:
    arguments = ffmpeg_arguments_mp4(Path('demo.webm'), Path('demo.mp4'), trim_lead_ms=1500)

    assert arguments[:4] == ['-ss', '1.500', '-i', 'demo.webm']


def test_mp4_arguments_burn_subtitles() -> None:
    arguments = ffmpeg_arguments_mp4(
        Path('demo.webm'),
        Path('demo.mp4'),
        subtitles=Path('subtitles.vtt'),
    )

    assert '-vf' in arguments
    assert 'subtitles=subtitles.vtt' in arguments


def test_mp4_arguments_negative_trim_rejected() -> None:
    with pytest.raises(ValueError, match='trim_lead_ms'):
        ffmpeg_arguments_mp4(Path('demo.webm'), Path('demo.mp4'), trim_lead_ms=-1)


def test_mp4_arguments_subtitles_path_escaped() -> None:
    arguments = ffmpeg_arguments_mp4(
        Path('demo.webm'),
        Path('demo.mp4'),
        subtitles=Path("sub'ti:tles.vtt"),
    )

    filter_index = arguments.index('-vf')

    assert arguments[filter_index + 1] == "subtitles=sub\\'ti\\:tles.vtt"


def test_mp4_arguments_audio_track_mapped() -> None:
    arguments = ffmpeg_arguments_mp4(
        Path('demo.webm'),
        Path('demo.mp4'),
        audio=Path('voiceover.wav'),
    )

    assert arguments[:4] == ['-i', 'demo.webm', '-i', 'voiceover.wav']
    assert arguments[arguments.index('-map'):arguments.index('-map') + 4] == ['-map', '0:v:0', '-map', '1:a:0']
    assert '-c:a' in arguments
    assert '-shortest' in arguments


def test_trim_lead_from_epochs_is_the_difference() -> None:
    trim_ms = trim_lead_ms_from_epochs(
        session_started_at_epoch_ms=5000,
        video_started_at_epoch_ms=3000,
    )

    assert trim_ms == 2000


def test_trim_lead_from_epochs_never_negative() -> None:
    trim_ms = trim_lead_ms_from_epochs(
        session_started_at_epoch_ms=3000,
        video_started_at_epoch_ms=5000,
    )

    assert trim_ms == 0


def test_ffprobe_arguments_target_the_source() -> None:
    arguments = ffprobe_arguments_duration(Path('demo.webm'))

    assert arguments[-1] == 'demo.webm'
    assert 'format=duration' in arguments


def test_gif_arguments_filter_graph() -> None:
    arguments = ffmpeg_arguments_gif(Path('demo.webm'), Path('demo.gif'), fps=10, width=640)

    assert arguments[:2] == ['-i', 'demo.webm']
    assert 'fps=10,scale=640:-1:flags=lanczos' in arguments[3]
    assert arguments[-1] == 'demo.gif'


def test_gif_arguments_fps_rejected() -> None:
    with pytest.raises(ValueError, match='fps'):
        ffmpeg_arguments_gif(Path('demo.webm'), Path('demo.gif'), fps=0)


def test_gif_arguments_width_rejected() -> None:
    with pytest.raises(ValueError, match='width'):
        ffmpeg_arguments_gif(Path('demo.webm'), Path('demo.gif'), width=0)


def test_frames_arguments_pipe_pngs_into_h264() -> None:
    arguments = ffmpeg_arguments_frames(Path('video.mp4'), fps=60)

    assert arguments[:6] == ['-f', 'image2pipe', '-framerate', '60', '-i', '-']
    assert '-crf' in arguments
    assert arguments[arguments.index('-crf') + 1] == '14'
    assert arguments[-1] == 'video.mp4'


def test_frames_arguments_fps_rejected() -> None:
    with pytest.raises(ValueError, match='fps'):
        ffmpeg_arguments_frames(Path('video.mp4'), fps=0)


def test_frames_arguments_crf_rejected() -> None:
    with pytest.raises(ValueError, match='crf'):
        ffmpeg_arguments_frames(Path('video.mp4'), fps=60, crf=99)
