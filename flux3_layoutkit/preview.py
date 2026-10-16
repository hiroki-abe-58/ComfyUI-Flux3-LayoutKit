"""Layout preview drawing. Pillow and numpy only; the torch conversion lives in nodes.py."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from .contract import CANVAS

PALETTE = ((230, 57, 70), (42, 157, 143), (69, 123, 157), (233, 196, 106), (131, 56, 236), (244, 162, 97), (6, 214, 160), (239, 71, 111))


def _px(box, width: int, height: int):
    y0, x0, y1, x1 = box
    return (round(x0 * width / CANVAS), round(y0 * height / CANVAS), round(x1 * width / CANVAS), round(y1 * height / CANVAS))


def _dashed_rect(draw: ImageDraw.ImageDraw, rect, colour, dash: int = 8, width: int = 2):
    x0, y0, x1, y1 = rect
    for x in range(x0, x1, dash * 2):
        draw.line([(x, y0), (min(x + dash, x1), y0)], fill=colour, width=width)
        draw.line([(x, y1), (min(x + dash, x1), y1)], fill=colour, width=width)
    for y in range(y0, y1, dash * 2):
        draw.line([(x0, y), (x0, min(y + dash, y1))], fill=colour, width=width)
        draw.line([(x1, y), (x1, min(y + dash, y1))], fill=colour, width=width)


def _font(size: int):
    try:
        return ImageFont.load_default(size)
    except TypeError:  # Pillow without sized default fonts
        return ImageFont.load_default()


def render(rows: list[dict], width: int, height: int, background: Image.Image | None = None) -> Image.Image:
    """Target boxes are solid, source boxes dashed, a move draws an arrow, a removal crosses out the source.

    Boxes are placed at ``round(v * size / 1000)`` so the preview matches the canvas the model is given.
    """
    if background is not None:
        canvas = background.convert("RGB").resize((width, height))
        canvas = Image.blend(canvas, Image.new("RGB", (width, height), (255, 255, 255)), 0.35)
    else:
        canvas = Image.new("RGB", (width, height), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    font = _font(max(12, min(width, height) // 40))
    for i, row in enumerate(rows):
        colour = PALETTE[i % len(PALETTE)]
        label = f"<{row['id']}>"
        if "bbox" in row:
            rect = _px(row["bbox"], width, height)
            draw.rectangle(rect, outline=colour, width=3)
            draw.text((rect[0] + 4, rect[1] + 2), label, fill=colour, font=font)
            continue
        src = _px(row["src_bbox"], width, height) if row["src_bbox"] else None
        tgt = _px(row["tgt_bbox"], width, height) if row["tgt_bbox"] else None
        if src:
            _dashed_rect(draw, src, colour)
            draw.text((src[0] + 4, src[1] + 2), f"{label} {row['from']}", fill=colour, font=font)
        if tgt:
            draw.rectangle(tgt, outline=colour, width=3)
            draw.text((tgt[0] + 4, tgt[1] + 2), label, fill=colour, font=font)
        if src and tgt and src != tgt:
            a = ((src[0] + src[2]) // 2, (src[1] + src[3]) // 2)
            b = ((tgt[0] + tgt[2]) // 2, (tgt[1] + tgt[3]) // 2)
            draw.line([a, b], fill=colour, width=2)
            draw.ellipse([b[0] - 5, b[1] - 5, b[0] + 5, b[1] + 5], fill=colour)
        if src and not tgt:
            draw.line([(src[0], src[1]), (src[2], src[3])], fill=colour, width=3)
            draw.line([(src[0], src[3]), (src[2], src[1])], fill=colour, width=3)
    return canvas
