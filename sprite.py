import os
import cv2
import numpy as np

IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

_raw = {}       # nama -> BGRA premultiplied (ukuran asli), atau None kalau gagal
_scaled = {}    # (nama, skala) -> BGRA premultiplied terskala


def load_rgba(name):
    if name in _raw:
        return _raw[name]
    path = os.path.join(IMG_DIR, name)
    img = None
    if not os.path.isfile(path):
        print(f"[sprite] file tidak ada: {path} -> memakai gambar garis")
    else:
        raw = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if raw is None or raw.ndim != 3 or raw.shape[2] != 4:
            print(f"[sprite] {path} harus PNG transparan (RGBA) -> memakai gambar garis")
        else:
            a = raw[..., 3:4].astype(np.float32) / 255.0
            pm = raw.copy()
            pm[..., :3] = (raw[..., :3].astype(np.float32) * a + 0.5).astype(np.uint8)
            img = pm
    _raw[name] = img
    return img


def scaled(name, scale):
    key = (name, round(scale, 3))
    if key in _scaled:
        return _scaled[key]
    img = load_rgba(name)
    out = None
    if img is not None:
        h, w = img.shape[:2]
        nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
        interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
        out = cv2.resize(img, (nw, nh), interpolation=interp)
    _scaled[key] = out
    return out


def blit(out, base, pivot_src, pivot_dst, sx, sy, angle, tints=()):
    """Tempel `base` ke `out`.
    pivot_src: titik di gambar yang dijadikan poros (px, py); pivot_dst: posisinya di layar.
    sx, sy: skala (sx negatif = cermin); angle: derajat, positif = berlawanan arah jarum jam.
    tints: daftar ((b, g, r), k): campur warna ke gambar sebesar k (0..1)."""
    if abs(sx) < 1e-3 or abs(sy) < 1e-3:
        return
    th = np.deg2rad(angle)
    c, s = np.cos(th), np.sin(th)
    A = np.array([[c, s], [-s, c]]) @ np.diag([sx, sy])      # konvensi cv2.getRotationMatrix2D
    t = np.asarray(pivot_dst, float) - A @ np.asarray(pivot_src, float)

    bh, bw = base.shape[:2]
    corners = np.array([[0, 0], [bw, 0], [bw, bh], [0, bh]], float)
    dst = corners @ A.T + t
    H, W = out.shape[:2]
    x0, y0 = max(0, int(np.floor(dst[:, 0].min()))), max(0, int(np.floor(dst[:, 1].min())))
    x1, y1 = min(W, int(np.ceil(dst[:, 0].max()))), min(H, int(np.ceil(dst[:, 1].max())))
    if x1 <= x0 or y1 <= y0:
        return

    M = np.hstack([A, (t - [x0, y0]).reshape(2, 1)]).astype(np.float32)
    warped = cv2.warpAffine(base, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    a = warped[..., 3:4].astype(np.float32) / 255.0
    rgb = warped[..., :3].astype(np.float32)
    for color, k in tints:
        if k > 0:
            rgb = rgb * (1 - k) + np.array(color, np.float32) * a * k
    roi = out[y0:y1, x0:x1].astype(np.float32)
    out[y0:y1, x0:x1] = np.clip(roi * (1 - a) + rgb, 0, 255).astype(np.uint8)