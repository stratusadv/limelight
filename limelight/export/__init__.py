from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from limelight.transcript import Event


@runtime_checkable
class Export(Protocol):
    """A protocol for one artifact rendered from a recorded transcript."""

    def export(self, events: list[Event], directory: Path) -> Path:
        """
        A method that renders the artifact into a directory.

        :param events: The recorded events of the run.
        :param directory: The directory the artifact is written to.
        :return: The path the artifact was written to.
        """

        ...


@dataclass(frozen=True)
class TextExport:
    """
    An export that renders the events into one text file.

    This class covers every artifact that is a string on disk, so a new one needs
    only a file name and the function that renders it.
    """

    file_name: str
    render: Callable[[list[Event]], str]

    def __post_init__(self) -> None:
        """
        A method that rejects an export with no file name.

        :raises ValueError: If the file name is empty.
        """

        if not self.file_name:
            message = 'file_name must not be empty'
            raise ValueError(message)

    def export(self, events: list[Event], directory: Path) -> Path:
        """
        A method that renders the events and writes them to the file.

        :param events: The recorded events of the run.
        :param directory: The directory the file is written to.
        :return: The path the file was written to.
        """

        path = directory / self.file_name

        path.write_text(self.render(events), encoding='utf-8')

        return path


def exports_run(events: list[Event], directory: Path, exports: Sequence[Export]) -> list[Path]:
    """
    A function that runs a sequence of exports over one transcript.

    :param events: The recorded events of the run.
    :param directory: The directory the artifacts are written to.
    :param exports: The artifacts to render, in the order they are run.
    :return: The path of each artifact, in the order it was rendered.
    """

    directory.mkdir(parents=True, exist_ok=True)

    return [export.export(events, directory) for export in exports]
