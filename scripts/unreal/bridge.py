# File bridge: run every inbox/*.py inside the editor, write output to outbox/<name>.out.
import unreal, os, io, sys, time, traceback, contextlib
D = os.path.dirname(os.path.abspath(__file__))
IN, OUT = os.path.join(D, "inbox"), os.path.join(D, "outbox")
_last = [0.0]
def _tick(dt):
    now = time.time()
    if now - _last[0] < 0.5: return
    _last[0] = now
    for f in sorted(os.listdir(IN)):
        if not f.endswith(".py"): continue
        p = os.path.join(IN, f); code = open(p).read(); os.remove(p)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try: exec(compile(code, f, "exec"), {"__name__": "__bridge__", "unreal": unreal})
            except Exception: traceback.print_exc()
        with open(os.path.join(OUT, f[:-3] + ".tmp"), "w") as o: o.write(buf.getvalue())
        os.replace(os.path.join(OUT, f[:-3] + ".tmp"), os.path.join(OUT, f[:-3] + ".out"))
if not getattr(unreal, "_bridge_handle", None):
    unreal._bridge_handle = unreal.register_slate_post_tick_callback(_tick)
print("bridge running:", D)
