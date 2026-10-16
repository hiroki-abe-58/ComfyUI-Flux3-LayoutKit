import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
API = sorted((ROOT / "workflows" / "api").glob("*.json"))

# node types that exist in ComfyUI v0.41.0 and are used by the shipped workflows
KNOWN = {
    "UNETLoader", "CLIPLoader", "VAELoader", "CLIPTextEncode", "ConditioningZeroOut", "KSampler", "VAEDecode", "SaveImage",
    "PreviewImage", "PreviewAny", "LoadImage", "EmptyFlux2LatentImage", "ReferenceMultiLatent",
}  # fmt: skip
OURS = {"Flux3LayoutRegion", "Flux3LayoutCompose", "Flux3LayoutPreview"}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_workflows_exist():
    assert {p.name for p in API} == {
        "layout_only_api.json",
        "flux3_klein_distilled_layout_t2i_api.json",
        "flux3_klein_distilled_layout_move_api.json",
        "flux3_klein_distilled_layout_remove_api.json",
    }


@pytest.mark.parametrize("path", API, ids=lambda p: p.name)
def test_links_point_at_real_nodes_and_known_types(path):
    graph = _load(path)
    for nid, node in graph.items():
        assert node["class_type"] in KNOWN | OURS, f"{path.name}: {nid} uses an unknown node type {node['class_type']}"
        for name, value in node["inputs"].items():
            if isinstance(value, list):
                assert len(value) == 2 and value[0] in graph, f"{path.name}: {nid}.{name} links to a missing node {value}"
                assert isinstance(value[1], int) and value[1] >= 0


@pytest.mark.parametrize("path", API, ids=lambda p: p.name)
def test_our_node_inputs_match_their_schemas(path, comfy_dir):
    from flux3_layoutkit import nodes

    classes = {c.define_schema().node_id: c for c in (nodes.Flux3LayoutRegion, nodes.Flux3LayoutCompose, nodes.Flux3LayoutPreview)}
    for nid, node in _load(path).items():
        if node["class_type"] not in OURS:
            continue
        schema = classes[node["class_type"]].define_schema()
        declared = {i.id: i for i in schema.inputs}
        assert set(node["inputs"]) <= set(declared), f"{path.name}:{nid} sets unknown inputs {set(node['inputs']) - set(declared)}"
        missing = [i for i, spec in declared.items() if not spec.optional and i not in node["inputs"] and getattr(spec, "default", None) is None]
        assert not missing, f"{path.name}:{nid} lacks required inputs {missing}"
        for iid, value in node["inputs"].items():
            options = getattr(declared[iid], "options", None)
            if options and not isinstance(value, list):
                assert value in options


@pytest.mark.parametrize("path", [p for p in API if p.name != "layout_only_api.json"], ids=lambda p: p.name)
def test_model_graph_follows_the_official_distilled_recipe(path):
    graph = _load(path)
    ks = next(n for n in graph.values() if n["class_type"] == "KSampler")["inputs"]
    assert (ks["steps"], ks["cfg"], ks["sampler_name"], ks["scheduler"], ks["denoise"]) == (16, 1, "euler", "simple", 1)
    clip = next(n for n in graph.values() if n["class_type"] == "CLIPLoader")["inputs"]
    assert clip["type"] == "flux3"
    names = {n["class_type"]: n["inputs"] for n in graph.values()}
    assert names["UNETLoader"]["unet_name"] == "flux3_image_klein_sd_int8_convrot.safetensors"
    assert names["VAELoader"]["vae_name"] == "flux2-vae.safetensors"
    text_source = next(n for n in graph.values() if n["class_type"] == "CLIPTextEncode")["inputs"]["text"]
    assert graph[text_source[0]]["class_type"] == "Flux3LayoutCompose"


def test_edit_graphs_wire_the_reference_into_both_conditionings():
    for name in ("move", "remove"):
        graph = _load(ROOT / "workflows" / "api" / f"flux3_klein_distilled_layout_{name}_api.json")
        ref = next(n for n in graph.values() if n["class_type"] == "ReferenceMultiLatent")["inputs"]
        assert ref["images.image0"] and ref["positive"] and ref["negative"]
        ks = next(n for n in graph.values() if n["class_type"] == "KSampler")["inputs"]
        assert ks["positive"][1] == 0 and ks["negative"][1] == 1 and ks["latent_image"][1] == 2  # outputs of ReferenceMultiLatent


def test_checked_in_workflows_equal_the_generator_output():
    spec = importlib.util.spec_from_file_location("make_workflows", ROOT / "scripts" / "make_workflows.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name, graph in mod.build().items():
        assert _load(ROOT / "workflows" / "api" / name) == graph, f"{name} is out of date; run scripts/make_workflows.py"


def test_no_absolute_local_paths_in_tracked_text():
    pattern = re.compile(r"[A-Za-z]:\\{1,2}[A-Za-z0-9_.-]+\\|/home/[a-z]+/|/Users/[A-Za-z]+/")
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(p in {".git", "__pycache__", ".ruff_cache", ".pytest_cache"} for p in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".json", ".md", ".toml", ".yml", ".yaml", ".txt"} or path.name == "FLUX3_LAYOUTKIT_CURSOR_PROMPT.md":
            continue
        assert not pattern.search(path.read_text(encoding="utf-8")), f"absolute path in {path.relative_to(ROOT)}"
