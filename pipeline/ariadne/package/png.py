# Written with AI assistance (Claude Code). See AI_USE.md.
"""A minimal PNG writer (zlib only): 8-bit gray, RGB and RGBA, and 16-bit gray heightmaps."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np


def write_png(path: Path, img: np.ndarray, level: int = 9) -> None:
    a = np.asarray(img)
    if a.dtype == np.uint16:
        if a.ndim != 2:
            raise ValueError("16-bit PNGs are gray only")
        depth, color, rows = 16, 0, a.astype(">u2")
    else:
        a = a.astype(np.uint8)
        depth = 8
        if a.ndim == 2:
            color = 0
        elif a.ndim == 3 and a.shape[2] in (3, 4):
            color = 2 if a.shape[2] == 3 else 6
        else:
            raise ValueError("need gray, RGB or RGBA")
        rows = a
    h, w = rows.shape[:2]
    flat = np.ascontiguousarray(rows).reshape(h, -1)
    raw = b"".join(b"\x00" + flat[i].tobytes() for i in range(h))

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    Path(path).write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, depth, color, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, level))
        + chunk(b"IEND", b"")
    )
