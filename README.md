# ComfyUI FLUX 3 LayoutKit (unofficial)

Small, strict FLUX 3 layout/bbox interoperability utilities for ComfyUI.

This is not a bounding-box editor. It converts and validates the layout table that FLUX 3 Image Klein reads from the prompt, and records what happened
when that table was used with the real weights. It is an unofficial community project, not affiliated with or endorsed by Black Forest Labs or Comfy-Org.

日本語の概要は [README.ja.md](README.ja.md)。

## What it is for

1. **0-1 <-> 0-1000 conversion.** The official BFL CLI reads `--boxes` files as 0-1 fractions; the Diffusers post and ComfyUI write the table into the prompt on a 0-1000 canvas.
   Both orders are `[y_min, x_min, y_max, x_max]`. The `scale` choice on a region and the `cli_boxes_json` output of the compose node convert in both directions with the official rounding (`round(v * 1000)`).
2. **Strict validation** of `bbox`, `src_bbox`, `tgt_bbox`, `from` (`target` or `ref_image_N`), reference index, ids and descriptions, and detection of a 0-1 box handed over as 0-1000 (or the reverse), which is rejected instead of passed through or clamped. A caption that never cites a region as `<id>` is rejected too (can be switched off).
3. **Evidence.** The output is tested against the official parser at a pinned commit, and the table was used for real generations on an RTX 5090 ([docs/VERIFICATION.md](docs/VERIFICATION.md)), including a case where it did not do what one might expect.

## Other projects: use them for editing

Layout and edit-row authoring already exists in several projects, most with a visual editor. Prefer them for drawing boxes and for editing workflows; this repository has nothing to add there.
Summaries below follow each project's own README as read on 2026-10-17; I have not tested them.

| Project | What it is | This repo |
|---|---|---|
| [ComfyUI core](https://github.com/Comfy-Org/ComfyUI) (`Create Bounding Boxes`, `FLUX 3 Image Layout Prompt`, v0.41.0) | Built-in canvas and text-to-image layout rows | Reuses its `elements` output; the compose node produces the same text for those rows |
| [InpaintCanvas](https://github.com/DenRakEiw/ComfyUI-InpaintCanvas) | Rich canvas / editor workflow, with FLUX 3 box rows | - |
| [ComfyUI-EditUtils](https://github.com/lrzjason/ComfyUI-EditUtils) | Comprehensive editing utilities, with a FLUX.3 Klein bounding-box canvas | - |
| [NKD Klein Tools](https://github.com/Nekodificador/ComfyUI-NKD-Klein-Tools) | High-level Klein workflow utilities, with a box prompt node | - |
| [Comfyui-Flux3-PE-GGUF-T8](https://github.com/T8mars/Comfyui-Flux3-PE-GGUF-T8) | Local FLUX 3 prompt enhancement with GGUF, reference images and layout support | - |
| **This repo** | Narrow schema / coordinate validation and interoperability, parity tests, validation evidence | |

## Nodes

* **FLUX 3 Layout Region (LayoutKit)** `Flux3LayoutRegion` - one row of the table, chained through `regions`. Operations: `generate` (`{id, bbox, desc}`) and the edit rows
  `add`, `move`, `keep`, `remove` (`{id, from, src_bbox, tgt_bbox, desc}`; `tgt_bbox` is null for `remove`, `src_bbox` is null for `add`).
  `scale`: `canvas_1000` or `unit_1`. A table is either all `generate` rows or all edit rows, as in the references.
* **FLUX 3 Layout Compose (LayoutKit)** `Flux3LayoutCompose` - validates the table and appends it to the prompt; also returns `table_json` and `cli_boxes_json` (0-1, the official `--boxes` file).
  `elements` accepts the output of ComfyUI's `Create Bounding Boxes` instead of `regions`.
* **FLUX 3 Layout Preview (LayoutKit)** `Flux3LayoutPreview` - draws the validated table as an `IMAGE` (target boxes solid, source boxes dashed, a line for moves, a cross for removals), a check that a table says what you meant.

## Coordinate contract

| Source | Where | Scale | Order |
|---|---|---|---|
| Diffusers post "Welcome FLUX.3 Image Klein in Diffusers" | JSON appended to the prompt | 0-1000 | `[y_min, x_min, y_max, x_max]` |
| `black-forest-labs/flux-3-image-klein` CLI `--boxes` | separate JSON file | 0-1, converted with `round(v * 1000)` | same |
| ComfyUI `Create Bounding Boxes` -> `elements` | node output | 0-1000 | same |

`tests/fixtures/upstream_to_canvas.json` holds rows produced by the official converter at commit `e53f4ea697fe45db8f38fca91a90f5623f7f8f37`; the tests require identical output (values and key order).
`scripts/check_upstream_parity.py` also feeds every composed prompt to the official `detect()` / `is_finished()` / `valid_added()` and requires the rows back unchanged.
Differences on purpose: the official CLI converter clamps out-of-range values to 0-1; this package raises. Boxes are guidance for composition, not hard masks.

## Install

ComfyUI >= v0.41.0. No extra Python dependencies.

```
cd ComfyUI/custom_nodes
git clone https://github.com/hiroki-abe-58/ComfyUI-Flux3-LayoutKit
```

The model weights are not included and are gated by Black Forest Labs: accept the FLUX Kommunity License on Hugging Face for
[black-forest-labs/flux-3-image-klein-comfy](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy) yourself. The workflows use
`flux3_image_klein_sd_int8_convrot.safetensors` (diffusion_models), `qwen3vl_4b_int8_convrot.safetensors` (text_encoders) and `flux2-vae.safetensors` (vae), as in the official `image_flux3_klein_distilled_*` templates.
This package never downloads weights. It is not published on the Comfy Registry; install it from GitHub.

## Workflows (`workflows/api`, API format)

Import with the ComfyUI frontend's API-format loader, or queue with `scripts/queue_prompt.py` (loopback only; it fails if ComfyUI dropped part of the graph during validation).
They follow the official distilled templates (16 steps, cfg 1, euler / simple, `ConditioningZeroOut` negative). A workflow in the frontend's graph format is not provided.

* `layout_only_api.json` - two regions -> prompt text + preview image. **No model files needed.**
* `flux3_klein_distilled_layout_t2i_api.json`, `..._move_api.json`, `..._remove_api.json` - model workflows; the edit ones use ComfyUI's `example.png` as a placeholder reference.
* `demo/*.json` - the exact prompts behind the release images. The edit demos expect the text-to-image demo's output copied into ComfyUI's input folder as `flux3kit_ref_balloons.png`.

```
python scripts/queue_prompt.py workflows/api/layout_only_api.json --port 8188
```

## Verification status

| Item | State |
|---|---|
| Contract vs the official converter / parser at a pinned commit | **Tested** (`scripts/check_upstream_parity.py`, 6 cases, in CI) |
| Same text as the built-in `FLUX 3 Image Layout Prompt` for text-to-image rows | **Tested** (ComfyUI v0.41.0 code, in-process) |
| Node registration, clean-clone install, queued prompts on a real ComfyUI v0.41.0 server | **Tested** on Windows 11 with CUDA PyTorch; the model-free workflow also runs in CI on Ubuntu and Windows (CPU) |
| Text-to-image, two regions, distilled INT8, RTX 5090 | **Tested**, 1 run: both balloons landed inside their boxes |
| Edit row `move` | **Tested**, 3 runs: moved in 2; in the run whose caption did not describe the emptied source, the model added a copy instead |
| Edit row `remove` (`tgt_bbox` null) | **Tested**, 1 run: removed cleanly. BFL does not document null handling in the prompt, so this is observed behaviour |
| Time and GPU memory | Cold 4.7 s, warm about 2.2 s wall clock per 1024x1024 image; `nvidia-smi` peak 11225 MiB for the whole GPU (see docs/VERIFICATION.md for what this is and is not) |
| NVFP4, BF16, 4-reference edits, upsampler, other resolutions | **Untested** |
| Comparison with the official Diffusers / CLI output on the same prompt and seed | **Not done** |
| macOS / MPS / MLX | **Untested** |

Write the edit caption as the **result**, as BFL recommends: a move row whose caption only said "move X to the lower right" produced a second copy of X;
adding "so the upper left sky is empty and there is only one balloon" produced a real move.

## Licensing

The code in this repository is MIT (see `LICENSE`) and applies **only to the original plugin code**. The FLUX 3 Image Klein weights are under the
FLUX Kommunity License; the text encoder and prompt upsampler are Apache-2.0; BFL's reference code is Apache-2.0. Nothing here relicenses any of them.
Commercial fine-tuning and some commercial use need a separate license from Black Forest Labs; this is not legal advice. See `docs/LICENSING.md` and `NOTICE`.
The generated demo images attached to the release were produced with the FLUX 3 Image Klein weights by the repository author and are provided as evidence, not under the MIT license.

## Development

```
python -m pytest -q          # set FLUX3_KIT_COMFYUI_DIR to a ComfyUI >= v0.41.0 checkout to run the node tests
python -m ruff check . && python -m ruff format --check .
python scripts/check_upstream_parity.py PATH/TO/flux-3-image-klein --expect-commit e53f4ea697fe45db8f38fca91a90f5623f7f8f37
python scripts/make_workflows.py && python scripts/make_demo_workflows.py
```

## Status

0.1.0. No further features are planned; the open question is whether anything here belongs in the projects above or in ComfyUI itself.
