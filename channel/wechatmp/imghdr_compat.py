"""
Minimal imghdr replacement for Python 3.13+ (stdlib imghdr removed).
Detects common formats used in wechat uploads.
"""
from __future__ import annotations

import os
from typing import Optional, Union


def what(file: Union[str, bytes, os.PathLike, object], h: Optional[bytes] = None) -> Optional[str]:
    """Return image type string or None."""
    if h is None:
        if isinstance(file, (str, bytes, os.PathLike)):
            with open(file, "rb") as f:
                h = f.read(32)
        else:
            pos = file.tell()
            h = file.read(32)
            file.seek(pos)

    if h.startswith(b"\xff\xd8"):
        return "jpeg"
    if h.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if h[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if h.startswith(b"BM"):
        return "bmp"
    if h.startswith(b"RIFF") and h[8:12] == b"WEBP":
        return "webp"
    if h.startswith(b"II*\x00") or h.startswith(b"MM\x00*"):
        return "tiff"
    return None


__all__ = ["what"]
