"""ComfyUI V3 nodes for the FLUX 3 Image Klein layout table: build, validate, convert and preview.

These are small utilities, not an editor. Drawing boxes is left to ComfyUI's own ``Create Bounding Boxes`` node
(its ``elements`` output is accepted here) and to the community editors. The nodes write the same table text as the
official reference code, refuse a 0-1 box given as 0-1000 (or the reverse), and export the official CLI ``--boxes`` file.
"""

from __future__ import annotations

import json

import numpy as np
import torch
from comfy_api.latest import ComfyExtension, io
from PIL import Image
from typing_extensions import override

from . import contract
from .preview import render

Flux3Regions = io.Custom("FLUX3_REGIONS")

OP_GENERATE = "generate"
REGION_OPERATIONS = [OP_GENERATE, *contract.OPERATIONS]


def _box(inputs: tuple[float, float, float, float]):
    return list(inputs)


class Flux3LayoutRegion(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        box = [
            io.Float.Input(name, default=0.0, min=0.0, max=1000.0, step=0.001, tooltip=tip)
            for name, tip in (
                ("tgt_y_min", "Target box (text-to-image 'generate' and edit 'add'/'move'/'keep'): top edge."),
                ("tgt_x_min", "Target box: left edge."),
                ("tgt_y_max", "Target box: bottom edge."),
                ("tgt_x_max", "Target box: right edge."),
                ("src_y_min", "Source box in the reference image ('move'/'keep'/'remove'): top edge."),
                ("src_x_min", "Source box: left edge."),
                ("src_y_max", "Source box: bottom edge."),
                ("src_x_max", "Source box: right edge."),
            )
        ]
        return io.Schema(
            node_id="Flux3LayoutRegion",
            display_name="FLUX 3 Layout Region (LayoutKit)",
            category="model/conditioning/flux",
            description=(
                "One region of a FLUX 3 Image layout table. Boxes are y_min, x_min, y_max, x_max (y first). "
                "Chain several of these through 'regions'. Unused boxes are ignored."
            ),
            inputs=[
                Flux3Regions.Input("regions", optional=True, tooltip="Regions collected so far."),
                io.String.Input("region_id", default="obj_1", tooltip="Cite it in the prompt as <region_id>."),
                io.String.Input(
                    "desc", multiline=True, default="", tooltip="What this region contains (or, for move/keep/remove, the content being moved)."
                ),
                io.Combo.Input(
                    "operation",
                    options=REGION_OPERATIONS,
                    default=OP_GENERATE,
                    tooltip="generate: text-to-image region. add / move / keep / remove: reference-image edit regions.",
                ),
                io.Combo.Input(
                    "scale",
                    options=list(contract.SCALES),
                    default=contract.SCALE_CANVAS,
                    tooltip=(
                        "canvas_1000: 0-1000 like the prompt table. unit_1: 0-1 fractions like the official CLI --boxes file. "
                        "A box that contradicts the choice is an error."
                    ),
                ),
                io.Int.Input("ref_index", default=0, min=0, max=9, tooltip="Which reference image (ref_image_N) a move/keep/remove box points into."),
                *box,
            ],
            outputs=[Flux3Regions.Output(display_name="regions")],
        )

    @classmethod
    def execute(
        cls,
        region_id,
        desc,
        operation,
        scale,
        ref_index,
        tgt_y_min,
        tgt_x_min,
        tgt_y_max,
        tgt_x_max,
        src_y_min,
        src_x_min,
        src_y_max,
        src_x_max,
        regions=None,
    ) -> io.NodeOutput:
        tgt = _box((tgt_y_min, tgt_x_min, tgt_y_max, tgt_x_max))
        src = _box((src_y_min, src_x_min, src_y_max, src_x_max))
        try:
            if operation == OP_GENERATE:
                row = contract.add_row(region_id, desc, tgt, scale)
            else:
                row = contract.edit_row(
                    region_id,
                    desc,
                    operation,
                    src_bbox=src if operation != contract.OP_ADD else None,
                    tgt_bbox=tgt if operation in (contract.OP_ADD, contract.OP_MOVE) else None,
                    ref_index=ref_index,
                    scale=scale,
                )
            table = [*(regions or []), row]
            contract.validate_rows(table)
        except contract.LayoutError as e:
            raise ValueError(f"FLUX 3 Layout Region '{region_id}': {e}") from e
        return io.NodeOutput(table)


class Flux3LayoutCompose(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="Flux3LayoutCompose",
            display_name="FLUX 3 Layout Compose (LayoutKit)",
            category="model/conditioning/flux",
            description=(
                "Appends the region table to the prompt. Also returns the same boxes as an official-CLI --boxes JSON (0-1). "
                "Use 'elements' to take boxes straight from ComfyUI's Create Bounding Boxes node instead of 'regions'."
            ),
            inputs=[
                io.String.Input("prompt", multiline=True, dynamic_prompts=True, tooltip="Cite every region as <region_id>."),
                Flux3Regions.Input("regions", optional=True),
                io.Array.Input("elements", optional=True, tooltip="Elements output of Create Bounding Boxes (text-to-image rows, 0-1000)."),
                io.Boolean.Input("require_citations", default=True, tooltip="Fail if a region's <id> never appears in the prompt."),
            ],
            outputs=[
                io.String.Output(display_name="prompt"),
                io.String.Output(display_name="table_json"),
                io.String.Output(display_name="cli_boxes_json"),
            ],
        )

    @classmethod
    def execute(cls, prompt, require_citations, regions=None, elements=None) -> io.NodeOutput:
        try:
            if regions and elements:
                raise contract.LayoutError("connect either 'regions' or 'elements', not both")
            if elements:
                rows = contract.rows_from_native_elements(elements)
            elif regions:
                rows = regions
            else:
                raise contract.LayoutError("no regions: connect 'regions' or 'elements'")
            composed = contract.compose_prompt(prompt, rows, require_citations)
            cli = contract.to_unit_boxes_file(rows)
        except contract.LayoutError as e:
            raise ValueError(f"FLUX 3 Layout Compose: {e}") from e
        return io.NodeOutput(composed, json.dumps(rows, ensure_ascii=False), json.dumps(cli, ensure_ascii=False, indent=1))


class Flux3LayoutPreview(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="Flux3LayoutPreview",
            display_name="FLUX 3 Layout Preview (LayoutKit)",
            category="model/conditioning/flux",
            description="Draws target boxes (solid), source boxes (dashed), move arrows and remove crosses on a canvas or a reference image.",
            inputs=[
                Flux3Regions.Input("regions"),
                io.Int.Input("width", default=1024, min=64, max=8192, step=16),
                io.Int.Input("height", default=1024, min=64, max=8192, step=16),
                io.Image.Input("background", optional=True, tooltip="Optional reference image drawn faded under the boxes."),
            ],
            outputs=[io.Image.Output(display_name="preview")],
        )

    @classmethod
    def execute(cls, regions, width, height, background=None) -> io.NodeOutput:
        try:
            contract.validate_rows(regions)
        except contract.LayoutError as e:
            raise ValueError(f"FLUX 3 Layout Preview: {e}") from e
        bg = None
        if background is not None and len(background) > 0:
            arr = (background[0].clamp(0, 1).cpu().numpy() * 255).round().astype(np.uint8)
            bg = Image.fromarray(arr[..., :3])
        img = render(regions, width, height, bg)
        tensor = torch.from_numpy(np.asarray(img).astype(np.float32) / 255.0).unsqueeze(0)
        return io.NodeOutput(tensor)


class Flux3LayoutKitExtension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [Flux3LayoutRegion, Flux3LayoutCompose, Flux3LayoutPreview]


async def comfy_entrypoint() -> Flux3LayoutKitExtension:
    return Flux3LayoutKitExtension()
