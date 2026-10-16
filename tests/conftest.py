import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Set FLUX3_KIT_COMFYUI_DIR to a ComfyUI >= v0.41.0 checkout. FLUX3_KIT_REQUIRE_COMFYUI=1 turns "missing" into a failure.
_COMFY = os.environ.get("FLUX3_KIT_COMFYUI_DIR")
if _COMFY and Path(_COMFY).is_dir():
    sys.path.insert(0, _COMFY)
    import comfy.options

    comfy.options.enable_args_parsing(False)
    import comfy.cli_args

    comfy.cli_args.args.cpu = True


@pytest.fixture(scope="session")
def comfy_dir():
    if not (_COMFY and Path(_COMFY).is_dir()):
        if os.environ.get("FLUX3_KIT_REQUIRE_COMFYUI") == "1":
            pytest.fail("FLUX3_KIT_COMFYUI_DIR is not set but FLUX3_KIT_REQUIRE_COMFYUI=1")
        pytest.skip("FLUX3_KIT_COMFYUI_DIR not set")
    return Path(_COMFY)
