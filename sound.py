"""Suara. File wav dimuat dari folder sounds/ di sebelah file ini.
Kalau pygame atau file tidak ada, game tetap jalan tanpa suara.

Tes suara tanpa kamera:  python sound.py
"""
import os

try:
    import pygame
except ImportError:
    pygame = None

SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")

FILES = {"slash": "slash.wav",
         "block": "block.wav",
         "enemydead": "enemydead.wav",
         "lose": "lose.wav"}

VOLUME = {"slash": 0.8,         # 0.0 - 1.0, atur keseimbangan antar suara
          "block": 0.9,
          "enemydead": 1.0,
          "lose": 1.0}

_snd = {}


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
    if _snd:
        pygame.mixer.stop()


def quit():
    if _snd:
        pygame.mixer.quit()


if __name__ == "__main__":
    import time
    init()
    for n in FILES:
        if n in _snd:
            print("memutar:", n)
            play(n)
            time.sleep(min(_snd[n].get_length(), 2.0) + 0.3)
    quit()