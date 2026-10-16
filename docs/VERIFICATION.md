# Verification record

Everything below was measured on one machine on 2026-10-17. No other model, GPU or OS has been tried. Numbers are single observations or
small samples, not benchmarks.

## Environment

| | |
|---|---|
| OS / GPU | Windows 11 Pro 10.0.26200, NVIDIA GeForce RTX 5090 (32 GB, compute capability 12.0), driver 610.88, 64 GB RAM |
| ComfyUI | v0.41.0, commit `98cc0bf84b7cb1383654c5b402e7612d875d6d22`, started with default memory settings (NORMAL_VRAM) |
| PyTorch | 2.14.1+cu130, Python 3.12 |
| LayoutKit | commit `351dfbd817a90a22a23a1dd22d7bd61c84621e2e`, installed as a clean `git clone` under a different folder name than the repository |
| Weights | `black-forest-labs/flux-3-image-klein-comfy` revision `5c9b714851dc072b04a23ef6d2d36421f5ccb3a0`; sizes match the Hub listing |

| File | SHA-256 |
|---|---|
| `diffusion_models/flux3_image_klein_sd_int8_convrot.safetensors` (distilled, INT8) | `847d8933548afd93df4af2cac2498e70891bf28d9dae06d695f536992e168fe2` |
| `text_encoders/qwen3vl_4b_int8_convrot.safetensors` | `32de113cbf8282b02cbff0794b637b9d6676da09314a1db5a30bcea9bf4ee01c` |
| `vae/flux2-vae.safetensors` | `868fe7b343cc8f3a19dbcfcafbc3d5f888802be3f89bd81b65b3621a066ce8f3` |

Settings for every run: distilled INT8, 1024x1024, 16 steps, cfg 1 (no guidance), euler / simple, no prompt upsampler. NVFP4 and BF16 were **not** run.

## Demo runs (`workflows/api/demo/`)

Each file was queued on the server above with `scripts/queue_prompt.py`; re-queueing the same file produced byte-identical PNGs on this machine
(SHA-256 compared for all five).

| Demo file | Seed | What happened (looked at by the author) |
|---|---|---|
| `demo_t2i_two_regions_seed1` | 1 | Two balloons, drawn inside their boxes: the red/yellow one spans about x 68-396, y 83-485 px for a box of x 61-389, y 82-491; the blue one about x 643-818, y 208-420 for a box of x 635-819, y 205-430 |
| `demo_move_seed2`, `demo_move_seed3` | 2, 3 | The red/yellow balloon (reference = the text-to-image image) was **moved** to the lower right; its old place is empty sky; the blue balloon stayed. The caption states the end state ("the upper left sky is empty") |
| `demo_move_seed1_caption_without_empty_source` | 1 | The caption only said "move ... down to the lower right". The model **added a second balloon** at the target and left the original in place. A move row alone did not make the source disappear |
| `demo_remove_seed1` | 1 | `tgt_bbox: null` row for the blue balloon: it was removed cleanly and the rest of the image was kept |

Observations, not guarantees: three move runs, one removal run, one text-to-image run. Boxes steer composition; they are not masks.
BFL's own guidance for editing is to write a full caption of the result.

## Timing and memory (one cold run, three warm runs)

| | Value |
|---|---|
| Cold, text-to-image, from queue to saved image (server already up, models loaded by this prompt) | 4.7 s wall clock |
| Warm, text-to-image, three runs with different seeds | 2.21 s, 2.21 s, 2.24 s wall clock |
| GPU memory seen by `nvidia-smi` during the cold run | peak 11225 MiB for the whole GPU, of which 1635 MiB was in use before the run |

Wall clock is measured around the HTTP queue call and includes polling (0.5 s steps) and the PNG download. Load / conditioning / denoise / VAE times,
PyTorch allocated / reserved peaks, host RAM and commit charge were **not measured**. No comparison with the official CLI or with other precisions has been made.

## Not verified

* Direct text-encoder input versus the official Diffusers / CLI path on the same prompt and seed (the BF16 reference weights were not downloaded).
* NVFP4, BF16, multi-reference (4 images) editing, the 9B prompt upsampler, resolutions other than 1024x1024.
* macOS / MPS / MLX. No MLX port of FLUX 3 is known to the author.
* Whether the model reads rows the way the Diffusers post describes in cases other than the ones above.
