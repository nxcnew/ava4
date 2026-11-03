#!/usr/bin/env python3
"""Shrink the textures embedded in binary FBX files, leaving meshes, skeleton and animation untouched.

Mixamo characters embed 4096px PNGs, so each file is ~50MB though the model itself is ~2MB. This rewrites every
embedded image at most MAX px on its long side: JPEG when it has no transparency, PNG when it does (hair, lashes).

    ./shrink-fbx.py avatars/*.fbx          # in place; originals are kept in avatars-original/ (not committed)
"""
import os, shutil, struct, subprocess, sys, tempfile

MAX = 2048
UNUSED_MAX = 256  # specular / glossiness maps: index.html builds its own matte materials and never uses them
JPEG_QUALITY = 85


def read_fbx(b):
    assert b[:20] == b'Kaydara FBX Binary  ', 'not a binary FBX'
    version = struct.unpack_from('<I', b, 23)[0]
    wide = version >= 7500  # 64-bit record offsets from FBX 7.5
    off_fmt, null_len = ('<QQQ', 25) if wide else ('<III', 13)
    hdr = struct.calcsize(off_fmt)

    def prop(pos):
        t = chr(b[pos]); pos += 1
        size = {'Y': 2, 'C': 1, 'I': 4, 'F': 4, 'D': 8, 'L': 8}.get(t)
        if size: return [t, b[pos:pos + size]], pos + size
        if t in 'SR':
            n = struct.unpack_from('<I', b, pos)[0]
            return [t, b[pos + 4:pos + 4 + n]], pos + 4 + n
        n = struct.unpack_from('<I', b, pos + 8)[0]  # arrays: length, encoding, compressed length, data
        return [t, b[pos:pos + 12 + n]], pos + 12 + n

    def node(pos):
        end, nprops, _ = struct.unpack_from(off_fmt, b, pos)
        if end == 0: return None, pos + null_len
        nl = b[pos + hdr]
        name = b[pos + hdr + 1:pos + hdr + 1 + nl].decode()
        pos += hdr + 1 + nl
        props = []
        for _ in range(nprops):
            p, pos = prop(pos); props.append(p)
        kids, block = [], pos < end
        while pos < end:
            k, pos = node(pos)
            if k is None: break
            kids.append(k)
        return {'name': name, 'props': props, 'kids': kids, 'block': block}, end

    pos, top = 27, []
    while True:
        n, pos = node(pos)
        if n is None: break
        top.append(n)
    return version, wide, top, b[pos:]


def write_fbx(version, wide, top, footer):
    off_fmt, null_len = ('<QQQ', 25) if wide else ('<III', 13)
    out = bytearray(b'Kaydara FBX Binary  \x00\x1a\x00' + struct.pack('<I', version))

    def prop_bytes(t, v):
        if t in 'SR': return t.encode() + struct.pack('<I', len(v)) + v
        return t.encode() + v

    def node(n):
        start = len(out)
        props = b''.join(prop_bytes(*p) for p in n['props'])
        nm = n['name'].encode()
        out.extend(b'\0' * struct.calcsize(off_fmt) + bytes([len(nm)]) + nm + props)
        if n['block']:
            for k in n['kids']: node(k)
            out.extend(b'\0' * null_len)
        struct.pack_into(off_fmt, out, start, len(out), len(n['props']), len(props))

    for n in top: node(n)
    out.extend(b'\0' * null_len)
    out.extend(footer)
    return bytes(out)


def shrink_image(data, tmp, limit):
    src = os.path.join(tmp, 'in')
    open(src, 'wb').write(data)
    info = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', '-g', 'hasAlpha', src], capture_output=True, text=True).stdout.split()
    w, h = int(info[info.index('pixelWidth:') + 1]), int(info[info.index('pixelHeight:') + 1])
    alpha = info[info.index('hasAlpha:') + 1] == 'yes'
    ext = 'png' if alpha else 'jpg'
    if max(w, h) <= limit and data[:3] == (b'\x89PN' if alpha else b'\xff\xd8\xff'): return data, None  # already done
    dst = os.path.join(tmp, 'out.' + ext)
    cmd = ['sips', '-s', 'format', 'png' if alpha else 'jpeg']
    if not alpha: cmd += ['-s', 'formatOptions', str(JPEG_QUALITY)]
    if max(w, h) > limit: cmd += ['-Z', str(limit)]
    subprocess.run(cmd + [src, '--out', dst], capture_output=True, check=True)
    new = open(dst, 'rb').read()
    return (new, ext) if len(new) < len(data) else (data, None)


def shrink(path):
    b = open(path, 'rb').read()
    version, wide, top, footer = read_fbx(b)
    renames = {}  # old texture file name -> new one, so the loader picks the right image decoder
    with tempfile.TemporaryDirectory() as tmp:
        def walk(n):
            if n['name'] == 'Video':
                kids = {k['name']: k for k in n['kids']}
                content = kids.get('Content')
                if content and content['props'] and content['props'][0][0] == 'R' and len(content['props'][0][1]) > 1024:
                    fn = kids.get('RelativeFilename') or kids.get('Filename')
                    name = fn['props'][0][1].lower() if fn and fn['props'] else b''
                    unused = any(w in name for w in (b'specular', b'gloss', b'roughness', b'metal'))
                    data, ext = shrink_image(content['props'][0][1], tmp, UNUSED_MAX if unused else MAX)
                    if ext:
                        content['props'][0][1] = data
                        for key in ('RelativeFilename', 'Filename'):
                            k = kids.get(key)
                            if k and k['props'] and k['props'][0][0] == 'S':
                                old = k['props'][0][1]
                                renames[old] = old[:old.rfind(b'.') + 1] + ext.encode() if b'.' in old else old
            for k in n['kids']: walk(k)
        for n in top: walk(n)

        def rename(n):
            for p in n['props']:
                if p[0] == 'S' and p[1] in renames: p[1] = renames[p[1]]
            for k in n['kids']: rename(k)
        for n in top: rename(n)
    return b, write_fbx(version, wide, top, footer)


if __name__ == '__main__':
    for path in sys.argv[1:]:
        before, after = shrink(path)
        if len(after) >= len(before): print(f'{path}: already small ({len(before) / 1e6:.1f} MB)'); continue
        keep = os.path.join(os.path.dirname(os.path.abspath(path)) + '-original', os.path.basename(path))
        os.makedirs(os.path.dirname(keep), exist_ok=True)
        if not os.path.exists(keep): shutil.copy2(path, keep)
        open(path, 'wb').write(after)
        print(f'{path}: {len(before) / 1e6:.1f} MB -> {len(after) / 1e6:.1f} MB')
