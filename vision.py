"""Deteksi warna merah, smoothing, trail, dan deteksi tebasan."""
import cv2
import numpy as np
from collections import deque

from config import (TRAIL_LEN, MIN_AREA, SMOOTH, SLASH_SPEED,
                    S_MIN_DEFAULT, V_MIN_DEFAULT)


class Hand:
    """Hasil satu frame: posisi tangan dan tebasan (kalau ada)."""

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


class RedTracker:
    def __init__(self):
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        cv2.namedWindow("mask")
        cv2.createTrackbar("S_min", "mask", S_MIN_DEFAULT, 255, lambda x: None)
        cv2.createTrackbar("V_min", "mask", V_MIN_DEFAULT, 255, lambda x: None)
        self.trail = deque(maxlen=TRAIL_LEN)
        self.reset()

    def reset(self):
        self.trail.clear()
        self.pos = None
        self.prev_pos = None
        self.prev_t = None

    def _mask(self, frame):
        blur = cv2.GaussianBlur(frame, (5, 5), 0)
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
        s = cv2.getTrackbarPos("S_min", "mask")
        v = cv2.getTrackbarPos("V_min", "mask")
        m1 = cv2.inRange(hsv, np.array([0, s, v]), np.array([10, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([170, s, v]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(m1, m2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel, iterations=2)
        return mask

    def update(self, frame, now):
        mask = self._mask(frame)
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
