from __future__ import annotations

import pytest

from pathlib import Path
from subprocess import CompletedProcess

from limelight import ffmpeg
from limelight.ffmpeg import Encoder, Ffmpeg

from fakes import FakeEncoder


def test_ffmpeg_satisfies_the_protocol() -> None:
    assert isinstance(Ffmpeg(), Encoder)
    assert isinstance(FakeEncoder(), Encoder)


def test_binary_empty_rejected() -> None:
    with pytest.raises(ValueError, match='binary'):
        Ffmpeg(binary=' ')


def test_run_prefixes_the_located_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def run_stub(
        command: list[str],
        *,
        capture_output: bool,
        check: bool,
    ) -> CompletedProcess[bytes]:
        commands.append(command)

        return CompletedProcess(command, 0, b'', b'')

    monkeypatch.setattr('limelight.ffmpeg.shutil.which', lambda name: f'/usr/bin/{name}')
    monkeypatch.setattr('limelight.ffmpeg.subprocess.run', run_stub)

    Ffmpeg().run(['-i', 'video.mp4', 'render.mp4'])

    assert commands == [[
        '/usr/bin/ffmpeg',
        '-y',
        '-loglevel',
        'error',
        '-i',
        'video.mp4',
        'render.mp4',
    ]]


def test_run_reports_what_ffmpeg_said_about_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def run_stub(
        command: list[str],
        *,
        capture_output: bool,
        check: bool,
    ) -> CompletedProcess[bytes]:
        return CompletedProcess(command, 1, b'', b'video.mp4: No such file or directory\n')

    monkeypatch.setattr('limelight.ffmpeg.shutil.which', lambda name: f'/usr/bin/{name}')
    monkeypatch.setattr('limelight.ffmpeg.subprocess.run', run_stub)

    with pytest.raises(RuntimeError, match='No such file or directory'):
        Ffmpeg().run(['-i', 'video.mp4', 'render.mp4'])


def test_missing_binary_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.ffmpeg.shutil.which', lambda name: None)

    with pytest.raises(RuntimeError, match='ffmpeg not found'):
        Ffmpeg().run([])


def test_mp4_arguments_default() -> None:
    arguments = ffmpeg.arguments_mp4(Path('video.mp4'), destination=Path('render.mp4'))

    assert arguments[:2] == ['-i', 'video.mp4']
    assert arguments[-1] == 'render.mp4'
    assert '-vf' not in arguments


def test_mp4_arguments_burn_subtitles() -> None:
    arguments = ffmpeg.arguments_mp4(
        Path('video.mp4'),
        destination=Path('render.mp4'),
        subtitles=Path('subtitles.vtt'),
    )

    assert '-vf' in arguments
    assert 'subtitles=subtitles.vtt' in arguments


def test_mp4_arguments_subtitles_path_escaped() -> None:
    arguments = ffmpeg.arguments_mp4(
        Path('video.mp4'),
        destination=Path('render.mp4'),
        subtitles=Path("sub'ti:tles.vtt"),
    )

    filter_index = arguments.index('-vf')

    assert arguments[filter_index + 1] == "subtitles=sub\\'ti\\:tles.vtt"


def test_mp4_arguments_audio_track_mapped() -> None:
    arguments = ffmpeg.arguments_mp4(
        Path('video.mp4'),
        destination=Path('render.mp4'),
        audio=Path('voiceover.wav'),
    )

    assert arguments[:4] == ['-i', 'video.mp4', '-i', 'voiceover.wav']
    map_index = arguments.index('-map')

    assert arguments[map_index:map_index + 4] == ['-map', '0:v:0', '-map', '1:a:0']
    assert '-c:a' in arguments
    assert '-shortest' in arguments


def test_gif_arguments_filter_graph() -> None:
    arguments = ffmpeg.arguments_gif(
        Path('video.mp4'),
        destination=Path('demo.gif'),
        fps=10,
        width=640,
    )

    assert arguments[:2] == ['-i', 'video.mp4']
    assert 'fps=10,scale=640:-1:flags=lanczos' in arguments[3]
    assert arguments[-1] == 'demo.gif'


def test_gif_arguments_fps_rejected() -> None:
    with pytest.raises(ValueError, match='fps'):
        ffmpeg.arguments_gif(Path('video.mp4'), destination=Path('demo.gif'), fps=0)


def test_gif_arguments_width_rejected() -> None:
    with pytest.raises(ValueError, match='width'):
        ffmpeg.arguments_gif(Path('video.mp4'), destination=Path('demo.gif'), width=0)


def test_frames_arguments_pipe_images_into_h264() -> None:
    arguments = ffmpeg.arguments_frames(Path('video.mp4'), fps=60)

    assert arguments[:6] == ['-f', 'image2pipe', '-framerate', '60', '-i', '-']
    assert '-crf' in arguments
    assert arguments[arguments.index('-crf') + 1] == '14'
    assert arguments[-1] == 'video.mp4'


def test_frames_arguments_fps_rejected() -> None:
    with pytest.raises(ValueError, match='fps'):
        ffmpeg.arguments_frames(Path('video.mp4'), fps=0)


def test_frames_arguments_crf_rejected() -> None:
    with pytest.raises(ValueError, match='crf'):
        ffmpeg.arguments_frames(Path('video.mp4'), fps=60, crf=99)


def test_voiceover_arguments_delay_each_cue_then_mix() -> None:
    cues = [
        (0, Path('cue-00.wav')),
        (1500, Path('cue-01.wav')),
    ]

    arguments = ffmpeg.arguments_voiceover(cues, Path('voiceover.wav'))

    filter_graph = arguments[arguments.index('-filter_complex') + 1]

    assert arguments[:4] == ['-i', 'cue-00.wav', '-i', 'cue-01.wav']
    assert '[0]adelay=0|0[voice0]' in filter_graph
    assert '[1]adelay=1500|1500[voice1]' in filter_graph
    assert 'amix=inputs=2:normalize=0[voiceover]' in filter_graph
    assert arguments[-1] == 'voiceover.wav'


def test_voiceover_arguments_reject_empty_cues() -> None:
    with pytest.raises(ValueError, match='cues'):
        ffmpeg.arguments_voiceover([], Path('voiceover.wav'))


def test_voiceover_arguments_reject_negative_offset() -> None:
    cues = [(-1, Path('cue-00.wav'))]

    with pytest.raises(ValueError, match='offset_ms'):
        ffmpeg.arguments_voiceover(cues, Path('voiceover.wav'))


def test_frame_arguments_refuse_a_negative_crf(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='crf must be non-negative: -1'):
        ffmpeg.arguments_frames(tmp_path / 'video.mp4', fps=60, crf=-1)


def test_frame_arguments_refuse_a_crf_beyond_the_ceiling(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='crf must not exceed'):
        ffmpeg.arguments_frames(tmp_path / 'video.mp4', fps=60, crf=52)


def test_pipe_opens_a_process_with_a_pipe_for_frames() -> None:
    process = Ffmpeg(binary='cat').pipe(['-'])

    try:
        assert process.stdin is not None
    finally:
        if process.stdin is not None:
            process.stdin.close()

        process.wait(timeout=5)
