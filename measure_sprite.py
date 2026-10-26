"""Ukur titik acuan sprite musuh dari kanal alpha.

Jalankan dari folder game:   python measure_sprite.py            (semua skeleton*.png di images/)
                             python measure_sprite.py nama.png   (file tertentu)

Hasilnya: sumbu badan, puncak kepala, dan telapak kaki sebagai fraksi ukuran gambar. Kalau berbeda
dari bawaan di config.py, salin barisnya ke SPRITE_ANCHORS di enemy.py. Juga menyimpan gambar
pemeriksa (garis hijau = sumbu, merah = puncak kepala, biru = telapak kaki) ke folder sementara.
Anggapan: badan menghadap depan, tombak di sisi kiri gambar, dan puncak kepala adalah titik
tertinggi di bagian tengah gambar (tombak tidak dihitung)."""
import glob
import os
import sys
import tempfile

import cv2
import numpy as np

from config import SPRITE_AXIS_X, SPRITE_HEAD_TOP, SPRITE_FEET_Y

IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")


def measure(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None or im.ndim != 3 or im.shape[2] != 4:
        return None, "bukan PNG transparan (RGBA)"
    H, W = im.shape[:2]
    m = im[..., 3] > 40
    center = m[:, int(W * 0.38):int(W * 0.70)]                 # pita tengah: kepala, tanpa ujung tombak
    rows = np.nonzero(center.any(axis=1))[0]
    right = m[:, int(W * 0.5):]                                # separuh kanan: kaki, tanpa ujung tombak
    feet_rows = np.nonzero(right.any(axis=1))[0]
    if len(rows) == 0 or len(feet_rows) == 0:
        return None, "gambar kosong"
    head_top, feet_y = int(rows.min()), int(feet_rows.max())
    r = min(H - 1, head_top + int(0.10 * (feet_y - head_top)))  # baris di kepala, untuk sumbu badan
    xs = np.nonzero(m[r, int(W * 0.30):int(W * 0.75)])[0] + int(W * 0.30)
    if len(xs) == 0:
        return None, "kepala tidak ditemukan di tengah gambar"
    axis_x = (int(xs.min()) + int(xs.max())) // 2
    return (im, W, H, axis_x, head_top, feet_y), None


def main():
    names = sys.argv[1:] or [os.path.basename(p) for p in sorted(glob.glob(os.path.join(IMG_DIR, "skeleton*.png")))]
    if not names:
        print("tidak ada skeleton*.png di", IMG_DIR)
        return
    default = (SPRITE_AXIS_X, SPRITE_HEAD_TOP, SPRITE_FEET_Y)
    for n in names:
        path = n if os.path.isabs(n) else os.path.join(IMG_DIR, n)
        res, err = measure(path)
        print(f"\n== {os.path.basename(path)}")
        if err:
            print("   gagal:", err)
            continue
        im, W, H, ax, ht, fy = res
        a = (round(ax / W, 4), round(ht / H, 4), round(fy / H, 4))
        print(f"   ukuran {W}x{H} | sumbu x {ax}px, puncak kepala y {ht}px, telapak kaki y {fy}px")
        same = all(abs(x - d) < 0.01 for x, d in zip(a, default))
        if same:
            print(f"   {a} sama dengan bawaan di config -> tidak perlu diubah")
        else:
            print(f"   {a} BERBEDA dari bawaan {default}. Tambahkan ke SPRITE_ANCHORS di enemy.py:")
            print(f'   "{os.path.basename(path)}": {a},')
        vis = cv2.cvtColor(im, cv2.COLOR_BGRA2BGR).copy()
        vis[im[..., 3] < 40] = (60, 60, 60)
        cv2.line(vis, (ax, 0), (ax, H), (0, 255, 0), 2)
        cv2.line(vis, (0, ht), (W, ht), (0, 0, 255), 2)
        cv2.line(vis, (0, fy), (W, fy), (255, 0, 0), 2)
        out = os.path.join(tempfile.gettempdir(), "anchor_check_" + os.path.basename(path))
        cv2.imwrite(out, vis)
        print("   gambar pemeriksa:", out)


if __name__ == "__main__":
    main()