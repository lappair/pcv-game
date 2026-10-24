"""Data musuh, pose animasi, dan gambar skeleton."""
import math
import cv2

from config import (STAGES, UNIT_DIV, ENEMY_Y, STRIKE_ANIM, RECOVER_DUR, STAGGER_DUR)

# pose pedang dalam satuan u: (tangan), (ujung pedang), relatif ke pusat kepala
IDLE = ((1.4, 2.6), (1.8, 0.8))
WIND = {"L": ((-1.8, 0.6), (-3.0, -1.4)),
        "R": ((1.8, 0.6), (3.0, -1.4)),
        "T": ((0.8, -0.8), (0.4, -3.0))}
END = {"L": ((1.2, 2.8), (3.0, 3.8)),
       "R": ((-1.2, 2.8), (-3.0, 3.8)),
       "T": ((0.8, 2.8), (0.6, 5.2))}


def make_enemy(stage, w, h, now):
    armor, hp, wd, cmin, cmax = STAGES[stage - 1]
    boss = armor == "B"
    return {"ex": w // 2, "ey": int(h * ENEMY_Y),
            "need": "H" if boss else armor, "boss": boss,
            "hp": hp, "maxhp": hp, "wd": wd, "base_wd": wd,
            "cmin": cmin, "cmax": cmax,
            "state": "intro", "st": now, "idle_dur": 1.0,
            "dirs": [], "cur": "L", "prev": "L", "chain": False,
            "total": 1, "idx": 1, "all_blocked": True,
            "blocked": False, "hit_t": 0.0, "flash_t": 0.0}


def lerp_pose(a, b, f):
    f = max(0.0, min(1.0, f))
    return tuple((a[i][0] + (b[i][0] - a[i][0]) * f,
                  a[i][1] + (b[i][1] - a[i][1]) * f) for i in range(2))


def enemy_pose(e, now):
    s, cur = e["state"], e["cur"]
    el = now - e["st"]
    if s in ("intro", "idle"):
        return IDLE
    if s == "windup":
        p = el / e["wd"]
        start = END[e["prev"]] if e["chain"] else IDLE
        return lerp_pose(start, WIND[cur], p * p * (3 - 2 * p))
    if s == "strike":
        f = el / STRIKE_ANIM
        if e["blocked"]:
            f *= 0.35
        return lerp_pose(WIND[cur], END[cur], f)
    if s == "recover":
        return lerp_pose(END[cur], IDLE, el / RECOVER_DUR)
    if s == "stagger":
        start = lerp_pose(WIND[cur], END[cur], 0.35)
        return lerp_pose(start, IDLE, el / STAGGER_DUR)
    return IDLE


def draw_enemy(out, e, now, h):
    u = h / UNIT_DIV
    ex = e["ex"]
    ey = e["ey"] + int(math.sin(now * 3) * 0.08 * u)
    vuln = e["state"] in ("recover", "stagger")
    hurt = now - e["flash_t"] < 0.1
    col = (255, 255, 255) if hurt else ((80, 220, 255) if vuln else (225, 225, 225))

    # kaki, tulang belakang, rusuk
    cv2.line(out, (ex - int(0.5 * u), ey + int(4 * u)), (ex - int(0.8 * u), ey + int(6 * u)), col, 5)
    cv2.line(out, (ex + int(0.5 * u), ey + int(4 * u)), (ex + int(0.8 * u), ey + int(6 * u)), col, 5)
    cv2.line(out, (ex, ey + int(u)), (ex, ey + int(4 * u)), col, 5)
    for k in range(4):
        yy = ey + int((1.6 + 0.6 * k) * u)
        cv2.line(out, (ex - int(0.8 * u), yy), (ex + int(0.8 * u), yy), col, 4)

    # lengan kiri (diam)
    cv2.line(out, (ex - int(0.9 * u), ey + int(1.5 * u)), (ex - int(1.2 * u), ey + int(3 * u)), col, 5)

    # kepala
    cv2.circle(out, (ex, ey), int(u), col, -1)
    glow = e["state"] == "windup" and (now - e["st"]) > e["wd"] - 0.3
    ecol = (0, 0, 255) if glow else (20, 20, 20)
    cv2.circle(out, (ex - int(0.35 * u), ey), int(0.22 * u), ecol, -1)
    cv2.circle(out, (ex + int(0.35 * u), ey), int(0.22 * u), ecol, -1)

    # armor + petunjuk arah
    bronze = (60, 120, 170)
    if e["need"] == "H":
        cv2.ellipse(out, (ex, ey), (int(1.1 * u), int(1.1 * u)), 0, 180, 360, bronze, -1)
        a = int(1.3 * u)
        y = ey - int(1.5 * u)
        cv2.arrowedLine(out, (ex - a, y), (ex + a, y), (0, 255, 255), 2, tipLength=0.2)
        cv2.arrowedLine(out, (ex + a, y), (ex - a, y), (0, 255, 255), 2, tipLength=0.2)
    elif e["need"] == "V":
        cv2.rectangle(out, (ex - int(0.8 * u), ey + int(1.1 * u)),
                      (ex + int(0.8 * u), ey + int(3.4 * u)), bronze, -1)
        a = int(1.2 * u)
        x = ex - int(1.8 * u)
        cv2.arrowedLine(out, (x, ey + int(0.5 * u)), (x, ey + int(0.5 * u) + 2 * a), (0, 255, 255), 2, tipLength=0.15)
        cv2.arrowedLine(out, (x, ey + int(0.5 * u) + 2 * a), (x, ey + int(0.5 * u)), (0, 255, 255), 2, tipLength=0.15)

    # lengan + pedang
    hand, tip = enemy_pose(e, now)
    hp_ = (ex + int(hand[0] * u), ey + int(hand[1] * u))
    tp_ = (ex + int(tip[0] * u), ey + int(tip[1] * u))
    cv2.line(out, (ex + int(0.9 * u), ey + int(1.5 * u)), hp_, col, 5)
    cv2.line(out, hp_, tp_, (210, 210, 235), 8, cv2.LINE_AA)
    cv2.circle(out, hp_, 8, (90, 90, 200), -1)
