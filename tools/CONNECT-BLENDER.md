# Connect Codebuff to your Blender

A tiny HTTP bridge runs **inside your Blender** and lets me (the agent) execute
bpy code, inspect your scene, and export GLBs — live, while you watch.

## 1. Start the bridge (pick one)

**GUI (recommended — you keep working, I see your scene live):**
1. Open Blender normally.
2. `Scripting` workspace → Text Editor → **New**, paste the contents of
   `tools/blender_bridge.py` (or open the file via Text → Open).
3. Click **Run Script** (▶ or Alt+P).
   Console prints: `[blender_bridge] listening on http://127.0.0.1:8765`

**Or one command from a terminal:**
```bash
/home/aime/Downloads/blender-5.2.2-linux-x64/blender --python tools/blender_bridge.py
# headless variant (no window): add --background
```

## 2. Tell me you started it

Say "bridge is up" (or anything similar). I will:

```bash
curl -s http://127.0.0.1:8765/ping
# {"ok":true,"blender":"5.2.2", ...}
```

From then on I can, while you watch:
- `scene` — list your objects, types, dimensions
- run any bpy code in your session (add/modify objects, materials, armatures…)
- export your scene to a GLB anywhere on disk (e.g. `compound_game_kit/character_human.glb`)

## 3. Quick manual test (optional)

```bash
chmod +x tools/blend_cmd.sh
tools/blend_cmd.sh ping
tools/blend_cmd.sh 'import bpy; print(sorted(bpy.data.objects.keys()))'
```

## Notes

- Bound to **127.0.0.1 only** — nothing on your network can reach it.
- Anyone/anything running on your machine can run bpy code through it — that's
  the point. Stop it by restarting Blender or re-running the script with the
  server thread killed (close the Blender file).
- The bridge lives only in that Blender session — re-run the script each time
  you restart Blender (or I can add it to your startup file on request).
