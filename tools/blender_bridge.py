"""
Compound Ops — live Blender bridge.
Lets an external agent (Codebuff) drive YOUR open Blender over local HTTP.

Start it one of two ways:
  A) GUI:  Blender -> Scripting -> Text Editor -> Open tools/blender_bridge.py -> Run Script (Alt+P)
     (safe to re-run; it replaces any previous bridge instance on the same port)
  B) CLI:  /path/to/blender --background --python tools/blender_bridge.py

It binds 127.0.0.1 ONLY (your machine, no network exposure).

Endpoints:
  GET  /ping   -> {"ok":true,"blender":"5.2.2","scene":"...","objects":N}
  GET  /scene  -> object list (name/type/verts/dims/location)
  POST /run    body {"code":"..."}  -> executes bpy python on Blender's MAIN thread
                                  returns {"ok","result","printed","error"}
  POST /export body {"path":"/abs/out.glb"} -> exports the current scene as GLB

Threading notes: bpy.context is main-thread-only. In background mode the HTTP
loop runs on the main thread; in GUI mode requests are marshaled to the main
thread through bpy.app.timers.
"""
import bpy, json, threading, io, sys, traceback, contextlib, queue, time
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer

PORT = 8765
BACKGROUND = "--background" in sys.argv

def _port():
    args = sys.argv
    if "--" in args:
        rest = args[args.index("--") + 1:]
        if "--port" in rest: return int(rest[rest.index("--port") + 1])
    return PORT

# ---------------- work execution (main thread) ----------------
_work = queue.Queue()
_timer_armed = False

def _drain():
    try:
        while True:
            fn, box = _work.get_nowait()
            try: box["out"] = fn()
            except Exception: box["out"] = {"ok": False, "error": traceback.format_exc()}
    except queue.Empty:
        pass
    return 0.05

def run_on_main(fn, timeout=60):
    """Run fn on Blender's main thread (GUI mode marshals via timers)."""
    global _timer_armed
    if threading.current_thread() is threading.main_thread():
        return fn()
    box = {}
    _work.put((fn, box))
    if not _timer_armed:
        bpy.app.timers.register(_drain, first_interval=0.05, persistent=True)
        _timer_armed = True
    t0 = time.time()
    while "out" not in box:
        if time.time() - t0 > timeout:
            return {"ok": False, "error": "main-thread execution timed out (%ss)" % timeout}
        time.sleep(0.02)
    return box["out"]

# ---------------- bpy work (always main thread) ----------------
def scene_summary():
    objs = []
    for o in bpy.data.objects:
        objs.append({
            "name": o.name, "type": o.type,
            "verts": len(o.data.vertices) if getattr(o, "data", None) and hasattr(o.data, "vertices") else None,
            "dims": [round(v, 3) for v in o.dimensions],
            "loc": [round(v, 3) for v in o.location],
        })
    return {"ok": True, "blender": bpy.app.version_string, "scene": bpy.context.scene.name,
            "objects": objs, "count": len(objs)}

def run_code(code):
    buf = io.StringIO()
    g = {"bpy": bpy, "mathutils": __import__("mathutils"), "math": __import__("math")}
    try:
        with contextlib.redirect_stdout(buf):
            try:
                result = eval(code, g)              # pure expression -> return its value
            except SyntaxError:
                result = exec(code, g) or None      # statements / semicolon one-liners
        return {"ok": True, "result": repr(result) if result is not None else None,
                "printed": buf.getvalue()}
    except Exception:
        return {"ok": False, "error": traceback.format_exc(), "printed": buf.getvalue()}

def export_glb(path):
    try:
        kw = dict(filepath=path, export_format='GLB', export_yup=True)
        known = {p.identifier for p in bpy.ops.export_scene.gltf.get_rna_type().properties}
        bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in known})
        return {"ok": True, "path": path}
    except Exception:
        return {"ok": False, "error": traceback.format_exc()}

# ---------------- HTTP ----------------
class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a): pass  # keep the Blender console clean

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/ping":
            out = run_on_main(lambda: {"ok": True, "blender": bpy.app.version_string,
                                       "scene": bpy.context.scene.name, "objects": len(bpy.data.objects)})
            self._send(out)
        elif self.path == "/scene":
            self._send(run_on_main(scene_summary))
        else:
            self._send({"ok": False, "error": "unknown endpoint"}, 404)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            self._send({"ok": False, "error": "bad json: " + str(e)}, 400); return
        if self.path == "/run":
            self._send(run_on_main(lambda: run_code(str(body.get("code", ""))), timeout=120))
        elif self.path == "/export":
            self._send(run_on_main(lambda: export_glb(str(body.get("path", ""))), timeout=300))
        else:
            self._send({"ok": False, "error": "unknown endpoint"}, 404)

def serve():
    port = _port()
    # background: single-threaded server on the main thread (bpy.context needs it)
    # GUI: threaded server; handlers marshal work to the main thread via timers
    srv = HTTPServer(("127.0.0.1", port), H) if BACKGROUND else ThreadingHTTPServer(("127.0.0.1", port), H)
    print("[blender_bridge] listening on http://127.0.0.1:%d  (ping /scene /run /export)" % port, flush=True)
    return srv

if "_bridge_running" not in bpy.app.driver_namespace:
    bpy.app.driver_namespace["_bridge_running"] = True
    srv = serve()
    if BACKGROUND:
        srv.serve_forever()   # blocks; this IS the main loop in background mode
else:
    print("[blender_bridge] already running in this session", flush=True)
