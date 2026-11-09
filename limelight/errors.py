from __future__ import annotations


class Error(Exception):
    pass


class BarrierError(Error):
    pass


class OverlayError(Error):
    pass


class RenderError(Error):
    pass
