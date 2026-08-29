from __future__ import annotations

from typing import TYPE_CHECKING

from limelight import ffmpeg
from limelight.artifacts import GIF_FILE_NAME, RENDER_FILE_NAME, VIDEO_FILE_NAME
from limelight.ffmpeg import GIF_FPS_DEFAULT, GIF_WIDTH_DEFAULT

if TYPE_CHECKING:
    from pathlib import Path

    from limelight.ffmpeg import Encoder
    from limelight.transcript import Event


def _source_validate(source: Path) -> None:
    """
    A function that rejects a missing source video.

    :param source: The video the export reads from.
    :raises FileNotFoundError: If the video does not exist.
    """

    if not source.is_file():
        message = f'source video not found: {source}'
        raise FileNotFoundError(message)


class GifExport:
    """An export that converts the recorded video into a GIF."""

    def __init__(
        self,
        encoder: Encoder,
        *,
        fps: int = GIF_FPS_DEFAULT,
        width: int = GIF_WIDTH_DEFAULT,
    ) -> None:
        """
        The constructor for the GifExport class.

        :param encoder: The encoder the conversion runs through.
        :param fps: The frame rate of the GIF.
        :param width: The width the frames are scaled to, with the height kept in proportion.
        :raises ValueError: If the frame rate or the width is not positive.
        """

        if fps < 1:
            message = f'fps must be positive: {fps}'
            raise ValueError(message)

        if width < 1:
            message = f'width must be positive: {width}'
            raise ValueError(message)

        self._encoder = encoder
        self._fps = fps
        self._width = width

    def export(self, events: list[Event], directory: Path) -> Path:
        """
        A method that converts the recorded video into a GIF.

        :param events: The recorded events of the run, which the conversion does not read.
        :param directory: The directory holding the video, and the one the GIF is written to.
        :return: The path the GIF was written to.
        :raises FileNotFoundError: If the recorded video is missing.
        """

        source = directory / VIDEO_FILE_NAME
        destination = directory / GIF_FILE_NAME

        _source_validate(source)

        arguments = ffmpeg.arguments_gif(
            source,
            destination=destination,
            fps=self._fps,
            width=self._width,
        )

        self._encoder.run(arguments)

        return destination


class VideoExport:
    """An export that lays the voiceover and the subtitles over the recorded video."""

    def __init__(
        self,
        encoder: Encoder,
        *,
        audio: Path | None = None,
        subtitles: Path | None = None,
    ) -> None:
        """
        The constructor for the VideoExport class.

        :param encoder: The encoder the render runs through.
        :param audio: The voiceover to mix in, or None for a silent video.
        :param subtitles: The subtitles to burn in, or None to leave the frames alone.
        """

        self._audio = audio
        self._encoder = encoder
        self._subtitles = subtitles

    def export(self, events: list[Event], directory: Path) -> Path:
        """
        A method that renders the final video.

        :param events: The recorded events of the run, which the render does not read.
        :param directory: The directory holding the video, and the one the render is written to.
        :return: The path the render was written to.
        :raises FileNotFoundError: If the recorded video is missing.
        """

        source = directory / VIDEO_FILE_NAME
        destination = directory / RENDER_FILE_NAME

        _source_validate(source)

        arguments = ffmpeg.arguments_mp4(
            source,
            destination=destination,
            audio=self._audio,
            subtitles=self._subtitles,
        )

        self._encoder.run(arguments)

        return destination
