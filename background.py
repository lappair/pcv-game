"""Latar belakang: foto dari folder images/, atau feed kamera yang diredupkan."""
import os
import cv2
import numpy as np

from config import BG_DIM

IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

_cache = {}     # (nama file, w, h) -> gambar siap pakai, atau None kalau gagal dimuat


def _load(name, w, h):
    key = (name, w, h)
    if key in _cache:
        return _cache[key]
    img = None
    path = os.path.join(IMG_DIR, name)
    raw = cv2.imread(path)
    if raw is None:
        print(f"[background] gagal memuat {path}, memakai kamera")
    else:
        # "cover": perbesar sampai menutup layar, lalu potong bagian tengah (tanpa gepeng)
        ih, iw = raw.shape[:2]
        s = max(w / iw, h / ih)
        nw, nh = int(round(iw * s)), int(round(ih * s))
        interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR
        raw = cv2.resize(raw, (nw, nh), interpolation=interp)
        x0, y0 = (nw - w) // 2, (nh - h) // 2
        img = (raw[y0:y0 + h, x0:x0 + w] * BG_DIM).astype(np.uint8)
    _cache[key] = img
    return img


def make_background(frame, image_name=None):
    """image_name=None memakai kamera. Selalu mengembalikan array baru yang aman digambari."""
    h, w = frame.shape[:2]
    if image_name:
        img = _load(image_name, w, h)
        if img is not None:
            return img.copy()
    return (frame * BG_DIM).astype(np.uint8)