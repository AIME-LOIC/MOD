#!/usr/bin/env bash
# One-liner client for the Blender bridge (tools/blender_bridge.py).
#   ./tools/blend_cmd.sh ping
#   ./tools/blend_cmd.sh scene
#   ./tools/blend_cmd.sh 'result = sorted(bpy.data.objects.keys())'
#   ./tools/blend_cmd.sh --file /abs/path/script.py
set -e
PORT="${BLEND_PORT:-8765}"
if [ "$1" = "ping" ]; then curl -s "http://127.0.0.1:$PORT/ping"; echo; exit 0; fi
if [ "$1" = "scene" ]; then curl -s "http://127.0.0.1:$PORT/scene"; echo; exit 0; fi
if [ "$1" = "--file" ]; then
  python3 - "$2" <<'PY'
import json, sys, urllib.request
code = open(sys.argv[1]).read()
r = urllib.request.urlopen(urllib.request.Request(
    "http://127.0.0.1:8765/run",
    data=json.dumps({"code": code}).encode(),
    headers={"Content-Type": "application/json"}), timeout=120)
d = json.load(r)
print(d.get("printed") or "", end="")
if d.get("error"): print("ERROR:\n" + d["error"], file=sys.stderr); sys.exit(1)
if d.get("result") is not None: print(d["result"])
PY
  exit 0
fi
CODE="$1"
python3 - "$CODE" <<'PY'
import json, sys, urllib.request
r = urllib.request.urlopen(urllib.request.Request(
    "http://127.0.0.1:8765/run",
    data=json.dumps({"code": sys.argv[1]}).encode(),
    headers={"Content-Type": "application/json"}), timeout=120)
d = json.load(r)
print(d.get("printed") or "", end="")
if d.get("error"): print("ERROR:\n" + d["error"], file=sys.stderr); sys.exit(1)
PY
