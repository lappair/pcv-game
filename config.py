"""Semua angka tuning ada di sini. File ini tidak meng-import apa-apa."""

# ---------- game ----------
TOTAL_STAGES = 5
MAX_HP = 100
ENEMY_DMG = 15

# ---------- deteksi warna ----------
TRAIL_LEN = 25
MIN_AREA = 800          # luas kontur minimum
SMOOTH = 0.5            # 0 = tanpa smoothing, makin besar makin halus tapi lag
S_MIN_DEFAULT = 80
V_MIN_DEFAULT = 50

# ---------- tebasan ----------
SLASH_SPEED = 700       # px/detik, di bawah ini bukan tebasan
DIR_TOL = 0.8           # cos toleransi arah
HIT_COOLDOWN = 0.5      # jeda antar tebasan yang menyentuh musuh
BLOCK_GRACE = 0.2       # detik, toleransi latensi untuk block

# ---------- zona block (lingkaran) ----------
BLOCK_R = 0.12          # radius, fraksi tinggi layar
ZONE_C = {"L": (0.15, 0.55),    # pusat zona, fraksi (w, h)
          "R": (0.85, 0.55),
          "T": (0.50, 0.12)}

# ---------- background ----------
# nama file di folder images/ (di sebelah main.py), atau None untuk memakai kamera
MENU_BG = "menu_bg.jpg"
GAME_BG = "menu_bg.jpg"
BG_DIM = 0.5            # 1.0 = terang penuh; turunkan kalau musuh/UI sulit dibaca

# ---------- menu ----------
MENU_DWELL = 1.0        # detik menahan tangan di tombol untuk memilih

# ---------- screen shake saat block berhasil ----------
SHAKE_AMP = 0.015       # amplitudo awal, fraksi lebar layar (0.015 = ~10 px di 640)
SHAKE_DUR = 0.25        # detik

# ---------- stamina ----------
MAX_STAM = 100
SWING_COST = 20
BLOCK_COST = 0
STAM_REGEN = 22
STAM_DELAY = 0.6
EXH_RECOVER = 35

# ---------- musuh: ukuran ----------
UNIT_DIV = 9.0          # u = h / UNIT_DIV
ENEMY_Y = 0.22          # posisi kepala, fraksi tinggi layar

# ---------- musuh: timing ----------
INTRO_DUR = 1.0
IDLE_MIN, IDLE_MAX = 0.6, 1.2
COMBO_WD_MULT = 0.9     # windup pukulan lanjutan = base_wd * ini
MIN_WD = 0.40           # windup tidak boleh lebih cepat dari ini
STRIKE_DUR = 0.18       # lama fase strike sebelum lanjut
STRIKE_ANIM = 0.12      # kecepatan animasi ayunan (visual saja)
RECOVER_DUR = 0.7
STAGGER_DUR = 1.0

# per stage: (armor, hp, windup, min pukulan, maks pukulan)
# armor: None polos, "H" helm, "V" chestplate, "B" boss (berganti-ganti)
STAGES = [
    (None, 6, 0.80, 2, 3),
    ("H", 8, 0.70, 2, 3),
    ("V", 8, 0.60, 2, 4),
    ("H", 10, 0.55, 3, 4),
    ("B", 14, 0.50, 3, 4),
]