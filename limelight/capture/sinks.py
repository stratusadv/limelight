from __future__ import annotations

import subprocess

from typing import TYPE_CHECKING, Protocol

from limelight import ffmpeg
from limelight.ffmpeg import FRAMES_CRF_DEFAULT, FRAMES_PRESET_DEFAULT

if TYPE_CHECKING:
    from pathlib import Path
    from subprocess import Popen

    from limelight.ffmpeg import Encoder


FRAME_FPS_DEFAULT = 60

STOP_TIMEOUT_SECONDS = 120


class FrameSink(Protocol):
    """
    A protocol for the destination a render writes its frames to.

    This protocol covers the lifecycle of a destination: it is opened once, written
    to once per frame in order, and closed when the run ends.
    """

    def close(self) -> None:
        """A method that finishes the destination and releases what it holds."""

        ...

    def open(self) -> None:
        """A method that prepares the destination for the first frame."""

        ...

    def write(self, index: int, image: bytes) -> None:
        """
        A method that writes one frame.

        :param index: The position of the frame in the timeline, counted from zero.
        :param image: The encoded image for the frame.
        """

        ...


class DirectorySink:
    """
    A frame destination that writes each frame as its own image file.

    This class is the sink for a run that inspects individual frames, so the names
    are zero-padded and sort in timeline order.
    """

    def __init__(self, directory: Path, *, suffix: str = '.png') -> None:
        """
        The constructor for the DirectorySink class.

        :param directory: The directory the frames are written to.
        :param suffix: The file extension for each frame, including the dot.
        :raises ValueError: If the suffix does not start with a dot.
        """

        if not suffix.startswith('.'):
            message = f'suffix must start with a dot: {suffix}'
            raise ValueError(message)

        self._directory = directory
        self._suffix = suffix

    def close(self) -> None:
        """
        A method that finishes the directory.

        There is nothing to release because each frame is written and closed on its
        own, so the method exists only to satisfy the sink protocol.
        """

    def open(self) -> None:
        """A method that creates the directory the frames are written to."""

        self._directory.mkdir(parents=True, exist_ok=True)

    def write(self, index: int, image: bytes) -> None:
        """
        A method that writes one frame as an image file.

        :param index: The position of the frame in the timeline, counted from zero.
        :param image: The encoded image for the frame.
        """

        (self._directory / f'frame-{index:06d}{self._suffix}').write_bytes(image)


class VideoSink:
    """
    A frame destination that pipes each frame into an encoder.

    This class holds the encoder process open across the run, so the frames are
    compressed as they arrive rather than accumulating on disk.
    """

    def __init__(
        self,
        destination: Path,
        encoder: Encoder,
        *,
        crf: int = FRAMES_CRF_DEFAULT,
        fps: int = FRAME_FPS_DEFAULT,
        preset: str = FRAMES_PRESET_DEFAULT,
    ) -> None:
        """
        The constructor for the VideoSink class.

        :param destination: The file the video is written to.
        :param encoder: The encoder the frames are piped into.
        :param crf: The constant rate factor, where a lower number is higher quality.
        :param fps: The frame rate the frames are played back at.
        :param preset: The encoder preset, trading speed against file size.
        """

        self._crf = crf
        self._destination = destination
        self._encoder = encoder
        self._fps = fps
        self._preset = preset
        self._process: Popen[bytes] | None = None

    def close(self) -> None:
        """
        A method that closes the pipe and waits for the encoder to finish.

        The process handle is cleared before the wait, so a close that raises cannot be
        retried against an encoder that has already been reaped. An encoder that never
        finishes is killed rather than left behind, because the pipe is already closed
        and a process still holding the output file would outlive the run.

        :raises RuntimeError: If the encoder exits with a non-zero status, or has to be killed.
        """

        process = self._process

        if process is None:
            return

        self._process = None

        if process.stdin is not None:
            process.stdin.close()

        try:
            return_code = process.wait(timeout=STOP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

            message = (
                f'ffmpeg did not finish within {STOP_TIMEOUT_SECONDS}s'
                f' while writing {self._destination}; it was killed'
            )

            raise RuntimeError(message) from None

        if return_code != 0:
            message = f'ffmpeg exited with status {return_code} while writing {self._destination}'
            raise RuntimeError(message)

    def open(self) -> None:
        """A method that starts the encoder reading from the pipe."""

        self._destination.parent.mkdir(parents=True, exist_ok=True)

        arguments = ffmpeg.arguments_frames(
            self._destination,
            fps=self._fps,
            crf=self._crf,
            preset=self._preset,
        )

        self._process = self._encoder.pipe(arguments)

    def write(self, index: int, image: bytes) -> None:
        """
        A method that writes one frame into the encoder.

        :param index: The position of the frame in the timeline, counted from zero.
        :param image: The encoded image for the frame.
        :raises RuntimeError: If the sink is not open, or the encoder has no pipe.
        """

        process = self._process

        if process is None:
            message = f'the video sink for {self._destination} is not open'
            raise RuntimeError(message)

        if process.stdin is None:
            message = f'the video sink for {self._destination} has no pipe into the encoder'
            raise RuntimeError(message)

        process.stdin.write(image)
