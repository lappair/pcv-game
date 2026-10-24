"""Menu utama dan layar cara bermain.
Dikontrol dengan tangan: tahan benda merah di dalam tombol selama MENU_DWELL detik.
Cadangan keyboard: SPACE/ENTER = start, H = cara main, B = kembali, Q = keluar."""
import cv2

from background import make_background
from config import MENU_DWELL, MENU_BG
from hud import draw_trail

FONT = cv2.FONT_HERSHEY_SIMPLEX

MAIN_BUTTONS = [("START", "start"), ("HOW TO PLAY", "howto"), ("QUIT", "quit")]
BACK_BUTTONS = [("BACK", "back")]

HOWTO_LINES = [
    "TEBAS: gerakkan benda merah cepat melewati musuh",
    "HELM (panah kiri-kanan): tebas horizontal",
    "CHESTPLATE (panah atas-bawah): tebas vertikal",
    "BLOCK: saat musuh angkat pedang, sentuh lingkaran yang menyala",
    "Musuh 2-4 pukulan beruntun: block tiap pukulan untuk stagger",
    "Tebasan memakai stamina, habis = EXHAUSTED (block ikut gagal)",
    "Musuh tidak bisa diserang saat sedang menyerang",
]


class Menu:
    def __init__(self):
        self.enter(0.0)

    def enter(self, now):
        """Panggil setiap kali masuk ke menu."""
        self.screen = "main"
        self._reset(now)

    def _reset(self, now):
        self.target = None          # tombol yang sedang diisi
        self.prog = 0.0             # 0..1
        self.last_t = now
        self.lock_until = now + 0.6  # abaikan tangan sebentar setelah ganti layar

    # ---------- layout ----------
    def _buttons(self):
        return MAIN_BUTTONS if self.screen == "main" else BACK_BUTTONS

    def _rects(self, w, h):
        bw, bh = int(w * 0.42), int(h * 0.11)
        x1 = (w - bw) // 2
        ycs = [0.46, 0.62, 0.78] if self.screen == "main" else [0.88]
        return [(x1, int(h * yc) - bh // 2, x1 + bw, int(h * yc) + bh // 2) for yc in ycs]

    # ---------- logika ----------
    def _key_action(self, key):
        if self.screen == "main":
            if key in (32, 13):
                return "start"
            if key == ord("h"):
                return "howto"
        elif key in (ord("b"), 27):
            return "back"
        return None

    def _dwell(self, hand, dt, now, w, h):
        hover = None
        if hand.detected and now >= self.lock_until:
            for i, (x1, y1, x2, y2) in enumerate(self._rects(w, h)):
                if x1 <= hand.pos[0] <= x2 and y1 <= hand.pos[1] <= y2:
                    hover = i
        if hover is not None and hover == self.target:
            self.prog += dt / MENU_DWELL
            if self.prog >= 1.0:
                self.prog = 0.0
                return self._buttons()[hover][1]
        else:
            # keluar dari tombol: progres turun 2x lebih cepat dari naiknya
            self.prog = max(0.0, self.prog - 2 * dt / MENU_DWELL)
            if self.prog == 0.0:
                self.target = hover
        return None

    def update(self, hand, now, w, h, key=255):
        """Mengembalikan "start" atau "quit" kalau dipilih, selain itu None."""
        dt = max(0.0, now - self.last_t)
        self.last_t = now
        act = self._key_action(key)
        if act is None:
            act = self._dwell(hand, dt, now, w, h)
        if act == "howto":
            self.screen = "howto"
            self._reset(now)
        elif act == "back":
            self.screen = "main"
            self._reset(now)
        elif act in ("start", "quit"):
            return act
        return None

    # ---------- gambar ----------
    def _text_center(self, out, txt, cx, cy, scale, col, th):
        (tw, th_), _ = cv2.getTextSize(txt, FONT, scale, th)
        cv2.putText(out, txt, (cx - tw // 2, cy + th_ // 2), FONT, scale, col, th, cv2.LINE_AA)

    def _draw_title(self, out, w, h, k):
        cx = w // 2
        self._text_center(out, "ESCAPE THE CRYPT", cx + 3, int(h * 0.20) + 3, 1.5 * k, (0, 0, 150), 3)
        self._text_center(out, "ESCAPE THE CRYPT", cx, int(h * 0.20), 1.5 * k, (235, 235, 235), 3)
        self._text_center(out, "tahan benda merah di tombol selama 1 detik", cx, int(h * 0.29),
                          0.55 * k, (200, 200, 200), 1)
        self._text_center(out, "SPACE = start   H = cara main   Q = keluar", cx, int(h * 0.93),
                          0.45 * k, (170, 170, 170), 1)

    def _draw_howto(self, out, w, h, k):
        ov = out.copy()
        cv2.rectangle(ov, (int(w * 0.05), int(h * 0.06)), (int(w * 0.95), int(h * 0.78)), (0, 0, 0), -1)
        out = cv2.addWeighted(ov, 0.6, out, 0.4, 0)
        self._text_center(out, "CARA BERMAIN", w // 2, int(h * 0.14), 1.0 * k, (80, 255, 255), 2)
        for i, line in enumerate(HOWTO_LINES):
            cv2.putText(out, line, (int(w * 0.08), int(h * (0.25 + 0.085 * i))), FONT,
                        0.5 * k, (235, 235, 235), 1, cv2.LINE_AA)
        return out

    def _draw_buttons(self, out, w, h, k):
        rects = self._rects(w, h)
        ov = out.copy()
        for i, (x1, y1, x2, y2) in enumerate(rects):
            cv2.rectangle(ov, (x1, y1), (x2, y2), (35, 35, 35), -1)
            if i == self.target and self.prog > 0:
                fx = x1 + int((x2 - x1) * min(self.prog, 1.0))
                cv2.rectangle(ov, (x1, y1), (fx, y2), (80, 200, 100), -1)
        out = cv2.addWeighted(ov, 0.7, out, 0.3, 0)
        for i, ((x1, y1, x2, y2), (label, _)) in enumerate(zip(rects, self._buttons())):
            active = i == self.target and self.prog > 0
            cv2.rectangle(out, (x1, y1), (x2, y2), (80, 255, 120) if active else (255, 255, 255), 2)
            self._text_center(out, label, (x1 + x2) // 2, (y1 + y2) // 2, 0.9 * k, (255, 255, 255), 2)
        return out

    def _draw_cursor(self, out, hand):
        if not hand.detected:
            return
        c = (int(hand.pos[0]), int(hand.pos[1]))
        cv2.circle(out, c, 10, (255, 255, 255), 2)
        if self.prog > 0:
            cv2.ellipse(out, c, (18, 18), -90, 0, 360 * min(self.prog, 1.0),
                        (80, 255, 120), 4, cv2.LINE_AA)

    def render(self, frame, hand, trail, now):
        h, w = frame.shape[:2]
        k = w / 640.0
        out = make_background(frame, MENU_BG)
        if self.screen == "main":
            self._draw_title(out, w, h, k)
        else:
            out = self._draw_howto(out, w, h, k)
        out = self._draw_buttons(out, w, h, k)
        draw_trail(out, trail, False)
        self._draw_cursor(out, hand)
        if not hand.detected:
            self._text_center(out, "benda merah tidak terdeteksi (atur S_min / V_min di window mask)",
                              w // 2, h - 10, 0.45 * k, (0, 160, 255), 1)
        return out