# Licensing

Summary as read on 2026-10-17. This is not legal advice; read the upstream texts.

| Component | License | Where it applies |
|---|---|---|
| This repository's original code (`flux3_layoutkit/`, `scripts/`, `tests/`, workflows, docs) | MIT (`LICENSE`) | Only the original plugin code |
| FLUX 3 Image Klein weights (distilled and base) and the ComfyUI repackaged copies | FLUX Kommunity License v1.0 | Not included here, not relicensed here. Accept it on Hugging Face yourself. Non-commercial use is free; commercial output generation is allowed for Qualifying Users (under US$5M gross annualized revenue including affiliates) subject to the license's conditions; commercial fine-tuning and other commercial use need a separate license from Black Forest Labs |
| Qwen3-VL-4B-Instruct text encoder, the FLUX 3 prompt upsampler | Apache-2.0 (as stated on the model card) | Not included |
| `black-forest-labs/flux-3-image-klein` reference code | Apache-2.0 | Not included. `tests/fixtures/upstream_to_canvas.json` holds the output of its `flux3.bbox.to_canvas` plus two small example box files copied from its `examples/inputs` (see `tests/fixtures/README.md`) |
| ComfyUI | GPL-3.0 | Not included. The nodes import ComfyUI's `comfy_api` at runtime inside a ComfyUI process; CI checks out ComfyUI to run tests |
| `scripts/make_workflows.py` graph layout | original | Node types, widget values and file names follow the official `image_flux3_klein_distilled_*` templates of ComfyUI's workflow templates package; no template file is copied |

* The MIT license of this repository does **not** extend to any model weights, and nothing here changes the FLUX Kommunity License.
* This package does not download or redistribute weights and ships no generated images.
* "FLUX", "Black Forest Labs" and "ComfyUI" are used only to name what the nodes work with.
* Only publicly documented behaviour is relied on: the Diffusers blog post, the BFL reference repository and ComfyUI's source.
