"""Write the exact prompts behind the published demo images to workflows/api/demo.

The reference image for the edits is the output of the text-to-image demo. Copy it into ComfyUI's input folder
under the name below before queueing the edit demos.

    python scripts/make_demo_workflows.py
"""

import json
from pathlib import Path

from make_workflows import build, region

OUT = Path(__file__).resolve().parent.parent / "workflows" / "api" / "demo"
REFERENCE = "flux3kit_ref_balloons.png"
EMPTY_SOURCE_CAPTION = (
    "In <ref_image_0>, move the large red and yellow balloon <obj_1> from the upper left to the lower right, "
    "so the upper left sky is empty and there is only one red balloon; the small blue balloon <obj_2> stays where it is."
)


def demos():
    flows = build()
    out = {}

    t2i = json.loads(json.dumps(flows["flux3_klein_distilled_layout_t2i_api.json"]))
    t2i["8"]["inputs"]["seed"] = 1
    out["demo_t2i_two_regions_seed1.json"] = t2i

    def move(seed, caption):
        g = json.loads(json.dumps(flows["flux3_klein_distilled_layout_move_api.json"]))
        g["6"]["inputs"]["image"] = REFERENCE
        g["20"] = region(None, "obj_1", "the large red and yellow striped hot-air balloon", "move", src=(80, 60, 480, 380), tgt=(480, 520, 880, 840))
        g["21"] = region("20", "obj_2", "the small blue hot-air balloon stays where it is", "keep", src=(200, 620, 420, 800))
        g["22"]["inputs"]["prompt"] = caption
        g["8"]["inputs"]["seed"] = seed
        return g

    out["demo_move_seed1_caption_without_empty_source.json"] = move(
        1,
        "In <ref_image_0>, move the large red and yellow balloon <obj_1> down to the lower right over the green valley; "
        "the small blue balloon <obj_2> stays where it is. Hot-air balloons over a green valley at sunrise.",
    )
    out["demo_move_seed2.json"] = move(2, EMPTY_SOURCE_CAPTION)
    out["demo_move_seed3.json"] = move(3, EMPTY_SOURCE_CAPTION)

    rem = json.loads(json.dumps(flows["flux3_klein_distilled_layout_remove_api.json"]))
    rem["6"]["inputs"]["image"] = REFERENCE
    rem["20"] = region(None, "obj_1", "the small blue hot-air balloon", "remove", src=(200, 620, 420, 800))
    rem["22"]["inputs"]["prompt"] = (
        "In <ref_image_0>, remove the small blue hot-air balloon <obj_1>; the sky there is empty. "
        "One red and yellow hot-air balloon over a green valley at sunrise."
    )
    rem["8"]["inputs"]["seed"] = 1
    out["demo_remove_seed1.json"] = rem
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, graph in demos().items():
        (OUT / name).write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote", name)
