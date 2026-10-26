"""Kalibrasi warna. Pemain menahan benda berwarna di kotak tengah layar; rentang HSV
dihitung dari sampelnya. Hasil disimpan ke calibration.json dan dipakai lagi saat game dibuka."""
import json
import os
import cv2
import numpy as np

from config import *
from hud import draw_trail

FONT = cv2.FONT_HERSHEY_SIMPLEX
SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")


# ---------- logika murni (tanpa kamera) ----------
def box_rect(w, h):
    side = int(CAL_BOX * min(w, h))
    x1, y1 = (w - side) // 2, (h - side) // 2
    return x1, y1, x1 + side, y1 + side


def circ_diff(a, b):
    """Selisih dua hue pada lingkaran 0..179."""
    d = abs(a - b) % 180
    return min(d, 180 - d)


def analyze(hsv_roi):
    """Hitung rentang deteksi dari sampel HSV.
    Mengembalikan (calib atau None, alasan, (hue, s, v) perwakilan atau None)."""
    px = hsv_roi.reshape(-1, 3)
    colored = (px[:, 1] >= CAL_MIN_S) & (px[:, 2] >= CAL_MIN_V)     # buang piksel pudar/gelap
    cover = float(colored.mean()) if len(px) else 0.0
    if cover < CAL_COVER:
        return None, f"kotak belum terisi warna ({int(cover * 100)}%)", None
    px = px[colored]

    # rata-rata hue harus melingkar: hue 2 dan 178 itu bertetangga (merah), bukan rata-rata 90
    h = px[:, 0].astype(np.float64)
    ang = h * (2 * np.pi / 180)
    hc = (np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()) % (2 * np.pi)) * 180 / (2 * np.pi)
    d = np.abs(h - hc)
    d = np.minimum(d, 180 - d)
    spread = float(np.percentile(d, 90))
    s_med, v_med = float(np.median(px[:, 1])), float(np.median(px[:, 2]))
    rep = (int(round(hc)) % 180, s_med, v_med)
    if spread > CAL_H_MAX:
        return None, "warna di kotak tidak seragam", rep

    calib = {"h_center": int(round(hc)) % 180,
             "h_tol": int(round(np.clip(spread + CAL_H_MARGIN, CAL_H_MIN, CAL_H_MAX))),
             "s_min": int(np.clip(s_med - CAL_DS, CAL_S_FLOOR, 255)),
             "v_min": int(np.clip(v_med - CAL_DV, CAL_V_FLOOR, 255))}
    return calib, "ok", rep


def save_calibration(c):
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump(c, f)
    except OSError as ex:
        print("[kalibrasi] gagal menyimpan:", ex)


def load_calibration():
    try:
        with open(SAVE_PATH) as f:
            c = json.load(f)
        ok = (0 <= c["h_center"] <= 179 and 0 <= c["h_tol"] <= 40
              and 0 <= c["s_min"] <= 255 and 0 <= c["v_min"] <= 255)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return c if ok else None


# ---------- layar ----------
class CalibrationScreen:
    def __init__(self, has_saved=False):
        self.has_saved = has_saved
        self.enter(0.0)

    def enter(self, now):
        self.phase = "sample"       # "sample" lalu "confirm"
        self.hold_t0 = None
        self.last_hc = None
        self.prog = 0.0
        self.ready = False
        self.reason = ""
        self.rep = None
        self.calib = None

    def _capture(self, tracker, calib):
        self.calib = calib
        tracker.set_calibration(calib)
        save_calibration(calib)
        self.has_saved = True
        self.phase = "confirm"
        self.hold_t0 = None
        self.prog = 0.0

    def update(self, tracker, hand, now, w, h, key=255):
        """Mengembalikan "done" (lanjut ke menu) atau "skip" (lewati), selain itu None."""
        if self.phase == "confirm":
            if key in (32, 13, 27):
                return "done"
            if key == ord("r"):
                self.enter(now)
            return None

        if key in (13, 27, ord("d")):
            return "skip"
        if tracker.last_hsv is None:
            return None

        x1, y1, x2, y2 = box_rect(w, h)
        calib, self.reason, self.rep = analyze(tracker.last_hsv[y1:y2, x1:x2])
        self.ready = calib is not None
        if not self.ready:
            self.hold_t0 = self.last_hc = None
            self.prog = 0.0
            return None
        if key == 32:                                   # ambil sekarang
            self._capture(tracker, calib)
            return None
        # harus stabil: hue tidak boleh melompat, kalau melompat hitungan menahan mulai lagi
        if (self.hold_t0 is None or self.last_hc is None
                or circ_diff(calib["h_center"], self.last_hc) > 6):
            self.hold_t0 = now
        self.last_hc = calib["h_center"]
        self.prog = (now - self.hold_t0) / CAL_HOLD
        if self.prog >= 1.0:
            self._capture(tracker, calib)
        return None

    # ---------- gambar ----------
    def _text(self, out, txt, cx, cy, scale, col, th=1):
        (tw, th_), _ = cv2.getTextSize(txt, FONT, scale, th)
        cv2.putText(out, txt, (cx - tw // 2, cy + th_ // 2), FONT, scale, col, th, cv2.LINE_AA)

    def _draw_sample(self, out, frame, w, h, k):
        x1, y1, x2, y2 = box_rect(w, h)
        out[y1:y2, x1:x2] = frame[y1:y2, x1:x2]         # isi kotak tetap terang: warna aslinya kelihatan
        col = (80, 255, 120) if self.ready else (0, 160, 255)
        cv2.rectangle(out, (x1, y1), (x2, y2), col, 3)
        # bar progres menahan
        by = y2 + int(8 * k)
        cv2.rectangle(out, (x1, by), (x2, by + int(8 * k)), (255, 255, 255), 1)
        cv2.rectangle(out, (x1, by), (x1 + int((x2 - x1) * min(self.prog, 1.0)), by + int(8 * k)), col, -1)

        cx = w // 2
        self._text(out, "KALIBRASI WARNA", cx, int(h * 0.10), 1.0 * k, (235, 235, 235), 2)
        self._text(out, "pegang benda yang akan jadi pedang di dalam kotak, isi sepenuhnya",
                   cx, int(h * 0.19), 0.5 * k, (200, 200, 200))
        status = "tahan... jangan digerakkan" if self.ready else self.reason
        self._text(out, status, cx, y2 + int(40 * k), 0.6 * k, col, 2)
        if self.rep:                                    # contoh warna yang terbaca
            bgr = cv2.cvtColor(np.uint8([[[self.rep[0], int(self.rep[1]), int(self.rep[2])]]]),
                               cv2.COLOR_HSV2BGR)[0, 0]
            sx = x2 + int(24 * k)
            cv2.rectangle(out, (sx, y1), (sx + int(40 * k), y1 + int(40 * k)), tuple(int(c) for c in bgr), -1)
            cv2.rectangle(out, (sx, y1), (sx + int(40 * k), y1 + int(40 * k)), (255, 255, 255), 1)
            cv2.putText(out, "terbaca", (sx, y1 + int(58 * k)), FONT, 0.45 * k, (200, 200, 200), 1, cv2.LINE_AA)
        last = "warna terakhir" if self.has_saved else "merah bawaan"
        self._text(out, f"SPACE = ambil sekarang   ENTER = lewati (pakai {last})   Q = keluar",
                   cx, int(h * 0.95), 0.45 * k, (170, 170, 170))

    def _draw_confirm(self, out, frame, tracker, hand, w, h, k):
        if tracker.mask is not None:                    # piksel yang terdeteksi menyala hijau
            ov = out.copy()
            ov[tracker.mask > 0] = (80, 255, 120)
            out = cv2.addWeighted(ov, 0.6, out, 0.4, 0)
        draw_trail(out, tracker.trail, False)
        if hand.detected:
            cv2.circle(out, (int(hand.pos[0]), int(hand.pos[1])), 12, (255, 255, 255), 2)
        c = self.calib
        cx = w // 2
        self._text(out, "WARNA TERSIMPAN", cx, int(h * 0.10), 1.0 * k, (80, 255, 120), 2)
        self._text(out, f"hue {c['h_center']} +-{c['h_tol']}   S >= {c['s_min']}   V >= {c['v_min']}",
                   cx, int(h * 0.18), 0.55 * k, (235, 235, 235))
        self._text(out, "gerakkan benda: hanya benda itu yang boleh menyala hijau",
                   cx, int(h * 0.25), 0.5 * k, (200, 200, 200))
        self._text(out, "dan cincin putih harus mengikutinya", cx, int(h * 0.30), 0.5 * k, (200, 200, 200))
        if not hand.detected:
            self._text(out, "benda tidak terdeteksi", cx, int(h * 0.55), 0.7 * k, (0, 160, 255), 2)
        self._text(out, "SPACE / ENTER = lanjut   R = ulangi   Q = keluar", cx, int(h * 0.95), 0.45 * k, (170, 170, 170))
        return out

    def render(self, frame, tracker, hand, now):
        h, w = frame.shape[:2]
        k = w / 640.0
        out = (frame * 0.5).astype(np.uint8)
        if self.phase == "sample":
            self._draw_sample(out, frame, w, h, k)
        else:
            out = self._draw_confirm(out, frame, tracker, hand, w, h, k)
        return out
