"""Titik masuk. Jalankan: python main.py"""
import time
import cv2

from vision import RedTracker
from game import new_game, step
from hud import render
from menu import Menu
import sound


def main():
    sound.init()
    cap = cv2.VideoCapture(0)
    tracker = RedTracker()
    menu = Menu()
    scene = "menu"          # "menu" atau "game"
    g = None

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        now = time.time()
        hand = tracker.update(frame, now)

        if scene == "menu":
            act = menu.update(hand, now, w, h, key)
            if act == "quit":
                break
            if act == "start":
                g = new_game(w, h)
                sound.stop()
                scene = "game"
        else:
            over = g["state"] in ("dead", "win")
            if key == 27 or (key == ord("m") and over):
                menu.enter(now)
                sound.stop()
                scene = "menu"
            elif key == ord(" ") and over:
                g = new_game(w, h)
                tracker.reset()
                sound.stop()
            else:
                step(g, hand, now, w, h)
                sound.play_events(g["events"])

        if scene == "menu":
            out = menu.render(frame, hand, tracker.trail, now)
        else:
            out = render(frame, g, hand, tracker.trail, now)
        cv2.imshow("game", out)

    cap.release()
    cv2.destroyAllWindows()
    sound.quit()


if __name__ == "__main__":
    main()