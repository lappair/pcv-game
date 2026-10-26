"""Data musuh, pose animasi, dan gambar musuh (sprite sendiri atau skeleton garis)."""
import math
import cv2

from config import *
import sprite

# ---------- pose gambar garis: (tangan), (ujung pedang), relatif ke pusat kepala, satuan u ----------
IDLE = ((1.4, 2.6), (1.8, 0.8))
WIND = {"L": ((-1.8, 0.6), (-3.0, -1.4)),
        "R": ((1.8, 0.6), (3.0, -1.4)),
        "T": ((0.8, -0.8), (0.4, -3.0))}
END = {"L": ((1.2, 2.8), (3.0, 3.8)),
       "R": ((-1.2, 2.8), (-3.0, 3.8)),
       "T": ((0.8, 2.8), (0.6, 5.2))}

# ---------- pose sprite: (sudut derajat, skala, dx dalam u, dy dalam u, regang vertikal) ----------
# Ditulis untuk sprite menghadap normal (tombak di kiri layar). Saat berbalik, sudut dan dx
# dikali facing (+1 / -1), jadi serangan dari kanan otomatis mencerminkan serangan dari kiri.
SP_IDLE = (0.0, 1.0, 0.0, 0.0, 1.0)
SP_WIND = {"S": (16.0, 0.95, -0.25, 0.05, 1.0),     # samping: miring ke arah tombak, menarik diri
           "T": (-4.0, 1.00, 0.00, -0.10, 1.04)}    # atas: naik sedikit dan meregang
SP_END = {"S": (-24.0, 1.22, 0.45, 0.30, 1.0),      # samping: menyapu menyilang, maju ke kamera
          "T": (0.0, 1.28, 0.00, 0.55, 0.92)}       # atas: menukik ke bawah, memendek

VULN_COLOR = (80, 220, 255)     # BGR, penanda musuh bisa dipukul 2x

# Gambar musuh menurut jenis armornya (kunci = e["need"]; file di folder images/).
# Boss berganti gambar tiap armornya berganti (helm <-> chestplate).
SPRITE_FILES = {None: "skeleton.png",
                "H": "skeleton_helmet.png",
                "V": "skeleton_chestplate.png"}
# Titik acuan per file kalau berbeda dari bawaan di config:
# nama file: (sumbu badan x, puncak kepala y, telapak kaki y), semuanya fraksi ukuran gambar.
# Ukur dengan: python measure_sprite.py
SPRITE_ANCHORS = {}


def sprite_anchors(name):
    return SPRITE_ANCHORS.get(name, (SPRITE_AXIS_X, SPRITE_HEAD_TOP, SPRITE_FEET_Y))


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
            "blocked": False, "hit_t": 0.0, "flash_t": 0.0,
            "face_from": 1.0, "face_to": 1.0, "face_t0": 0.0}


def lerp_pose(a, b, f):
    f = max(0.0, min(1.0, f))
    return tuple((a[i][0] + (b[i][0] - a[i][0]) * f,
                  a[i][1] + (b[i][1] - a[i][1]) * f) for i in range(2))


def lerp_params(a, b, f):
    f = max(0.0, min(1.0, f))
    return tuple(x + (y - x) * f for x, y in zip(a, b))


def _smooth(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


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


# ---------- sprite: arah hadap dan parameter pose ----------
def current_face(e, now):
    """+1 = hadap normal (tombak di kiri), -1 = dicerminkan; berubah halus saat berbalik."""
    p = _smooth((now - e["face_t0"]) / FACE_TURN_DUR)
    return e["face_from"] + (e["face_to"] - e["face_from"]) * p


def set_facing(e, now):
    """Dipanggil game saat windup dimulai: serangan dari kiri/kanan menentukan arah hadap."""
    target = e["face_to"]
    if e["cur"] == "L":
        target = 1.0
    elif e["cur"] == "R":
        target = -1.0
    if target != e["face_to"]:
        e["face_from"] = current_face(e, now)
        e["face_to"] = target
        e["face_t0"] = now


def _kind(d):
    return "T" if d == "T" else "S"


def sprite_params(e, now):
    s, k = e["state"], _kind(e["cur"])
    el = now - e["st"]
    if s in ("intro", "idle"):
        return SP_IDLE
    if s == "windup":
        start = SP_END[_kind(e["prev"])] if e["chain"] else SP_IDLE
        return lerp_params(start, SP_WIND[k], _smooth(el / e["wd"]))
    if s == "strike":
        f = min(1.0, el / STRIKE_ANIM)
        if e["blocked"]:
            f *= 0.35
        return lerp_params(SP_WIND[k], SP_END[k], 1 - (1 - f) ** 2)     # ease-out: awal cepat
    if s == "recover":
        return lerp_params(SP_END[k], SP_IDLE, _smooth(el / RECOVER_DUR))
    if s == "stagger":
        start = lerp_params(SP_WIND[k], SP_END[k], 0.35)
        return lerp_params(start, SP_IDLE, _smooth(el / STAGGER_DUR))
    return SP_IDLE


def _draw_hints(out, e, ex, ey, u, vx):
    """Panah petunjuk arah tebasan: horizontal di atas kepala (helm), vertikal di samping (chestplate)."""
    if e["need"] == "H":
        a = int(1.3 * u)
        y = ey - int(1.5 * u)
        cv2.arrowedLine(out, (ex - a, y), (ex + a, y), (0, 255, 255), 2, tipLength=0.2)
        cv2.arrowedLine(out, (ex + a, y), (ex - a, y), (0, 255, 255), 2, tipLength=0.2)
    elif e["need"] == "V":
        a = int(1.2 * u)
        y0 = ey + int(0.5 * u)
        cv2.arrowedLine(out, (vx, y0), (vx, y0 + 2 * a), (0, 255, 255), 2, tipLength=0.15)
        cv2.arrowedLine(out, (vx, y0 + 2 * a), (vx, y0), (0, 255, 255), 2, tipLength=0.15)


def draw_enemy_sprite(out, e, now, h):
    """Gambar musuh dari sprite. Mengembalikan False kalau gambarnya tidak tersedia."""
    name = SPRITE_FILES.get(e["need"])
    if not name:
        return False
    src = sprite.load_rgba(name)
    if src is None:
        return False
    u = h / UNIT_DIV
    axis_x, head_top, feet_y = sprite_anchors(name)
    ih = src.shape[0]
    # tinggi puncak kepala -> telapak kaki di layar = 7u, sama dengan skeleton garis,
    # berapa pun ukuran gambarnya
    scale = 7.0 * u / ((feet_y - head_top) * ih)
    base = sprite.scaled(name, scale)
    bh, bw = base.shape[:2]
    pivot_src = (axis_x * bw, feet_y * bh)

    ang, sc, dx, dy, sy = sprite_params(e, now)
    face = current_face(e, now)
    el = now - e["st"]

    bob = math.sin(now * 3) * 0.08                              # napas, dalam u
    sc *= 1.0 + 0.012 * math.sin(now * 3)
    hurt_age = now - e["flash_t"]
    shake = math.sin(now * 90) * 0.12 * (1 - hurt_age / 0.15) if hurt_age < 0.15 else 0.0
    px = e["ex"] + (dx * face + shake) * u
    py = e["ey"] + (6.0 + SPRITE_DY + dy + bob) * u

    tints = []
    if e["state"] in ("recover", "stagger"):
        tints.append((VULN_COLOR, 0.30))
    if e["state"] == "windup" and el > e["wd"] - 0.3:           # peringatan menjelang pukulan
        pulse = 0.5 + 0.5 * math.sin(now * 30)
        tints.append(((0, 0, 255), 0.15 + 0.25 * pulse))
    if hurt_age < 0.1:
        tints.append(((255, 255, 255), 0.85))

    sprite.blit(out, base, pivot_src, (px, py), sc * face, sc * sy, ang * face, tints)
    _draw_hints(out, e, e["ex"], e["ey"], u, e["ex"] + int(2.4 * u))
    return True


def draw_enemy(out, e, now, h):
    # pakai gambar sendiri kalau tersedia; kalau file-nya tidak ada, jatuh ke skeleton garis
    if draw_enemy_sprite(out, e, now, h):
        return

    u = h / UNIT_DIV
    ex = e["ex"]
    ey = e["ey"] + int(math.sin(now * 3) * 0.08 * u)
    vuln = e["state"] in ("recover", "stagger")
    hurt = now - e["flash_t"] < 0.1
    col = (255, 255, 255) if hurt else (VULN_COLOR if vuln else (225, 225, 225))

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

    # armor
    bronze = (60, 120, 170)
    if e["need"] == "H":
        cv2.ellipse(out, (ex, ey), (int(1.1 * u), int(1.1 * u)), 0, 180, 360, bronze, -1)
    elif e["need"] == "V":
        cv2.rectangle(out, (ex - int(0.8 * u), ey + int(1.1 * u)),
                      (ex + int(0.8 * u), ey + int(3.4 * u)), bronze, -1)
    _draw_hints(out, e, ex, ey, u, ex - int(1.8 * u))

    # lengan + pedang
    hand, tip = enemy_pose(e, now)
    hp_ = (ex + int(hand[0] * u), ey + int(hand[1] * u))
    tp_ = (ex + int(tip[0] * u), ey + int(tip[1] * u))
    cv2.line(out, (ex + int(0.9 * u), ey + int(1.5 * u)), hp_, col, 5)
    cv2.line(out, hp_, tp_, (210, 210, 235), 8, cv2.LINE_AA)
    cv2.circle(out, hp_, 8, (90, 90, 200), -1)