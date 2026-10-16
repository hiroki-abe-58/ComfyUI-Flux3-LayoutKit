"""Write the API-format prompts in workflows/api. Every node type and socket name below exists in ComfyUI v0.41.0
(checked against /object_info); the model graph mirrors the official image_flux3_klein_distilled_* templates:
UNETLoader + CLIPLoader(type flux3) + VAELoader, CLIPTextEncode, ConditioningZeroOut as the negative,
KSampler 16 steps / cfg 1 / euler / simple, EmptyFlux2LatentImage or ReferenceMultiLatent, VAEDecode, SaveImage.

    python scripts/make_workflows.py
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "workflows" / "api"

UNET = "flux3_image_klein_sd_int8_convrot.safetensors"
CLIP = "qwen3vl_4b_int8_convrot.safetensors"
VAE = "flux2-vae.safetensors"
EDIT_REFERENCE = "example.png"  # ComfyUI ships this file in its input folder


def region(prev, rid, desc, op, tgt=(0, 0, 0, 0), src=(0, 0, 0, 0), scale="canvas_1000", ref=0):
    inputs = {"region_id": rid, "desc": desc, "operation": op, "scale": scale, "ref_index": ref}
    for name, v in zip(("tgt_y_min", "tgt_x_min", "tgt_y_max", "tgt_x_max"), tgt):
        inputs[name] = v
    for name, v in zip(("src_y_min", "src_x_min", "src_y_max", "src_x_max"), src):
        inputs[name] = v
    if prev:
        inputs["regions"] = [prev, 0]
    return {"class_type": "Flux3LayoutRegion", "inputs": inputs}


def model_graph(prompt_node, latent_node, reference=False, seed=1, steps=16, prefix="flux3_layoutkit"):
    """Nodes shared by every model workflow. ``prompt_node`` is the id of the node whose output 0 is the composed prompt."""
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "flux3", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": [prompt_node, 0]}},
        "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
    }
    pos, neg, latent = ["4", 0], ["5", 0], [latent_node, 0]
    if reference:
        g["6"] = {"class_type": "LoadImage", "inputs": {"image": EDIT_REFERENCE}}
        g["7"] = {
            "class_type": "ReferenceMultiLatent",
            "inputs": {
                "positive": ["4", 0],
                "negative": ["5", 0],
                "vae": ["3", 0],
                "resolution": "resize",
                "resolution.megapixels": 1.0,
                "images.image0": ["6", 0],
            },
        }
        pos, neg, latent = ["7", 0], ["7", 1], ["7", 2]
    g["8"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "positive": pos,
            "negative": neg,
            "latent_image": latent,
            "seed": seed,
            "steps": steps,
            "cfg": 1,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1,
        },
    }
    g["9"] = {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}}
    g["10"] = {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}}
    return g


def compose(prompt, regions_node):
    return {"class_type": "Flux3LayoutCompose", "inputs": {"prompt": prompt, "regions": [regions_node, 0], "require_citations": True}}


def build():
    flows = {}

    # 1) layout only: no model files needed, queueable on any ComfyUI that has the nodes
    flows["layout_only_api.json"] = {
        "20": region(None, "obj_1", "a red and yellow striped hot-air balloon", "generate", tgt=(80, 60, 480, 380)),
        "21": region("20", "obj_2", "a small blue hot-air balloon", "generate", tgt=(0.2, 0.62, 0.42, 0.8), scale="unit_1"),
        "22": compose("hot-air balloons over a green valley at sunrise, <obj_1> on the left, <obj_2> on the right", "21"),
        "23": {"class_type": "PreviewAny", "inputs": {"source": ["22", 0]}},
        "24": {"class_type": "Flux3LayoutPreview", "inputs": {"regions": ["21", 0], "width": 1024, "height": 1024}},
        "25": {"class_type": "PreviewImage", "inputs": {"images": ["24", 0]}},
    }

    # 2) text-to-image, two layout regions
    t2i = {
        "20": region(None, "obj_1", "a red and yellow striped hot-air balloon", "generate", tgt=(80, 60, 480, 380)),
        "21": region("20", "obj_2", "a small blue hot-air balloon", "generate", tgt=(200, 620, 420, 800)),
        "22": compose("hot-air balloons over a green valley at sunrise, <obj_1> on the left, <obj_2> on the right", "21"),
        "23": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "24": {"class_type": "Flux3LayoutPreview", "inputs": {"regions": ["21", 0], "width": 1024, "height": 1024}},
        "25": {"class_type": "PreviewImage", "inputs": {"images": ["24", 0]}},
    }
    t2i.update(model_graph("22", "23", prefix="flux3_layoutkit_t2i"))
    flows["flux3_klein_distilled_layout_t2i_api.json"] = t2i

    # 3) reference edit: move one region, keep the rest in place
    move = {
        "20": region(None, "obj_1", "the subject being moved", "move", src=(500, 150, 850, 350), tgt=(194, 55, 544, 255)),
        "21": region("20", "obj_2", "the backdrop stays where it is", "keep", src=(0, 0, 1000, 1000)),
        "22": compose("In <ref_image_0>, move the subject <obj_1> up and to the left, the rest <obj_2> unchanged.", "21"),
        "23": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "24": {"class_type": "Flux3LayoutPreview", "inputs": {"regions": ["21", 0], "width": 1024, "height": 1024}},
        "25": {"class_type": "PreviewImage", "inputs": {"images": ["24", 0]}},
    }
    move.update(model_graph("22", "23", reference=True, prefix="flux3_layoutkit_move"))
    flows["flux3_klein_distilled_layout_move_api.json"] = move

    # 4) reference edit: remove one region (tgt_bbox null)
    remove = {
        "20": region(None, "obj_1", "the item to remove", "remove", src=(200, 200, 400, 400)),
        "22": compose("In <ref_image_0>, remove <obj_1> and fill the place with the surrounding background.", "20"),
        "23": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "24": {"class_type": "Flux3LayoutPreview", "inputs": {"regions": ["20", 0], "width": 1024, "height": 1024}},
        "25": {"class_type": "PreviewImage", "inputs": {"images": ["24", 0]}},
    }
    remove.update(model_graph("22", "23", reference=True, prefix="flux3_layoutkit_remove"))
    flows["flux3_klein_distilled_layout_remove_api.json"] = remove
    return flows


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, graph in build().items():
        (OUT / name).write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote", name)
