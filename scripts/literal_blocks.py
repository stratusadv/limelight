from __future__ import annotations

import re
import textwrap

from typing import TYPE_CHECKING
from typing_extensions import override

from griffe import Extension

if TYPE_CHECKING:
    from griffe import Object


LITERAL_BLOCK_PATTERN = re.compile(r'^::\n((?:\n| .*\n?)+)', re.MULTILINE)
LITERAL_MARKER_PATTERN = re.compile(r'::$', re.MULTILINE)


def literal_block_fenced(match: re.Match[str]) -> str:
    code = textwrap.dedent(match.group(1)).strip('\n')
    return f'```python\n{code}\n```\n\n'


class LiteralBlocks(Extension):
    @override
    def on_instance(self, *, obj: Object, **_kwargs: object) -> None:
        docstring = obj.docstring

        if docstring is None:
            return

        value = LITERAL_BLOCK_PATTERN.sub(literal_block_fenced, docstring.value)

        if LITERAL_MARKER_PATTERN.search(value):
            message = f'{obj.path} has a literal block that is not opened by a lone "::" line'
            raise ValueError(message)

        docstring.value = value
