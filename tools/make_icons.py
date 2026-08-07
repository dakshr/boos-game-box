#!/usr/bin/env python3
"""Generate the three app icons.

Pure standard library — no Pillow, no design tool, no binary blobs checked
in that nobody can regenerate. Run it if you change the palette:

    python tools/make_icons.py

Writes public/icons/icon-192.png, icon-512.png and icon-maskable-512.png.

The maskable variant keeps its artwork inside the centre 80% so Android can
crop it to a circle, a squircle, or a rounded square without cutting the box
in half.
"""

import math
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS = os.path.join(os.path.dirname(HERE), "public", "icons")

CREAM = (253, 246, 227)
TEAL = (42, 157, 143)
MUSTARD = (233, 196, 106)
INK = (38, 70, 83)

SUPERSAMPLE = 3  # cheap antialiasing


# --- a very small PNG writer ------------------------------------------


def write_png(path: str, width: int, height: int, pixels: bytearray) -> None:
    """pixels is width*height*3 bytes of RGB."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0
        raw += pixels[y * stride : (y + 1) * stride]

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")

    with open(path, "wb") as fh:
        fh.write(png)


# --- a very small rasteriser ------------------------------------------


class Canvas:
    def __init__(self, size: int, background):
        self.size = size
        self.buf = bytearray(background * (size * size))

    def fill_spans(self, spans, color):
        """spans: iterable of (y, x0, x1) in pixels, x1 exclusive."""
        r, g, b = color
        pixel = bytes((r, g, b))
        size = self.size
        for y, x0, x1 in spans:
            if y < 0 or y >= size:
                continue
            x0 = max(0, int(math.floor(x0)))
            x1 = min(size, int(math.ceil(x1)))
            if x1 <= x0:
                continue
            self.buf[(y * size + x0) * 3 : (y * size + x1) * 3] = pixel * (x1 - x0)

    def downsample(self, factor: int) -> tuple[int, bytearray]:
        out_size = self.size // factor
        out = bytearray(out_size * out_size * 3)
        area = factor * factor
        for oy in range(out_size):
            for ox in range(out_size):
                r = g = b = 0
                for dy in range(factor):
                    row = (oy * factor + dy) * self.size
                    base = (row + ox * factor) * 3
                    for dx in range(factor):
                        i = base + dx * 3
                        r += self.buf[i]
                        g += self.buf[i + 1]
                        b += self.buf[i + 2]
                i = (oy * out_size + ox) * 3
                out[i] = r // area
                out[i + 1] = g // area
                out[i + 2] = b // area
        return out_size, out


def rounded_rect_spans(x0, y0, x1, y1, radius, height):
    radius = max(0.0, min(radius, (x1 - x0) / 2, (y1 - y0) / 2))
    for y in range(max(0, int(y0)), min(height, int(math.ceil(y1)))):
        cy = y + 0.5
        if cy < y0 or cy > y1:
            continue
        if cy < y0 + radius:
            dy = y0 + radius - cy
        elif cy > y1 - radius:
            dy = cy - (y1 - radius)
        else:
            dy = 0.0
        if dy >= radius:
            continue
        inset = radius - math.sqrt(max(0.0, radius * radius - dy * dy))
        yield y, x0 + inset, x1 - inset


def polygon_spans(points, height):
    ys = [p[1] for p in points]
    for y in range(max(0, int(min(ys))), min(height, int(math.ceil(max(ys))) + 1)):
        cy = y + 0.5
        crossings = []
        for i in range(len(points)):
            ax, ay = points[i]
            bx, by = points[(i + 1) % len(points)]
            if (ay <= cy < by) or (by <= cy < ay):
                crossings.append(ax + (cy - ay) / (by - ay) * (bx - ax))
        crossings.sort()
        for i in range(0, len(crossings) - 1, 2):
            yield y, crossings[i], crossings[i + 1]


def star_points(cx, cy, outer, inner, count=5):
    points = []
    for i in range(count * 2):
        angle = -math.pi / 2 + i * math.pi / count
        radius = outer if i % 2 == 0 else inner
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


# --- the artwork ------------------------------------------------------


def draw_icon(size: int, content: float) -> tuple[int, bytearray]:
    """`content` is the fraction of the icon the artwork may use."""
    big = size * SUPERSAMPLE
    canvas = Canvas(big, TEAL)

    unit = big * content / 2.0  # one art-space unit in pixels
    cx = cy = big / 2.0
    stroke = unit * 0.075

    def X(v):
        return cx + v * unit

    def Y(v):
        return cy + v * unit

    def rect(x0, y0, x1, y1, radius, color, outline=True):
        if outline:
            canvas.fill_spans(
                rounded_rect_spans(
                    X(x0) - stroke, Y(y0) - stroke, X(x1) + stroke, Y(y1) + stroke,
                    radius * unit + stroke, big,
                ),
                INK,
            )
        canvas.fill_spans(
            rounded_rect_spans(X(x0), Y(y0), X(x1), Y(y1), radius * unit, big), color
        )

    # A star, sitting behind the lid, peeking out of the box.
    star_cx, star_cy = X(0.0), Y(-0.45)
    outer, inner = 0.40 * unit, 0.17 * unit
    canvas.fill_spans(
        polygon_spans(
            star_points(star_cx, star_cy, outer + stroke, inner + stroke), big
        ),
        INK,
    )
    canvas.fill_spans(
        polygon_spans(star_points(star_cx, star_cy, outer, inner), big), MUSTARD
    )

    # The box itself: a body, and a lid resting slightly proud of it.
    rect(-0.72, 0.03, 0.72, 0.85, 0.10, CREAM)
    rect(-0.86, -0.21, 0.86, 0.11, 0.08, CREAM)

    return canvas.downsample(SUPERSAMPLE)


def main() -> int:
    os.makedirs(ICONS, exist_ok=True)
    jobs = [
        ("icon-192.png", 192, 0.66),
        ("icon-512.png", 512, 0.66),
        # maskable: artwork inside the centre 80%, so a circular crop is safe
        ("icon-maskable-512.png", 512, 0.50),
    ]
    for name, size, content in jobs:
        width, pixels = draw_icon(size, content)
        path = os.path.join(ICONS, name)
        write_png(path, width, width, pixels)
        print(f"  wrote {os.path.relpath(path)}  ({width}x{width})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
