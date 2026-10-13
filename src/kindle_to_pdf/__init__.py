"""Kindle Library Sync package.

Legacy macOS converter is imported lazily so pure domain/metadata modules can
run and be tested on Linux without Quartz, Pillow or OCR dependencies.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .converter import KindleToPDF

__all__ = ["KindleToPDF"]


def __getattr__(name: str):
    if name == "KindleToPDF":
        from .converter import KindleToPDF

        return KindleToPDF
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
