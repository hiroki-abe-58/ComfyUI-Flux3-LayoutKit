# ComfyUI FLUX 3 LayoutKit (unofficial)

Community nodes for the layout table of **FLUX 3 Image Klein** in ComfyUI. Not affiliated with, sponsored by or endorsed by Black Forest Labs or Comfy-Org.

> **Status: 0.1.0 pre-release, model-free verification only.** The nodes, the prompt contract and the workflows are tested against
> the official reference code and a real ComfyUI v0.41.0 queue, **but nothing here has been run with the FLUX 3 weights yet**
> (see [Verification status](#verification-status)). What the model does with the `remove` rows in particular is not specified by BFL.

日本語の概要は [README.ja.md](README.ja.md)。

## What this adds, and what it does not

ComfyUI v0.41.0 already ships **`Create Bounding Boxes`** (a drawing canvas with preview) and **`FLUX 3 Image Layout Prompt`**
(appends text-to-image boxes to a prompt). Use those for drawing and for plain text-to-image layouts. This package covers what they do not:

| | ComfyUI built-in | LayoutKit |
|---|---|---|
| Draw boxes on a canvas | yes (`Create Bounding Boxes`) | no, reuses it via the `elements` input |
| Text-to-image rows (`id`, `bbox`, `desc`) | yes | yes (same JSON as ComfyUI writes) |
| **Reference-image edit rows** (`from`, `src_bbox`, `tgt_bbox`: add / move / keep / remove) | no | **yes** |
| **0-1 vs 0-1000 mix-up detection** | no (a 0-1 box is passed through as is) | **yes, an error** |
| **`<id>` citation check** (every region is named in the prompt) | no | yes (can be switched off) |
| Official-CLI `--boxes` file (0-1) from the same rows | no | yes (`cli_boxes_json` output) |
| Preview of source and target boxes, move arrows, remove crosses | target boxes only | yes |

If ComfyUI later gains edit rows itself, this package should be retired in favour of the built-in nodes.

## Nodes

* **FLUX 3 Layout Region (LayoutKit)** `Flux3LayoutRegion` - one region; chain several through `regions`.
  `operation`: `generate` (text-to-image row) or an edit row: `add` (new content at the target box), `move` (source box to target box),
  `keep` (target = source, "stays where it is"), `remove` (source box, `tgt_bbox` null). `scale`: `canvas_1000` (0-1000, as in the prompt table) or `unit_1`
  (0-1, as in the official CLI file). Boxes are `y_min, x_min, y_max, x_max` (y first, origin top-left).
* **FLUX 3 Layout Compose (LayoutKit)** `Flux3LayoutCompose` - `prompt` + `regions` (or the `elements` of `Create Bounding Boxes`) -> `prompt` with the table appended,
  `table_json`, and `cli_boxes_json`.
* **FLUX 3 Layout Preview (LayoutKit)** `Flux3LayoutPreview` - draws the table as an `IMAGE` (target boxes solid, source boxes dashed, arrows for moves, a cross for removals), optionally over a reference image.

## Coordinate contract

| Source | Where | Scale | Order |
|---|---|---|---|
| Diffusers blog "Welcome FLUX.3 Image Klein in Diffusers" | JSON appended to the prompt | 0-1000 | `[y_min, x_min, y_max, x_max]` |
| `black-forest-labs/flux-3-image-klein` CLI `--boxes` | separate JSON file | 0-1, converted with `round(v * 1000)` | same |
| ComfyUI `Create Bounding Boxes` -> `elements` | node output | 0-1000 | same |

`tests/fixtures/upstream_to_canvas.json` holds rows produced by the official converter at commit `e53f4ea697fe45db8f38fca91a90f5623f7f8f37`;
the tests require identical output (values and key order). `scripts/check_upstream_parity.py` also feeds every composed prompt to the official
`detect()` / `is_finished()` / `valid_added()` and requires the rows back unchanged. Boxes are **guidance, not hard masks**: elements may extend past their box and small ones may be dropped.

## Install

ComfyUI >= v0.41.0 (the FLUX 3 nodes). No extra Python dependencies.

```
cd ComfyUI/custom_nodes
git clone https://github.com/hiroki-abe-58/ComfyUI-Flux3-LayoutKit
```

Models are **not** included and are gated by Black Forest Labs: accept the FLUX Kommunity License on Hugging Face
for [black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy) yourself, then place
`flux3_image_klein_sd_int8_convrot.safetensors` (diffusion_models, 5.8 GB), `qwen3vl_4b_int8_convrot.safetensors` (text_encoders, 4.9 GB) and
`flux2-vae.safetensors` (vae, 0.3 GB) where ComfyUI expects them. NVFP4 needs a Blackwell GPU. This package never downloads weights.

## Workflows (`workflows/api`, API format)

Load with the ComfyUI frontend's API-format import, or queue them with `scripts/queue_prompt.py` (loopback only). They mirror the official
`image_flux3_klein_distilled_*` templates (16 steps, cfg 1, euler / simple, `ConditioningZeroOut` negative).

* `layout_only_api.json` - two regions -> prompt text + preview image. **No model files needed.**
* `flux3_klein_distilled_layout_t2i_api.json` - text-to-image with two regions.
* `flux3_klein_distilled_layout_move_api.json` - reference edit: one region moved, one kept. Uses ComfyUI's `example.png` as the reference placeholder; replace it.
* `flux3_klein_distilled_layout_remove_api.json` - reference edit: one region removed (`tgt_bbox` null).

```
python scripts/queue_prompt.py workflows/api/layout_only_api.json --port 8188
```

## Verification status

| Item | State |
|---|---|
| Contract vs official converter / parser at a pinned commit | **Tested** (`scripts/check_upstream_parity.py`, 6 cases) |
| Built-in `FLUX 3 Image Layout Prompt` gives the same text as `Flux3LayoutCompose` for text-to-image rows | **Tested** (ComfyUI v0.41.0 code, in-process) |
| Node registration in a real ComfyUI server (`/object_info`) and a queued `layout_only` prompt, output text and preview checked | **Tested**, ComfyUI v0.41.0, Windows 11, CPU-only, Python 3.12, torch 2.14.1 |
| Model workflows pass ComfyUI's graph validation (node types, sockets) | **Tested**: the only validation errors are the missing model files |
| Generation with FLUX 3 Image Klein weights (text-to-image with regions, reference move, removal) | **Untested** - the weights are gated and were not available to the author's machine |
| Layout boxes actually steering the image; behaviour of `remove` (null target) | **Untested** |
| RTX 5090 / NVFP4 / INT8 timings and VRAM | **Untested**, no numbers are claimed |
| macOS / MPS / MLX | **Planned**; no MLX port of FLUX 3 is known to the author |
| Linux | CI runs the model-free tests; no generation |

## Licensing

The code in this repository is MIT (see `LICENSE`). It applies **only to the original plugin code**. The FLUX 3 Image Klein weights are under the
FLUX Kommunity License; the text encoder and prompt upsampler are Apache-2.0; BFL's reference code is Apache-2.0. Nothing here relicenses any of them,
and nothing here is advice on commercial fine-tuning, which the license restricts. See `docs/LICENSING.md` and `NOTICE`.

## Development

```
python -m pytest -q          # set FLUX3_KIT_COMFYUI_DIR to a ComfyUI >= v0.41.0 checkout to run the node tests
python -m ruff check . && python -m ruff format --check .
python scripts/check_upstream_parity.py PATH/TO/flux-3-image-klein --expect-commit e53f4ea697fe45db8f38fca91a90f5623f7f8f37
python scripts/make_workflows.py
```

## Roadmap

Run the real-weights checks (text-to-image with regions, move, removal; direct text-encoder input versus the official CLI on the same prompt and seed);
a browser-side drag editor for edit rows if the built-in canvas does not gain one; a workflow in the frontend's graph format; macOS CPU CI.
