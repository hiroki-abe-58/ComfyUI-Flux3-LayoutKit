"""LayoutKit for FLUX 3 Image Klein: reference-image edit regions and a strict box-scale check (unofficial community nodes)."""

import logging

try:
    from .flux3_layoutkit.nodes import comfy_entrypoint  # noqa: F401
except ImportError as e:  # ComfyUI without the V3 node API
    logging.error("[Flux3-LayoutKit] not loaded: %s", e)
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}
