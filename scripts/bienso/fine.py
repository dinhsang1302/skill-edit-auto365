"""Ảnh phóng to có lưới 10 px để đọc toạ độ 4 góc biển. Dùng: python fine.py out.jpg <n>:<t>:x0:y0:x1:y1 ... (toạ độ 1920x1080)"""
import cv2, numpy as np, sys
from cand import src
def grab(n, t):
    c = cv2.VideoCapture(str(src(n))); c.set(0, t * 1000); ok, fr = c.read()
    return cv2.resize(fr, (1920, 1080), interpolation=cv2.INTER_AREA)
tiles = []
for a in sys.argv[2:]:
    n, t, x0, y0, x1, y1 = a.split(":"); t = float(t); x0, y0, x1, y1 = map(int, (x0, y0, x1, y1))
    fr = grab(n, t)[y0:y1, x0:x1]; s = 640 / (x1 - x0); v = cv2.resize(fr, (640, int((y1 - y0) * s)), interpolation=cv2.INTER_CUBIC)
    for gx in range((x0 // 10 + 1) * 10, x1, 10):
        X = int((gx - x0) * s); cv2.line(v, (X, 0), (X, v.shape[0]), (0, 255, 255) if gx % 50 == 0 else (0, 120, 160), 1)
        if gx % 50 == 0: cv2.putText(v, str(gx), (X + 2, 12), 0, 0.4, (0, 255, 0), 1)
    for gy in range((y0 // 10 + 1) * 10, y1, 10):
        Y = int((gy - y0) * s); cv2.line(v, (0, Y), (640, Y), (0, 255, 255) if gy % 50 == 0 else (0, 120, 160), 1)
        if gy % 50 == 0: cv2.putText(v, str(gy), (2, Y - 2), 0, 0.4, (0, 255, 0), 1)
    cv2.putText(v, f"C{n} {t}s", (5, v.shape[0] - 6), 0, 0.6, (255, 0, 255), 2)
    v = cv2.copyMakeBorder(v, 0, max(0, 640 - v.shape[0]), 0, 0, 0)[:640]; tiles.append(v)
while len(tiles) % 3: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(sys.argv[1], np.vstack([np.hstack(tiles[j:j + 3]) for j in range(0, len(tiles), 3)]), [1, 90])
