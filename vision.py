"""Deteksi warna (bisa dikalibrasi), smoothing, trail, dan deteksi tebasan."""
import cv2
import numpy as np
from collections import deque

from config import (TRAIL_LEN, MIN_AREA, SMOOTH, SLASH_SPEED,
                    S_MIN_DEFAULT, V_MIN_DEFAULT, H_CENTER_DEFAULT, H_TOL_DEFAULT)


class Hand:
    """Hasil satu frame: posisi benda dan tebasan (kalau ada)."""

    def __init__(self):
        self.detected = False
        self.pos = None         # np.array([x, y]) yang sudah di-smooth
        self.slashing = False
        self.p0 = None          # posisi frame sebelumnya
        self.p1 = None          # posisi sekarang
        self.d = None           # arah tebasan (vektor satuan)


def seg_dist(c, p0, p1):
    """Jarak titik c ke segmen p0-p1."""
    d = p1 - p0
    L2 = float(d @ d)
    if L2 < 1e-6:
        return float(np.linalg.norm(c - p0))
    t = np.clip(((c - p0) @ d) / L2, 0.0, 1.0)
    return float(np.linalg.norm(c - (p0 + t * d)))


def hue_mask(hsv, hc, tol, smin, vmin):
    """Piksel dengan hue dalam hc +- tol (melingkar: 0 dan 179 bersebelahan), S >= smin, V >= vmin."""
    lo, hi = hc - tol, hc + tol

    def rng(a, b):
        return cv2.inRange(hsv, np.array([a, smin, vmin]), np.array([b, 255, 255]))

    if lo < 0:                      # melewati batas bawah: [0, hi] dan [180+lo, 179]
        return cv2.bitwise_or(rng(0, hi), rng(180 + lo, 179))
    if hi > 179:                    # melewati batas atas: [lo, 179] dan [0, hi-180]
        return cv2.bitwise_or(rng(lo, 179), rng(0, hi - 180))
    return rng(lo, hi)


class ColorTracker:
    def __init__(self):
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        cv2.namedWindow("mask")
        cv2.createTrackbar("H_center", "mask", H_CENTER_DEFAULT, 179, lambda x: None)
        cv2.createTrackbar("H_tol", "mask", H_TOL_DEFAULT, 40, lambda x: None)
        cv2.createTrackbar("S_min", "mask", S_MIN_DEFAULT, 255, lambda x: None)
        cv2.createTrackbar("V_min", "mask", V_MIN_DEFAULT, 255, lambda x: None)
        self.trail = deque(maxlen=TRAIL_LEN)
        self.mask = None        # mask frame terakhir (untuk layar kalibrasi)
        self.last_hsv = None    # HSV frame terakhir (untuk mengambil sampel warna)
        self.reset()

    def reset(self):
        self.trail.clear()
        self.pos = None
        self.prev_pos = None
        self.prev_t = None

    def params(self):
        return (cv2.getTrackbarPos("H_center", "mask"), cv2.getTrackbarPos("H_tol", "mask"),
                cv2.getTrackbarPos("S_min", "mask"), cv2.getTrackbarPos("V_min", "mask"))

    def set_calibration(self, c):
        """c: dict h_center, h_tol, s_min, v_min. Trackbar tetap bisa digeser manual sesudahnya."""
        for name, key in (("H_center", "h_center"), ("H_tol", "h_tol"),
                          ("S_min", "s_min"), ("V_min", "v_min")):
            cv2.setTrackbarPos(name, "mask", int(c[key]))
        self.reset()

    def _mask(self, frame):
        blur = cv2.GaussianBlur(frame, (5, 5), 0)
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
        self.last_hsv = hsv
        hc, tol, s, v = self.params()
        mask = hue_mask(hsv, hc, tol, s, v)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel, iterations=2)
        return mask

    def update(self, frame, now):
        mask = self._mask(frame)
        self.mask = mask
        cv2.imshow("mask", mask)

        hand = Hand()
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            if cv2.contourArea(c) > MIN_AREA:
                M = cv2.moments(c)
                new = np.array([M["m10"] / M["m00"], M["m01"] / M["m00"]])
                self.pos = new if self.pos is None else SMOOTH * self.pos + (1 - SMOOTH) * new
                hand.detected = True
        if not hand.detected:
            self.pos = None

        if hand.detected and self.prev_pos is not None and self.prev_t is not None:
            dt = max(now - self.prev_t, 1e-3)
            move = self.pos - self.prev_pos
            dist = float(np.linalg.norm(move))
            if dist / dt > SLASH_SPEED and dist > 1e-6:
                hand.slashing = True
                hand.p0, hand.p1 = self.prev_pos, self.pos
                hand.d = move / dist

        hand.pos = self.pos
        self.prev_pos = self.pos.copy() if hand.detected else None
        self.prev_t = now
        self.trail.append((int(self.pos[0]), int(self.pos[1])) if hand.detected else None)
        return hand


RedTracker = ColorTracker       # nama lama, supaya kode yang masih memakainya tidak rusak
