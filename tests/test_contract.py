import json
from pathlib import Path

import pytest

from flux3_layoutkit import contract as c

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "upstream_to_canvas.json").read_text(encoding="utf-8"))
IDS = [f"{i}-{x['source']}" for i, x in enumerate(FIXTURE)]


def _rows_from_cli_input(items):
    """Rebuild rows from the official CLI --boxes input with this package's own builders."""
    rows = []
    for it in items:
        if "bbox" in it:
            rows.append(c.add_row(it["id"], it["desc"], it["bbox"], c.SCALE_UNIT))
        elif it["from"] == "target":
            rows.append(c.edit_row(it["id"], it["desc"], c.OP_ADD, tgt_bbox=it["tgt_bbox"], scale=c.SCALE_UNIT))
        elif it["tgt_bbox"] is None:
            rows.append(c.edit_row(it["id"], it["desc"], c.OP_REMOVE, src_bbox=it["src_bbox"], ref_index=int(it["from"][-1]), scale=c.SCALE_UNIT))
        else:
            rows.append(c.edit_row(it["id"], it["desc"], c.OP_MOVE, it["src_bbox"], it["tgt_bbox"], int(it["from"][-1]), c.SCALE_UNIT))
    return rows


@pytest.mark.parametrize("case", FIXTURE, ids=IDS)
def test_unit_input_matches_the_pinned_official_converter(case):
    # canvas_rows were produced by flux3.bbox.to_canvas at BFL flux-3-image-klein e53f4ea (see fixtures/README.md)
    ours = _rows_from_cli_input(case["input"])
    assert ours == case["canvas_rows"]
    assert json.dumps(ours) == json.dumps(case["canvas_rows"])  # key order matters in the prompt text


@pytest.mark.parametrize("case", FIXTURE, ids=IDS)
def test_cli_boxes_file_round_trips(case):
    rows = case["canvas_rows"]
    again = _rows_from_cli_input(c.to_unit_boxes_file(rows))
    assert again == rows


def test_diffusers_blog_move_example():
    # Welcome FLUX.3 Image Klein in Diffusers: move the knight, pin the backdrop
    knight = c.edit_row("knight_1", "grey amigurumi knight", c.OP_MOVE, [500, 150, 850, 350], [194, 55, 544, 255], 0)
    assert knight == {
        "id": "knight_1",
        "from": "ref_image_0",
        "src_bbox": [500, 150, 850, 350],
        "tgt_bbox": [194, 55, 544, 255],
        "desc": "grey amigurumi knight",
    }
    pinned = c.edit_row("background_1", "backdrop", c.OP_KEEP, [0, 0, 1000, 1000], ref_index=0)
    assert pinned["src_bbox"] == pinned["tgt_bbox"] == [0, 0, 1000, 1000]
    table = c.validate_rows([knight, pinned])
    assert c.reference_indices(table) == [0]


def test_blog_text_to_image_row_shape():
    row = c.add_row("background_1", "A flat field of neon yellow-green", [0, 0, 1000, 1000])
    assert list(row) == ["id", "bbox", "desc"] and row["bbox"] == [0, 0, 1000, 1000]


def test_remove_keeps_null_target():
    row = c.edit_row("obj_1", "the cup", c.OP_REMOVE, [200, 200, 400, 400])
    assert row["tgt_bbox"] is None and row["from"] == "ref_image_0"
    assert json.loads(json.dumps(row))["tgt_bbox"] is None


def test_add_has_null_source_and_target_origin():
    row = c.edit_row("obj_1", "a cactus", c.OP_ADD, tgt_bbox=[550, 620, 850, 850])
    assert row["from"] == "target" and row["src_bbox"] is None


# scale confusion must be detected, not accepted
def test_unit_values_in_canvas_mode_are_rejected():
    with pytest.raises(c.LayoutError, match="looks like 0..1"):
        c.canvas_box([0.1, 0.1, 0.5, 0.5], c.SCALE_CANVAS)


def test_canvas_values_in_unit_mode_are_rejected():
    with pytest.raises(c.LayoutError, match="above 1"):
        c.canvas_box([100, 100, 500, 500], c.SCALE_UNIT)


def test_whole_image_unit_box_is_not_silently_read_as_canvas():
    with pytest.raises(c.LayoutError):
        c.canvas_box([0, 0, 1, 1], c.SCALE_CANVAS)
    assert c.canvas_box([0, 0, 1, 1], c.SCALE_UNIT) == [0, 0, 1000, 1000]


@pytest.mark.parametrize(
    "box",
    [[0, 0, 0, 10], [10, 10, 5, 20], [0, 0, 10, 1001], [-1, 0, 10, 10], [0, 0, 10], [0, 0, 10, float("nan")], [0, 0, 10, True], "abcd", None],
)
def test_bad_boxes_rejected(box):
    with pytest.raises(c.LayoutError):
        c.canvas_box(box, c.SCALE_CANVAS)


def test_bad_ids_and_descriptions():
    for bad in ("", "1abc", "has space", "a-b", None, "<x>"):
        with pytest.raises(c.LayoutError):
            c.add_row(bad, "d", [0, 0, 10, 10])
    with pytest.raises(c.LayoutError):
        c.add_row("a", "   ", [0, 0, 10, 10])


def test_operations_need_their_boxes():
    with pytest.raises(c.LayoutError):
        c.edit_row("a", "d", c.OP_ADD)
    with pytest.raises(c.LayoutError):
        c.edit_row("a", "d", c.OP_MOVE, [0, 0, 10, 10])
    with pytest.raises(c.LayoutError):
        c.edit_row("a", "d", c.OP_REMOVE)
    with pytest.raises(c.LayoutError):
        c.edit_row("a", "d", "teleport", [0, 0, 10, 10])
    with pytest.raises(c.LayoutError):
        c.edit_row("a", "d", c.OP_KEEP, [0, 0, 10, 10], ref_index=-1)


def test_table_validation():
    a = c.add_row("a", "x", [0, 0, 10, 10])
    e = c.edit_row("b", "y", c.OP_KEEP, [0, 0, 10, 10])
    with pytest.raises(c.LayoutError, match="duplicate"):
        c.validate_rows([a, a])
    with pytest.raises(c.LayoutError, match="never mix"):
        c.validate_rows([a, e])
    with pytest.raises(c.LayoutError, match="empty"):
        c.validate_rows([])
    with pytest.raises(c.LayoutError):
        c.validate_rows([{"id": "z", "from": "target", "src_bbox": [0, 0, 10, 10], "tgt_bbox": [0, 0, 10, 10], "desc": "d"}])
    with pytest.raises(c.LayoutError):
        c.validate_rows([{"id": "z", "from": "somewhere", "src_bbox": [0, 0, 10, 10], "tgt_bbox": None, "desc": "d"}])
    with pytest.raises(c.LayoutError):
        c.validate_rows([{"id": "z", "from": "ref_image_0", "src_bbox": None, "tgt_bbox": None, "desc": "d"}])


def test_compose_appends_table_and_requires_citations():
    rows = [c.add_row("obj_1", "a red balloon", [80, 60, 480, 380])]
    text = c.compose_prompt("balloons over a valley, <obj_1> on the left", rows)
    assert text == 'balloons over a valley, <obj_1> on the left [{"id": "obj_1", "bbox": [80, 60, 480, 380], "desc": "a red balloon"}]'
    caption, parsed = c.split_prompt(text)
    assert caption == "balloons over a valley, <obj_1> on the left" and parsed == rows
    with pytest.raises(c.LayoutError, match="does not cite"):
        c.compose_prompt("balloons over a valley", rows)
    assert c.compose_prompt("balloons over a valley", rows, require_citations=False).startswith("balloons over a valley [")


def test_compose_refuses_a_second_table_but_allows_a_bracketed_caption():
    rows = [c.add_row("obj_1", "x", [80, 60, 480, 380])]
    once = c.compose_prompt("a <obj_1>", rows)
    with pytest.raises(c.LayoutError, match="already ends"):
        c.compose_prompt(once, rows)
    assert c.compose_prompt("a poster saying [SALE] <obj_1>", rows).startswith("a poster saying [SALE] <obj_1> [")


def test_unicode_and_quotes_survive():
    rows = [c.add_row("obj_1", '看板 "OPEN" ☕', [10, 10, 100, 100])]
    text = c.compose_prompt("<obj_1> 日本語", rows)
    assert "看板" in text and c.split_prompt(text)[1] == rows


def test_native_elements_match_comfyui_layout_prompt_rows():
    els = [
        {"type": "obj", "bbox": [80, 60, 480, 380], "desc": "balloon"},
        {"type": "text", "bbox": [10, 10, 100, 500], "text": "SALE", "desc": "sign"},
    ]
    rows = c.rows_from_native_elements(els)
    assert rows[0] == {"id": "obj_1", "bbox": [80, 60, 480, 380], "desc": "balloon"}
    assert rows[1]["desc"] == 'sign "SALE"' and rows[1]["id"] == "obj_2"
    with pytest.raises(c.LayoutError):
        c.rows_from_native_elements([{"type": "obj", "desc": "no box"}])
    with pytest.raises(c.LayoutError, match="looks like 0..1"):
        c.rows_from_native_elements([{"type": "obj", "bbox": [0.1, 0.1, 0.5, 0.5], "desc": "x"}])
