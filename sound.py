"""Suara. File dimuat dari folder sounds/ di sebelah file ini.
- Efek suara (.wav pendek) dimuat utuh ke memori dan diputar per kejadian.
- BGM (bgm.ogg / bgm.mp3 / bgm.wav, opsional) di-stream dan diulang terus. Fade in/out dibuat
  manual per frame lewat update(), karena pygame.mixer.music.fadeout() memblokir loop game.
Kalau pygame atau file tidak ada, game tetap jalan tanpa suara.

Tes tanpa kamera:  python sound.py
"""
import os
import time

try:
    import pygame
except ImportError:
    pygame = None

SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")

FILES = {"slash": "slash.wav",
         "block": "block.wav",
         "enemydead": "enemydead.wav",
         "lose": "lose.wav",
         "takedamage": "takedamage.wav"}

VOLUME = {"slash": 0.8,         # 0.0 - 1.0, atur keseimbangan antar suara
          "block": 0.9,
          "enemydead": 1.0,
          "lose": 1.0,
          "takedamage": 1.0}

MUSIC_FILES = ("bgm.ogg", "bgm.mp3", "bgm.wav")     # dicari berurutan; yang pertama ketemu dipakai
MUSIC_VOLUME = 0.35             # BGM dibuat lebih pelan dari efek supaya efek tetap terdengar
MUSIC_FADE_IN = 1.0             # detik
MUSIC_FADE_OUT = 0.8

_snd = {}
_music_path = None
_music_playing = False          # lagu sedang berjalan (termasuk saat sedang di-fade out)
_want = False                   # apakah musik sedang diminta menyala
_mv = 0.0                       # volume musik sekarang
_mv_target = 0.0
_mv_rate = 1.0                  # perubahan volume per detik
_t_last = None


def _init_mixer():
    """Coba beberapa konfigurasi, karena sebagian driver audio menolak buffer kecil."""
    attempts = [
        dict(frequency=44100, size=-16, channels=2, buffer=512),
        dict(frequency=44100, size=-16, channels=2, buffer=1024),
        dict(frequency=44100, size=-16, channels=2),
        {},
    ]
    last = None
    for kw in attempts:
        try:
            pygame.mixer.init(**kw)
            return True
        except Exception as ex:
            last = ex
            pygame.mixer.quit()
    print("[sound] mixer gagal init:", last)
    return False


def _init_music():
    global _music_path
    for fn in MUSIC_FILES:
        path = os.path.join(SOUND_DIR, fn)
        if os.path.isfile(path):
            try:
                pygame.mixer.music.load(path)
                _music_path = path
                print("[sound] bgm:", fn)
            except Exception as ex:
                print(f"[sound] gagal memuat {fn}: {ex} (coba .ogg atau .wav)")
            return
    print("[sound] bgm tidak ada (opsional), taruh salah satu di sounds/:", ", ".join(MUSIC_FILES))


def init():
    if pygame is None:
        print("[sound] pygame tidak terpasang, jalan tanpa suara")
        return
    if not _init_mixer():
        return
    print("[sound] mixer OK:", pygame.mixer.get_init(), "| folder:", SOUND_DIR)
    for name, fn in FILES.items():
        path = os.path.join(SOUND_DIR, fn)
        if not os.path.isfile(path):
            print(f"[sound] FILE TIDAK ADA: {path}")
            continue
        try:
            s = pygame.mixer.Sound(path)
            s.set_volume(VOLUME.get(name, 1.0))
            _snd[name] = s
        except Exception as ex:
            print(f"[sound] gagal memuat {fn}: {ex}")
    print("[sound] termuat:", sorted(_snd) or "tidak ada")
    _init_music()


# ---------- efek suara ----------
def play(name):
    s = _snd.get(name)
    if s:
        s.play()
    else:
        print(f"[sound] '{name}' diminta tapi tidak termuat")


def play_events(events):
    """Putar semua kejadian yang dicatat game, lalu kosongkan daftarnya."""
    for name in events:
        play(name)
    events.clear()


def stop():
    """Hentikan efek suara (BGM tidak ikut berhenti)."""
    if _snd:
        pygame.mixer.stop()


# ---------- BGM ----------
def _ramp_to(target, secs):
    global _mv_target, _mv_rate
    _mv_target = target
    _mv_rate = max(abs(target - _mv), 1e-3) / max(secs, 1e-3)   # tiba tepat dalam `secs` detik


def set_music(want):
    """Panggil tiap frame dengan True/False: musik harus menyala atau tidak.
    Hanya bereaksi saat nilainya berubah. Mati total lalu menyala lagi = mulai dari awal lagu."""
    global _want, _music_playing, _mv
    if _music_path is None or want == _want:
        return
    _want = want
    if want:
        if not _music_playing:              # kalau masih ada sisa fade out, cukup dinaikkan lagi
            _mv = 0.0
            pygame.mixer.music.set_volume(0.0)
            pygame.mixer.music.play(loops=-1)
            _music_playing = True
        _ramp_to(MUSIC_VOLUME, MUSIC_FADE_IN)
    else:
        _ramp_to(0.0, MUSIC_FADE_OUT)


def update():
    """Panggil tiap frame: menggerakkan fade volume dan mematikan lagu setelah fade out selesai."""
    global _mv, _t_last, _music_playing
    now = time.time()
    dt = 0.0 if _t_last is None else min(now - _t_last, 0.1)
    _t_last = now
    if not _music_playing:
        return
    if _mv != _mv_target:
        step = _mv_rate * dt
        _mv = min(_mv + step, _mv_target) if _mv < _mv_target else max(_mv - step, _mv_target)
        pygame.mixer.music.set_volume(_mv)
    if _mv_target == 0.0 and _mv <= 0.0:
        pygame.mixer.music.stop()
        _music_playing = False


def quit():
    if pygame is not None and pygame.mixer.get_init():
        pygame.mixer.quit()


if __name__ == "__main__":
    init()
    for n in FILES:
        if n in _snd:
            print("memutar:", n)
            play(n)
            time.sleep(min(_snd[n].get_length(), 2.0) + 0.3)
    if _music_path:
        print("bgm: fade in, 4 detik, lalu fade out")
        set_music(True)
        t0 = time.time()
        while time.time() - t0 < 4.0:
            update()
            time.sleep(0.016)
        set_music(False)
        t0 = time.time()
        while time.time() - t0 < MUSIC_FADE_OUT + 0.3:
            update()
            time.sleep(0.016)
    quit()