#!/bin/sh
# Writes manifest.json: each library folder's files with their sizes (for download progress),
# plus each wall image's shape, average colour and faces, so the site can pair walls without downloading every image.
# GitHub Pages has no directory listings, so index.html reads this instead.
cd "$(dirname "$0")"
python3 - <<'PY'
import json, math, os, struct, subprocess, tempfile
def look(path):
    # Same measure as imageLook() in index.html: hue as a vector weighted by chroma, plus average lightness.
    with tempfile.TemporaryDirectory() as t:
        out = os.path.join(t, 'a.bmp')
        info = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', path], capture_output=True, text=True).stdout.split()
        w, h = int(info[info.index('pixelWidth:') + 1]), int(info[info.index('pixelHeight:') + 1])
        subprocess.run(['sips', '-s', 'format', 'bmp', '-z', '24', '24', path, '--out', out], capture_output=True, check=True)
        b = open(out, 'rb').read()
    off, W, H, bpp = struct.unpack_from('<I', b, 10)[0], *struct.unpack_from('<ii', b, 18), struct.unpack_from('<H', b, 28)[0]
    step, row = bpp // 8, ((bpp // 8) * W + 3) & ~3
    x = y = l = 0
    for j in range(abs(H)):
        for i in range(W):
            p = off + j * row + i * step
            bl, g, r = (v / 255 for v in b[p:p + 3])
            mx, mn = max(r, g, bl), min(r, g, bl); ch = mx - mn
            l += (mx + mn) / 2
            if not ch: continue
            hh = (((g - bl) / ch) % 6 if mx == r else (bl - r) / ch + 2 if mx == g else (r - g) / ch + 4) * math.pi / 3
            x += ch * math.cos(hh); y += ch * math.sin(hh)
    n = W * abs(H)
    return {'aspect': round(w / h, 3), 'px': max(w, h), 'x': round(x / n, 4), 'y': round(y / n, 4), 'l': round(l / n, 4)}
dirs = ['avatars', 'crowd', 'dances', 'screens', 'songs', 'walks', 'walls']
out = {}
for d in dirs:
    if not os.path.isdir(d): continue
    out[d] = {}
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if f.startswith('.') or not os.path.isfile(p): continue
        e = {'size': os.path.getsize(p)}
        if d == 'walls':
            try: e['look'] = look(p)
            except Exception: pass
        out[d][f] = e
# Faces in the wall images (macOS Vision), so the page can keep the main face in view when it crops
walls = [os.path.join('walls', f) for f in out.get('walls', {})]
if walls:
    try:
        r = subprocess.run(['swift', 'scripts/faces.swift', *walls], capture_output=True, text=True, timeout=600)
        for p, faces in json.loads(r.stdout).items():
            e = out['walls'][os.path.basename(p)]
            if 'look' in e: e['look']['faces'] = faces
    except Exception as ex: print('faces skipped:', ex)
json.dump(out, open('manifest.json', 'w'), indent=1)
print({d: len(v) for d, v in out.items()})
PY
