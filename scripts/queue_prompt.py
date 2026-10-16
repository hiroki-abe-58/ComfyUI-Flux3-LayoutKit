"""Queue an API-format prompt on a local ComfyUI, wait for that prompt_id, and print what it produced.

    python scripts/queue_prompt.py workflows/api/layout_only_api.json --port 8188 [--save-dir DIR]

Only loopback hosts are accepted. Exit code 0 only when ComfyUI reports the prompt as successfully completed.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def call(base, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8")
            return json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise SystemExit(f"HTTP {e.code} from {path}: {body[:3000]}") from None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow", type=Path)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--save-dir", type=Path)
    ap.add_argument("--allow-partial", action="store_true", help="run the valid part of a graph although some nodes failed validation")
    ap.add_argument("--set", action="append", default=[], metavar="NODE.INPUT=JSON", help="override one input, value parsed as JSON")
    args = ap.parse_args(argv)
    if args.host not in LOOPBACK:
        raise SystemExit(f"refusing to talk to {args.host}: loopback only")
    base = f"http://{args.host}:{args.port}"
    prompt = json.loads(args.workflow.read_text(encoding="utf-8"))
    for item in args.set:
        key, _, value = item.partition("=")
        node, _, name = key.partition(".")
        prompt[node]["inputs"][name] = json.loads(value)
    queued = call(base, "/prompt", {"prompt": prompt, "client_id": str(uuid.uuid4())})
    pid = queued["prompt_id"]
    print("prompt_id", pid)
    # ComfyUI drops an output node whose inputs fail validation (e.g. a missing model file) and still runs the others,
    # so a "success" can hide a skipped branch. Report it and fail unless the caller asked for a partial run.
    dropped = queued.get("node_errors") or {}
    for nid, info in dropped.items():
        for e in info.get("errors", []):
            print(
                "node_error", nid, info.get("class_type"), "|", e.get("type"), "|", e.get("message"), "|", e.get("extra_info", {}).get("input_name")
            )
    if dropped and not args.allow_partial:
        print("validation dropped part of the graph; nothing was executed to completion (use --allow-partial to run the rest)")
        call(base, "/queue", {"delete": [pid]})
        return 3
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        hist = call(base, f"/history/{pid}")
        if pid in hist:
            entry = hist[pid]
            status = entry.get("status", {})
            print("status", status.get("status_str"), "completed", status.get("completed"))
            if status.get("status_str") != "success":
                for m in status.get("messages", []):
                    if m[0] == "execution_error":
                        print("error", m[1].get("node_type"), m[1].get("exception_message"))
                return 1
            for nid, out in entry.get("outputs", {}).items():
                for kind, items in out.items():
                    for it in items:
                        if isinstance(it, dict) and "filename" in it:
                            q = urllib.parse.urlencode({k: it.get(k, "") for k in ("filename", "subfolder", "type")})
                            with urllib.request.urlopen(f"{base}/view?{q}", timeout=60) as r:
                                blob = r.read()
                            print("output", nid, kind, it["filename"], len(blob), "bytes")
                            if args.save_dir:
                                args.save_dir.mkdir(parents=True, exist_ok=True)
                                (args.save_dir / f"{nid}_{it['filename']}").write_bytes(blob)
                        else:
                            print("output", nid, kind, json.dumps(it, ensure_ascii=False)[:2000])
            return 0
        time.sleep(0.5)
    print("timeout waiting for", pid)
    return 2


if __name__ == "__main__":
    sys.exit(main())
