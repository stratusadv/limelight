from __future__ import annotations

from importlib.resources import files


SCRIPTS = files('limelight').joinpath('scripts')


def script(name: str) -> str:
    """
    A function that reads a bundled browser script by file name.

    :param name: The file name of the script under limelight/scripts.
    :return: The source of the script.
    """

    return SCRIPTS.joinpath(name).read_text(encoding='utf-8')
