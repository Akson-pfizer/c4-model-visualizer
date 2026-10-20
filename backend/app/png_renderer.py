"""Zero-dependency pure-Python PNG renderer for Confluence architecture diagrams.

Generates crisp, high-resolution RGBA PNG files (`1280x430`) directly using only
the Python standard library (`zlib`, `struct`, `math`) so `c4-doc-agent` works in
any container or sandboxed environment without native C/Cairo dependencies.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Any

# Minimal 5x7 bitmap font for uppercase, lowercase, digits, and punctuation
FONT_5X7: dict[str, tuple[int, ...]] = {
    " ": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    '"': (0x0A, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00),
    "#": (0x0A, 0x1F, 0x0A, 0x0A, 0x1F, 0x0A, 0x00),
    "%": (0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "'": (0x04, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "*": (0x00, 0x04, 0x15, 0x0E, 0x15, 0x04, 0x00),
    "+": (0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00),
    ",": (0x00, 0x00, 0x00, 0x00, 0x04, 0x04, 0x08),
    "-": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    "/": (0x01, 0x02, 0x04, 0x04, 0x08, 0x10, 0x00),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x06, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    ":": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    ";": (0x00, 0x04, 0x00, 0x00, 0x04, 0x04, 0x08),
    "<": (0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02),
    "=": (0x00, 0x00, 0x1F, 0x00, 0x1F, 0x00, 0x00),
    ">": (0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04),
    "@": (0x0E, 0x11, 0x17, 0x15, 0x17, 0x10, 0x0E),
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "[": (0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E),
    "]": (0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E),
    "_": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F),
    "|": (0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 6:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 29, 78, 216


class PurePNGCanvas:
    def __init__(self, width: int, height: int, bg_hex: str = "#f8fafc") -> None:
        self.width = width
        self.height = height
        r, g, b = _hex_to_rgb(bg_hex)
        self.buf = bytearray([r, g, b] * (width * height))

    def set_px(self, x: int, y: int, rgb: tuple[int, int, int]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            idx = (y * self.width + x) * 3
            self.buf[idx] = rgb[0]
            self.buf[idx + 1] = rgb[1]
            self.buf[idx + 2] = rgb[2]

    def fill_rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        fill_hex: str,
        border_hex: str | None = None,
    ) -> None:
        rgb = _hex_to_rgb(fill_hex)
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.width, int(x + w))
        y1 = min(self.height, int(y + h))
        row_bytes = bytes(rgb) * (x1 - x0)
        for py in range(y0, y1):
            start = (py * self.width + x0) * 3
            self.buf[start : start + (x1 - x0) * 3] = row_bytes

        if border_hex:
            b_rgb = _hex_to_rgb(border_hex)
            for px in range(x0, x1):
                self.set_px(px, y0, b_rgb)
                self.set_px(px, y0 + 1, b_rgb)
                self.set_px(px, y1 - 1, b_rgb)
                self.set_px(px, y1 - 2, b_rgb)
            for py in range(y0, y1):
                self.set_px(x0, py, b_rgb)
                self.set_px(x0 + 1, py, b_rgb)
                self.set_px(x1 - 1, py, b_rgb)
                self.set_px(x1 - 2, py, b_rgb)

    def draw_line(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        color_hex: str = "#64748b",
        thickness: int = 2,
    ) -> None:
        rgb = _hex_to_rgb(color_hex)
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        cx, cy = x0, y0
        while True:
            for ox in range(-thickness // 2, thickness // 2 + 1):
                for oy in range(-thickness // 2, thickness // 2 + 1):
                    self.set_px(cx + ox, cy + oy, rgb)
            if cx == x1 and cy == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                cx += sx
            if e2 <= dx:
                err += dx
                cy += sy

    def draw_text(
        self,
        text: str,
        x: int,
        y: int,
        color_hex: str = "#ffffff",
        scale: int = 2,
        center_width: int | None = None,
    ) -> None:
        rgb = _hex_to_rgb(color_hex)
        clean = str(text)
        char_w = 6 * scale
        if center_width is not None:
            total_w = len(clean) * char_w
            x = x + max(4, (center_width - total_w) // 2)

        cursor_x = x
        for ch in clean:
            glyph = FONT_5X7.get(ch.upper(), FONT_5X7[" "])
            for row_idx, row_bits in enumerate(glyph):
                for col_idx in range(5):
                    if (row_bits >> (4 - col_idx)) & 1:
                        for sy in range(scale):
                            for sx in range(scale):
                                self.set_px(
                                    cursor_x + col_idx * scale + sx,
                                    y + row_idx * scale + sy,
                                    rgb,
                                )
            cursor_x += char_w

    def save_png(self, path: Path) -> None:
        raw_rows = bytearray()
        stride = self.width * 3
        for y in range(self.height):
            raw_rows.append(0)  # filter type 0 (None)
            start = y * stride
            raw_rows.extend(self.buf[start : start + stride])

        def chunk(chunk_type: bytes, data: bytes) -> bytes:
            crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
            return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

        ihdr = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        compressed = zlib.compress(bytes(raw_rows), level=6)
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", compressed)
            + chunk(b"IEND", b"")
        )
        path.write_bytes(png_bytes)


def render_diagram_png(spec: Any, png_path: Path) -> None:
    width, height = 1280, 430
    canvas = PurePNGCanvas(width, height, bg_hex="#f8fafc")

    # Outer frame & header banner
    canvas.fill_rect(16, 14, width - 32, height - 28, "#ffffff", border_hex="#cbd5e1")
    canvas.fill_rect(16, 14, width - 32, 46, "#0f172a")
    canvas.draw_text(spec.title[:58], 34, 30, color_hex="#ffffff", scale=2)
    canvas.draw_text(
        f"C4 MODELLING - CONFLUENCE ({spec.category.upper()})",
        width - 470,
        30,
        color_hex="#93c5fd",
        scale=2,
    )

    box_w, box_h = 210, 66
    y_offset = 22
    nodes_by_id = {n["id"]: n for n in spec.svg_nodes}

    # Draw edges first
    for src_id, tgt_id, label in spec.svg_edges:
        src = nodes_by_id.get(src_id)
        tgt = nodes_by_id.get(tgt_id)
        if not src or not tgt:
            continue
        x1 = int(src["x"] + box_w)
        y1 = int(src["y"] + y_offset + box_h // 2)
        x2 = int(tgt["x"])
        y2 = int(tgt["y"] + y_offset + box_h // 2)
        if x2 < x1:
            x1 = int(src["x"] + box_w // 2)
            y1 = int(src["y"] + y_offset + box_h)
            x2 = int(tgt["x"] + box_w // 2)
            y2 = int(tgt["y"] + y_offset)
        canvas.draw_line(x1, y1, x2, y2, color_hex="#64748b", thickness=2)
        if label:
            mx = (x1 + x2) // 2
            my = (y1 + y2) // 2 - 10
            canvas.fill_rect(mx - 62, my - 4, 124, 18, "#f1f5f9", border_hex="#cbd5e1")
            canvas.draw_text(
                label[:18],
                mx - 58,
                my + 2,
                color_hex="#1e293b",
                scale=1,
                center_width=116,
            )

    # Draw nodes
    for n in spec.svg_nodes:
        nx = int(n["x"])
        ny = int(n["y"] + y_offset)
        color = n.get("color", "#1d4ed8")
        canvas.fill_rect(nx, ny, box_w, box_h, color, border_hex="#0f172a")
        canvas.draw_text(
            n["label"][:28],
            nx,
            ny + 15,
            color_hex="#ffffff",
            scale=1,
            center_width=box_w,
        )
        canvas.draw_text(
            n["sub"][:32],
            nx,
            ny + 38,
            color_hex="#e2e8f0",
            scale=1,
            center_width=box_w,
        )

    # Footer summary
    canvas.draw_text(
        spec.summary[:100],
        34,
        height - 28,
        color_hex="#475569",
        scale=1,
    )
    canvas.save_png(png_path)
