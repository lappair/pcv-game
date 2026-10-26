"""Aturan game: state, stamina, state machine musuh, tebasan, progres stage.
Tidak ada kode gambar di sini."""
import time
import random
import numpy as np

from config import *
from enemy import make_enemy, set_facing
from vision import seg_dist


# ---------- zona block ----------
def zone_center(z, w, h):
    return (int(ZONE_C[z][0] * w), int(ZONE_C[z][1] * h))


def in_zone(z, p, w, h):
    cx, cy = zone_center(z, w, h)
    r = BLOCK_R * h
    return (p[0] - cx) ** 2 + (p[1] - cy) ** 2 <= r * r


# ---------- state ----------
def new_game(w, h):
    now = time.time()
    return {"stage": 1, "hp": MAX_HP, "kills": 0, "state": "play",
            "enemy": make_enemy(1, w, h, now), "banner_t": 0.0,
            "flash": 0.0, "shake_t": 0.0, "fx": [], "events": [],
            "stam": float(MAX_STAM), "exh": False, "stam_t": 0.0, "last": now,
            "zone_t": {"L": 0.0, "R": 0.0, "T": 0.0}}


def spend(g, amt, now):
    if amt <= 0:            # biaya 0: jangan tunda regenerasi stamina
        return
    g["stam"] = max(0.0, g["stam"] - amt)
    g["stam_t"] = now


def emit(g, name):
    """Catat kejadian untuk suara. Diputar oleh main.py lewat sound.play_events."""
    g["events"].append(name)


def update_stamina(g, now):
    fdt = now - g["last"]
    g["last"] = now
    if g["stam"] <= 0:
        g["exh"] = True
    elif g["exh"] and g["stam"] >= EXH_RECOVER:
        g["exh"] = False
    if now - g["stam_t"] > STAM_DELAY:
        g["stam"] = min(float(MAX_STAM), g["stam"] + STAM_REGEN * fdt)


def track_zones(g, hand, now, w, h):
    """Catat kapan terakhir tangan ada di tiap zona block."""
    if hand.detected:
        for z in g["zone_t"]:
            if in_zone(z, hand.pos, w, h):
                g["zone_t"][z] = now


# ---------- musuh ----------
def _go_idle(e, now):
    e["state"], e["st"] = "idle", now
    e["idle_dur"] = random.uniform(IDLE_MIN, IDLE_MAX)


def update_enemy(g, hand, now, w, h):
    e = g["enemy"]
    el = now - e["st"]
    st = e["state"]

    if st == "intro" and el > INTRO_DUR:
        _go_idle(e, now)

    elif st == "idle" and el >= e["idle_dur"]:
        n = random.randint(e["cmin"], e["cmax"])
        e["dirs"] = [random.choice("LRT") for _ in range(n)]
        e["total"], e["idx"] = n, 1
        e["cur"] = e["dirs"].pop(0)
        e["wd"] = e["base_wd"]
        e["chain"] = False
        e["all_blocked"] = True
        set_facing(e, now)
        e["state"], e["st"] = "windup", now

    elif st == "windup" and el >= e["wd"]:
        e["blocked"] = ((not g["exh"]) and hand.detected
                        and (now - g["zone_t"][e["cur"]] <= BLOCK_GRACE))
        if e["blocked"]:
            spend(g, BLOCK_COST, now)
            emit(g, "block")
            g["shake_t"] = now
            g["fx"].append((w // 2 - 50, int(h * 0.12), now, "BLOCKED", (80, 255, 120)))
        else:
            e["all_blocked"] = False
            g["hp"] -= ENEMY_DMG
            g["flash"] = now
            emit(g, "takedamage")
            g["fx"].append((w // 2 - 35, int(h * 0.12), now, "OUCH", (80, 80, 255)))
        e["state"], e["st"] = "strike", now

    elif st == "strike" and el >= STRIKE_DUR:
        if e["dirs"]:
            e["prev"] = e["cur"]
            e["cur"] = e["dirs"].pop(0)
            e["idx"] += 1
            e["wd"] = max(MIN_WD, e["base_wd"] * COMBO_WD_MULT)
            e["chain"] = True
            set_facing(e, now)
            e["state"], e["st"] = "windup", now
        elif e["all_blocked"]:
            e["state"], e["st"] = "stagger", now
        else:
            e["state"], e["st"] = "recover", now

    elif st == "recover" and el >= RECOVER_DUR:
        _go_idle(e, now)

    elif st == "stagger" and el >= STAGGER_DUR:
        _go_idle(e, now)


# ---------- tebasan pemain ----------
def resolve_slash(g, hand, now, h):
    e = g["enemy"]
    u = h / UNIT_DIV
    can_attack = e["state"] in ("idle", "recover", "stagger")   # tidak saat musuh menyerang
    if not (hand.slashing and can_attack and not g["exh"] and now - e["hit_t"] > HIT_COOLDOWN):
        return

    c = np.array([e["ex"], e["ey"] + 2.0 * u])
    if seg_dist(c, hand.p0, hand.p1) > 2.4 * u:
        return

    spend(g, SWING_COST, now)
    e["hit_t"] = now
    d = hand.d
    if e["need"] == "H":
        valid = abs(d[0]) >= DIR_TOL
    elif e["need"] == "V":
        valid = abs(d[1]) >= DIR_TOL
    else:
        valid = True

    fx_pos = (e["ex"] - 30, e["ey"] - int(1.4 * u))
    if valid:
        vuln = e["state"] in ("recover", "stagger")
        e["hp"] -= 2 if vuln else 1
        e["flash_t"] = now
        emit(g, "slash")
        g["fx"].append((*fx_pos, now, "CRIT" if vuln else "HIT",
                        (80, 220, 255) if vuln else (80, 255, 120)))
        if e["boss"]:
            e["need"] = "V" if e["need"] == "H" else "H"
    else:
        emit(g, "block")
        g["fx"].append((*fx_pos, now, "CLANG", (80, 80, 255)))


# ---------- progres ----------
def check_progress(g, now):
    e = g["enemy"]
    if g["hp"] <= 0:
        g["state"] = "dead"
        emit(g, "lose")
    elif e["hp"] <= 0:
        g["kills"] += 1
        emit(g, "enemydead")
        if g["stage"] >= TOTAL_STAGES:
            g["state"] = "win"
        else:
            g["state"] = "clear"
            g["banner_t"] = now


def advance_stage(g, now, w, h):
    if now - g["banner_t"] > 1.8:
        g["stage"] += 1
        g["enemy"] = make_enemy(g["stage"], w, h, now)
        g["stam"] = float(MAX_STAM)
        g["exh"] = False
        g["state"] = "play"


def step(g, hand, now, w, h):
    """Satu tick logika game. Dipanggil sekali per frame dari main."""
    track_zones(g, hand, now, w, h)
    update_stamina(g, now)
    if g["state"] == "play":
        update_enemy(g, hand, now, w, h)
        resolve_slash(g, hand, now, h)
        check_progress(g, now)
    elif g["state"] == "clear":
        advance_stage(g, now, w, h)