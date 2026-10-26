"""Semua gambar ke layar: musuh, zona block, trail, HUD, banner."""
import random
import cv2
import numpy as np

from config import *
from background import make_background
from enemy import draw_enemy
from game import zone_center, in_zone

FONT = cv2.FONT_HERSHEY_SIMPLEX
GRAY = (130, 130, 130)


def _draw_block_zone(out, g, hand, now, w, h):
    e = g["enemy"]
    cx, cy = zone_center(e["cur"], w, h)
    r = int(BLOCK_R * h)
    inside = hand.detected and in_zone(e["cur"], hand.pos, w, h) and not g["exh"]
    if g["exh"]:
        zc = GRAY
    else:
        zc = (80, 255, 120) if inside else (0, 160, 255)
    ov = out.copy()
    cv2.circle(ov, (cx, cy), r, zc, -1)
    out = cv2.addWeighted(ov, 0.35, out, 0.65, 0)
    cv2.circle(out, (cx, cy), r, zc, 3, cv2.LINE_AA)
    (tw, _), _ = cv2.getTextSize("BLOCK", FONT, 0.6, 2)
    cv2.putText(out, "BLOCK", (cx - tw // 2, cy + 6), FONT, 0.6, zc, 2)
    cv2.putText(out, f"{e['idx']}/{e['total']}", (cx - 18, cy + 28), FONT, 0.6, zc, 2)
    return out


def _apply_shake(out, g, now):
    age = now - g["shake_t"]
    if age < 0 or age >= SHAKE_DUR:
        return out
    h, w = out.shape[:2]
    amp = SHAKE_AMP * w * (1 - age / SHAKE_DUR) ** 2
    M = np.float32([[1, 0, random.uniform(-amp, amp)],
                    [0, 1, random.uniform(-amp, amp)]])
    return cv2.warpAffine(out, M, (w, h), borderMode=cv2.BORDER_REPLICATE)


def _draw_fx_text(out, g, now):
    g["fx"] = [f for f in g["fx"] if now - f[2] < 0.6]
    for x, y, t, txt, col in g["fx"]:
        rise = int((now - t) * 50)
        cv2.putText(out, txt, (x, y - rise), FONT, 0.9, col, 2)


def draw_trail(out, trail, exh):
    n = len(trail)
    color = GRAY if exh else (255, 255, 255)
    for i in range(1, n):
        if trail[i - 1] is None or trail[i] is None:
            continue
        k = i / n
        cv2.line(out, trail[i - 1], trail[i], color, max(1, int(k * 12)), cv2.LINE_AA)


def _draw_hand_ring(out, g, hand):
    if not hand.detected:
        return
    ring = GRAY if g["exh"] else ((80, 80, 255) if hand.slashing else (255, 255, 255))
    cv2.circle(out, (int(hand.pos[0]), int(hand.pos[1])), 10, ring, 2)


def _draw_bars(out, g, w):
    e = g["enemy"]
    # HP pemain
    cv2.rectangle(out, (10, 10), (10 + 2 * max(g["hp"], 0), 24), (80, 255, 120), -1)
    cv2.rectangle(out, (10, 10), (10 + 2 * MAX_HP, 24), (255, 255, 255), 1)
    # stamina
    sw = int(2 * MAX_HP * max(g["stam"], 0) / MAX_STAM)
    scol = (60, 60, 230) if g["exh"] else (255, 200, 80)
    cv2.rectangle(out, (10, 30), (10 + sw, 40), scol, -1)
    cv2.rectangle(out, (10, 30), (10 + 2 * MAX_HP, 40), (255, 255, 255), 1)
    if g["exh"]:
        cv2.putText(out, "EXHAUSTED", (10 + 2 * MAX_HP + 10, 40), FONT, 0.6, (80, 80, 255), 2)
    # HP musuh
    ebw = 200
    frac = max(e["hp"], 0) / e["maxhp"]
    cv2.rectangle(out, (w - 10 - int(ebw * frac), 10), (w - 10, 24), (80, 80, 255), -1)
    cv2.rectangle(out, (w - 10 - ebw, 10), (w - 10, 24), (255, 255, 255), 1)
    cv2.putText(out, f"Stage {g['stage']}/{TOTAL_STAGES}", (10, 70), FONT, 0.8, (255, 255, 255), 2)


def _draw_banners(out, g, w, h):
    def center_text(txt, dy, scale, col, th):
        (tw, _), _ = cv2.getTextSize(txt, FONT, scale, th)
        cv2.putText(out, txt, ((w - tw) // 2, h // 2 + dy), FONT, scale, col, th)

    if g["state"] == "clear":
        center_text(f"STAGE {g['stage']} CLEAR", 0, 1.2, (80, 255, 120), 3)
    elif g["state"] == "dead":
        center_text("YOU DIED", -10, 1.5, (80, 80, 255), 3)
        center_text(f"Stage {g['stage']}", 30, 0.8, (255, 255, 255), 2)
        center_text("SPACE = ulang, M = menu, Q = keluar", 65, 0.6, (255, 255, 255), 1)
    elif g["state"] == "win":
        center_text("YOU ESCAPED THE CRYPT", -10, 1.2, (80, 255, 255), 3)
        center_text(f"HP sisa {g['hp']}", 30, 0.8, (255, 255, 255), 2)
        center_text("SPACE = main lagi, M = menu, Q = keluar", 65, 0.6, (255, 255, 255), 1)


def render(frame, g, hand, trail, now):
    """Gabungkan semua lapisan, kembalikan frame siap tampil."""
    h, w = frame.shape[:2]
    out = make_background(frame, GAME_BG)
    e = g["enemy"]

    if g["state"] in ("play", "clear"):
        draw_enemy(out, e, now, h)
    if g["state"] == "play" and e["state"] == "windup":
        out = _draw_block_zone(out, g, hand, now, w, h)

    _draw_fx_text(out, g, now)
    out = _apply_shake(out, g, now)      # dunia bergetar; trail, HUD, dan flash tidak
    draw_trail(out, trail, g["exh"])
    _draw_hand_ring(out, g, hand)

    if now - g["flash"] < 0.2:
        cv2.rectangle(out, (0, 0), (w - 1, h - 1), (0, 0, 255), 8)

    _draw_bars(out, g, w)
    _draw_banners(out, g, w, h)
    return out