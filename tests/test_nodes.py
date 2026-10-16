import asyncio
import json

import numpy as np
import pytest

from flux3_layoutkit import contract as c


def _nodes():
    from flux3_layoutkit import nodes

    return nodes


def _region(nodes, regions=None, **kw):
    args = dict(
        region_id="obj_1",
        desc="x",
        operation="generate",
        scale="canvas_1000",
        ref_index=0,
        tgt_y_min=0.0,
        tgt_x_min=0.0,
        tgt_y_max=0.0,
        tgt_x_max=0.0,
        src_y_min=0.0,
        src_x_min=0.0,
        src_y_max=0.0,
        src_x_max=0.0,
    )
    args.update(kw)
    return nodes.Flux3LayoutRegion.execute(regions=regions, **args).result[0]


def test_extension_registers_three_nodes(comfy_dir):
    nodes = _nodes()
    ext = asyncio.run(nodes.comfy_entrypoint())
    listed = asyncio.run(ext.get_node_list())
    assert [n.define_schema().node_id for n in listed] == ["Flux3LayoutRegion", "Flux3LayoutCompose", "Flux3LayoutPreview"]
    # none of the ids collide with ComfyUI's own nodes
    import nodes as comfy_nodes  # noqa: F401  (ComfyUI's nodes.py)
    from comfy_extras import nodes_flux

    native = {"Flux3LayoutPrompt", "CreateBoundingBoxes"}
    assert not native & {n.define_schema().node_id for n in listed}
    assert hasattr(nodes_flux, "Flux3LayoutPrompt")


def test_schema_inputs_and_outputs(comfy_dir):
    nodes = _nodes()
    region = nodes.Flux3LayoutRegion.define_schema()
    assert [i.id for i in region.inputs][:6] == ["regions", "region_id", "desc", "operation", "scale", "ref_index"]
    assert region.inputs[3].options == ["generate", "add", "move", "keep", "remove"]
    assert region.inputs[4].default == "canvas_1000"
    compose = nodes.Flux3LayoutCompose.define_schema()
    assert [o.display_name for o in compose.outputs] == ["prompt", "table_json", "cli_boxes_json"]
    assert compose.inputs[3].default is True


def test_chain_generate_regions_and_compose(comfy_dir):
    nodes = _nodes()
    r1 = _region(nodes, region_id="obj_1", desc="red balloon", tgt_y_min=80, tgt_x_min=60, tgt_y_max=480, tgt_x_max=380)
    r2 = _region(nodes, r1, region_id="obj_2", desc="blue balloon", scale="unit_1", tgt_y_min=0.2, tgt_x_min=0.62, tgt_y_max=0.42, tgt_x_max=0.8)
    assert r2[1]["bbox"] == [200, 620, 420, 800]
    prompt, table, cli = nodes.Flux3LayoutCompose.execute(prompt="balloons <obj_1> and <obj_2>", require_citations=True, regions=r2).result
    assert prompt.endswith(table) and json.loads(table) == r2
    assert json.loads(cli)[0]["bbox"] == [0.08, 0.06, 0.48, 0.38]


def test_move_keep_remove_add_regions(comfy_dir):
    nodes = _nodes()
    move = _region(
        nodes,
        operation="move",
        region_id="knight_1",
        src_y_min=500,
        src_x_min=150,
        src_y_max=850,
        src_x_max=350,
        tgt_y_min=194,
        tgt_x_min=55,
        tgt_y_max=544,
        tgt_x_max=255,
    )
    assert move[0] == {"id": "knight_1", "from": "ref_image_0", "src_bbox": [500, 150, 850, 350], "tgt_bbox": [194, 55, 544, 255], "desc": "x"}
    keep = _region(nodes, operation="keep", region_id="bg", src_y_min=0, src_x_min=0, src_y_max=1000, src_x_max=1000, tgt_y_max=5.0, ref_index=2)
    assert keep[0]["tgt_bbox"] == keep[0]["src_bbox"] == [0, 0, 1000, 1000] and keep[0]["from"] == "ref_image_2"
    rem = _region(
        nodes,
        operation="remove",
        region_id="cup",
        src_y_min=200,
        src_x_min=200,
        src_y_max=400,
        src_x_max=400,
        tgt_y_min=1,
        tgt_x_min=1,
        tgt_y_max=2,
        tgt_x_max=2,
    )
    assert rem[0]["tgt_bbox"] is None  # the unused target widgets do not leak into a removal
    add = _region(
        nodes,
        operation="add",
        region_id="cactus",
        tgt_y_min=550,
        tgt_x_min=620,
        tgt_y_max=850,
        tgt_x_max=850,
        src_y_min=9,
        src_x_min=9,
        src_y_max=99,
        src_x_max=99,
    )
    assert add[0]["src_bbox"] is None and add[0]["from"] == "target"


def test_region_errors_name_the_region(comfy_dir):
    nodes = _nodes()
    with pytest.raises(ValueError, match="obj_1.*looks like 0..1"):
        _region(nodes, tgt_y_min=0.1, tgt_x_min=0.1, tgt_y_max=0.5, tgt_x_max=0.5)
    with pytest.raises(ValueError, match="duplicate"):
        first = _region(nodes, tgt_y_min=1, tgt_x_min=1, tgt_y_max=20, tgt_x_max=20)
        _region(nodes, first, tgt_y_min=1, tgt_x_min=1, tgt_y_max=20, tgt_x_max=20)
    with pytest.raises(ValueError, match="never mix"):
        first = _region(nodes, tgt_y_min=1, tgt_x_min=1, tgt_y_max=20, tgt_x_max=20)
        _region(nodes, first, region_id="b", operation="keep", src_y_min=1, src_x_min=1, src_y_max=20, src_x_max=20)


def test_compose_errors(comfy_dir):
    nodes = _nodes()
    reg = _region(nodes, tgt_y_min=1, tgt_x_min=1, tgt_y_max=20, tgt_x_max=20)
    with pytest.raises(ValueError, match="no regions"):
        nodes.Flux3LayoutCompose.execute(prompt="x", require_citations=True)
    with pytest.raises(ValueError, match="not both"):
        nodes.Flux3LayoutCompose.execute(prompt="<obj_1>", require_citations=True, regions=reg, elements=[{"bbox": [1, 1, 20, 20], "desc": "d"}])
    with pytest.raises(ValueError, match="does not cite"):
        nodes.Flux3LayoutCompose.execute(prompt="no tag", require_citations=True, regions=reg)


def test_compose_matches_comfyui_native_layout_prompt_for_text_to_image(comfy_dir):
    from comfy_extras import nodes_bounding_boxes, nodes_flux

    nodes = _nodes()
    regions = [
        {"x": 0.06, "y": 0.08, "w": 0.32, "h": 0.40, "type": "obj", "desc": "red balloon"},
        {"x": 0.62, "y": 0.20, "w": 0.18, "h": 0.22, "type": "text", "text": "HI", "desc": "small flag"},
    ]
    elements = nodes_bounding_boxes.build_elements(regions)
    native = nodes_flux.Flux3LayoutPrompt.execute(prompt="a valley <obj_1> <obj_2>", element=elements).result[0]
    ours = nodes.Flux3LayoutCompose.execute(prompt="a valley <obj_1> <obj_2>", require_citations=True, elements=elements).result[0]
    assert ours == native


def test_native_node_does_not_catch_scale_mix_up_but_ours_does(comfy_dir):
    from comfy_extras import nodes_flux

    nodes = _nodes()
    bad = [{"type": "obj", "bbox": [0.1, 0.1, 0.5, 0.5], "desc": "x"}]
    assert "0.1" in nodes_flux.Flux3LayoutPrompt.execute(prompt="<obj_1>", element=bad).result[0]  # passed through as is
    with pytest.raises(ValueError, match="looks like 0..1"):
        nodes.Flux3LayoutCompose.execute(prompt="<obj_1>", require_citations=True, elements=bad)


def test_preview_dimensions_and_box_placement(comfy_dir):
    nodes = _nodes()
    rows = [c.add_row("a", "x", [100, 200, 500, 600])]
    (img,) = nodes.Flux3LayoutPreview.execute(regions=rows, width=640, height=480).result
    assert tuple(img.shape) == (1, 480, 640, 3) and img.dtype.is_floating_point
    arr = (img[0].numpy() * 255).round().astype(np.uint8)
    # the box [y 100..500, x 200..600] on a 1000 canvas -> pixels x 128..384, y 48..240
    x0, y0, x1, y1 = round(200 * 640 / 1000), round(100 * 480 / 1000), round(600 * 640 / 1000), round(500 * 480 / 1000)
    assert (x0, y0, x1, y1) == (128, 48, 384, 240)
    edge = arr[y0 + 1, (x0 + x1) // 2]
    inside = arr[(y0 + y1) // 2, (x0 + x1) // 2]
    outside = arr[y0 - 10, (x0 + x1) // 2]
    assert tuple(edge) == (230, 57, 70)  # first palette colour drawn on the top edge
    assert tuple(inside) == tuple(outside) == (245, 245, 245)  # background untouched inside and outside


def test_preview_edit_rows_draw_source_target_and_cross(comfy_dir):
    nodes = _nodes()
    rows = [c.edit_row("m", "d", "move", [100, 100, 300, 300], [600, 600, 800, 800])]
    (img,) = nodes.Flux3LayoutPreview.execute(regions=rows, width=1000, height=1000).result
    arr = (img[0].numpy() * 255).round().astype(np.uint8)
    assert tuple(arr[601, 700]) == (230, 57, 70)  # solid target top edge
    assert tuple(arr[500, 500]) == (230, 57, 70)  # the arrow runs along the diagonal between the two box centres
    assert tuple(arr[500, 300]) == (245, 245, 245)  # and nothing is drawn off that line
    rem = [c.edit_row("r", "d", "remove", [100, 100, 300, 300])]
    (img2,) = nodes.Flux3LayoutPreview.execute(regions=rem, width=1000, height=1000).result
    a2 = (img2[0].numpy() * 255).round().astype(np.uint8)
    assert tuple(a2[200, 200]) == (230, 57, 70)  # centre of the cross over the removed source box


def test_preview_with_background_and_rejects_bad_table(comfy_dir):
    import torch

    nodes = _nodes()
    rows = [c.add_row("a", "x", [100, 200, 500, 600])]
    bg = torch.zeros(1, 32, 48, 3)
    (img,) = nodes.Flux3LayoutPreview.execute(regions=rows, width=256, height=128, background=bg).result
    assert tuple(img.shape) == (1, 128, 256, 3)
    assert float(img[0, 5, 5].mean()) > 0.3  # background was faded toward white, not left black
    with pytest.raises(ValueError, match="empty"):
        nodes.Flux3LayoutPreview.execute(regions=[], width=64, height=64)


def test_loads_through_comfyui_custom_node_loader(comfy_dir, tmp_path):
    """Import the repository root the way ComfyUI does (as a package) and check that the entrypoint is exposed."""
    import importlib.util
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("Flux3_LayoutKit_under_test", root / "__init__.py", submodule_search_locations=[str(root)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    assert callable(mod.comfy_entrypoint)
    assert not hasattr(mod, "NODE_CLASS_MAPPINGS") or mod.NODE_CLASS_MAPPINGS != {}
