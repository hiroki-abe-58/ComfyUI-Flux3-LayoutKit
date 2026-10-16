"""Pure-Python layout contract for FLUX 3 Image Klein prompts (no ComfyUI, torch or numpy needed).

The model reads a JSON table of regions appended to the caption. Boxes are ``[y_min, x_min, y_max, x_max]``
(y first) on a 0-1000 canvas with the origin at the top-left. The official BFL CLI takes the same boxes in a
separate file as 0-1 fractions and converts them with ``round(v * 1000)``.

This module differs from the references in one deliberate way: a value that looks like the other scale is an
error here, not something that is clamped or passed through.
"""

from __future__ import annotations

import json
import math
import re

CANVAS = 1000
SCALE_CANVAS = "canvas_1000"
SCALE_UNIT = "unit_1"
SCALES = (SCALE_CANVAS, SCALE_UNIT)

OP_ADD = "add"
OP_MOVE = "move"
OP_KEEP = "keep"
OP_REMOVE = "remove"
OPERATIONS = (OP_ADD, OP_MOVE, OP_KEEP, OP_REMOVE)

_ID = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_REF = re.compile(r"ref_image_(\d+)")


class LayoutError(ValueError):
    """The layout cannot be expressed as a valid FLUX 3 region table."""


def _finite_numbers(box, name: str) -> list[float]:
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        raise LayoutError(f"{name} must be [y_min, x_min, y_max, x_max], got {box!r}")
    out = []
    for v in box:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise LayoutError(f"{name} holds a non-numeric or non-finite value: {box!r}")
        out.append(float(v))
    return out


def canvas_box(box, scale: str, name: str = "bbox") -> list[int]:
    """Validate a box and return it as integers on the 0-1000 canvas.

    ``scale`` says what the caller meant. A box that contradicts it is rejected so a 0-1 box is never
    silently read as 0-1000 (a box about 1/1000 of the image) or a 0-1000 box clamped to 0-1.
    """
    if scale not in SCALES:
        raise LayoutError(f"scale must be one of {SCALES}, got {scale!r}")
    vals = _finite_numbers(box, name)
    if scale == SCALE_UNIT:
        if max(vals) > 1.0:
            raise LayoutError(f"{name} {box!r} has a value above 1 but the scale is {SCALE_UNIT}; did you mean {SCALE_CANVAS}?")
        if min(vals) < 0.0:
            raise LayoutError(f"{name} {box!r} has a negative value")
        grid = [round(v * CANVAS) for v in vals]
    else:
        if min(vals) < 0.0 or max(vals) > CANVAS:
            raise LayoutError(f"{name} {box!r} is outside 0..{CANVAS}")
        if max(vals) <= 1.0:
            raise LayoutError(
                f"{name} {box!r} looks like 0..1 fractions but the scale is {SCALE_CANVAS}; "
                f"on the 0..{CANVAS} canvas this box would cover about a millionth of the image. Did you mean {SCALE_UNIT}?"
            )
        grid = [int(round(v)) for v in vals]
    if not (grid[2] > grid[0] and grid[3] > grid[1]):
        raise LayoutError(f"{name} {box!r} is empty or inverted on the canvas ({grid}); expected y_max > y_min and x_max > x_min")
    return grid


def _check_id(region_id: str) -> str:
    if not isinstance(region_id, str) or not _ID.fullmatch(region_id):
        raise LayoutError(f"region id {region_id!r} must match [A-Za-z][A-Za-z0-9_]*")
    return region_id


def _check_desc(desc: str) -> str:
    if not isinstance(desc, str) or not desc.strip():
        raise LayoutError("a region needs a non-empty description")
    return desc.strip()


def add_row(region_id: str, desc: str, bbox, scale: str = SCALE_CANVAS) -> dict:
    """A text-to-image region, the same row the official layout table uses: id, bbox, desc."""
    return {"id": _check_id(region_id), "bbox": canvas_box(bbox, scale), "desc": _check_desc(desc)}


def edit_row(region_id: str, desc: str, operation: str, src_bbox=None, tgt_bbox=None, ref_index: int = 0, scale: str = SCALE_CANVAS) -> dict:
    """A reference-image edit region: id, from, src_bbox, tgt_bbox, desc.

    * ``add``: new content at ``tgt_bbox``; ``from`` is ``"target"`` and ``src_bbox`` is null.
    * ``move``: content at ``src_bbox`` of reference ``ref_index`` goes to ``tgt_bbox``.
    * ``keep``: like ``move`` with ``tgt_bbox == src_bbox`` (the official blog: the region "stays where it is").
    * ``remove``: content at ``src_bbox`` is taken out; ``tgt_bbox`` is null.

    ``remove`` follows the null handling of the official CLI converter and prompt validator. The blog does not
    document it, so how the model reacts to it is not specified upstream.
    """
    if operation not in OPERATIONS:
        raise LayoutError(f"operation must be one of {OPERATIONS}, got {operation!r}")
    row = {"id": _check_id(region_id)}
    if operation == OP_ADD:
        if tgt_bbox is None:
            raise LayoutError("add needs a target box")
        row.update({"from": "target", "src_bbox": None, "tgt_bbox": canvas_box(tgt_bbox, scale, "tgt_bbox")})
    else:
        if isinstance(ref_index, bool) or not isinstance(ref_index, int) or ref_index < 0:
            raise LayoutError(f"ref_index must be a non-negative integer, got {ref_index!r}")
        if src_bbox is None:
            raise LayoutError(f"{operation} needs a source box")
        src = canvas_box(src_bbox, scale, "src_bbox")
        if operation == OP_REMOVE:
            tgt = None
        elif operation == OP_KEEP:
            tgt = list(src)
        else:
            if tgt_bbox is None:
                raise LayoutError("move needs a target box")
            tgt = canvas_box(tgt_bbox, scale, "tgt_bbox")
        row.update({"from": f"ref_image_{ref_index}", "src_bbox": src, "tgt_bbox": tgt})
    row["desc"] = _check_desc(desc)
    return row


def rows_from_native_elements(elements) -> list[dict]:
    """Rows from the elements of ComfyUI's ``Create Bounding Boxes`` node (already on the 0-1000 canvas).

    Mirrors what ComfyUI's own ``FLUX 3 Image Layout Prompt`` writes (ids ``obj_1``..``obj_N``, a text element's
    string appended to the description in quotes) but validates the boxes.
    """
    rows = []
    if not isinstance(elements, list):
        raise LayoutError("elements must be a list")
    for i, el in enumerate(elements):
        if not isinstance(el, dict) or "bbox" not in el:
            raise LayoutError(f"element {i} has no bbox")
        desc = str(el.get("desc", "")).strip()
        if el.get("type") == "text" and el.get("text"):
            desc = f'{desc} "{el["text"]}"'.strip()
        rows.append(add_row(f"obj_{i + 1}", desc, el["bbox"], SCALE_CANVAS))
    return rows


def validate_rows(rows: list[dict]) -> list[dict]:
    """Check a finished table: unique ids, a well-formed shape per row, and edit rows that are consistent."""
    if not isinstance(rows, list) or not rows:
        raise LayoutError("the layout table is empty")
    seen = set()
    if len({"bbox" in r for r in rows if isinstance(r, dict)}) > 1:
        raise LayoutError("a table is either all text-to-image rows (bbox) or all edit rows (from/src_bbox/tgt_bbox); the references never mix them")
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise LayoutError(f"row {i} is not an object")
        rid = _check_id(row.get("id"))
        if rid in seen:
            raise LayoutError(f"duplicate region id {rid!r}")
        seen.add(rid)
        _check_desc(row.get("desc"))
        if "bbox" in row:
            if set(row) != {"id", "bbox", "desc"}:
                raise LayoutError(f"row {rid!r} mixes bbox with edit keys")
            canvas_box(row["bbox"], SCALE_CANVAS)
            continue
        origin, src, tgt = row.get("from"), row.get("src_bbox"), row.get("tgt_bbox")
        if set(row) != {"id", "from", "src_bbox", "tgt_bbox", "desc"}:
            raise LayoutError(f"row {rid!r} has unexpected keys {sorted(row)}")
        if src is None and tgt is None:
            raise LayoutError(f"row {rid!r} has neither a source nor a target box")
        if origin == "target":
            if src is not None or tgt is None:
                raise LayoutError(f"row {rid!r} comes from 'target': src_bbox must be null and tgt_bbox set")
        elif isinstance(origin, str) and _REF.fullmatch(origin):
            if src is None:
                raise LayoutError(f"row {rid!r} comes from {origin} but has no src_bbox")
        else:
            raise LayoutError(f"row {rid!r}: from must be 'target' or 'ref_image_<n>', got {origin!r}")
        for name, box in (("src_bbox", src), ("tgt_bbox", tgt)):
            if box is not None:
                canvas_box(box, SCALE_CANVAS, name)
    return rows


def reference_indices(rows: list[dict]) -> list[int]:
    """The reference-image indices the table refers to, sorted."""
    found = set()
    for row in rows:
        m = _REF.fullmatch(str(row.get("from", "")))
        if m:
            found.add(int(m.group(1)))
    return sorted(found)


def check_citations(prompt: str, rows: list[dict]) -> list[str]:
    """Ids of rows the caption never cites as ``<id>``. The model ties words to boxes through these tags."""
    return [row["id"] for row in rows if f"<{row['id']}>" not in prompt]


def compose_prompt(prompt: str, rows: list[dict], require_citations: bool = True) -> str:
    """``<caption> <json rows>``, the layout form that the official reference code and the blog use."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise LayoutError("the prompt is empty")
    if split_prompt(prompt)[1] is not None:  # a table already in the prompt would end up as two
        raise LayoutError("the prompt already ends with a JSON region table; remove it before composing")
    validate_rows(rows)
    if require_citations:
        missing = check_citations(prompt, rows)
        if missing:
            raise LayoutError(f"the prompt does not cite {', '.join(f'<{m}>' for m in missing)}; add the tags or turn citations off")
    return f"{prompt.rstrip()} {json.dumps(rows, ensure_ascii=False)}"


def split_prompt(text: str) -> tuple[str, list | None]:
    """Caption and rows: the last ``[`` from which the rest of the text parses as a JSON list of region objects."""
    for i in range(len(text) - 1, -1, -1):
        if text[i] != "[":
            continue
        try:
            rows = json.loads(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(rows, list) and rows and all(isinstance(r, dict) and isinstance(r.get("id"), str) for r in rows):
            return text[:i].rstrip(), rows
    return text.strip(), None


def to_unit_boxes_file(rows: list[dict]) -> list[dict]:
    """The rows as the official CLI ``--boxes`` file expects them: 0..1 fractions, null kept as null."""

    def unit(box):
        return None if box is None else [v / CANVAS for v in box]

    out = []
    for row in validate_rows(rows):
        if "bbox" in row:
            out.append({"id": row["id"], "desc": row["desc"], "bbox": unit(row["bbox"])})
        else:
            out.append(
                {
                    "id": row["id"],
                    "desc": row["desc"],
                    "from": row["from"],
                    "src_bbox": unit(row["src_bbox"]),
                    "tgt_bbox": unit(row["tgt_bbox"]),
                }
            )
    return out
