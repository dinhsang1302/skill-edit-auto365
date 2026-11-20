#!/usr/bin/env python3
"""Thử nghiệm minh hoạ 3D có tracking — cảnh CHỐNG TIA UV (anh yêu cầu 19/11/2026: diễn hoạt kiểu 3D, có tracking, không vỡ nét/răng cưa).
- Máy quay ảo: lia/xoay nhẹ + tiến vào (homography K·R·K⁻¹) → nền và MỌI hiệu ứng đi chung một phép chiếu (tracking).
- Mặt kính là một mặt phẳng: lớp phim lưới tổ ong + vòng va chạm được chiếu lên mặt phẳng kính (phối cảnh thật).
- Tia UV: chùm sáng thuôn (nhỏ ở xa, to ở gần), lõi sáng + quầng, gói sáng trôi CHẬM dọc tia; chạm kính → dội ngược.
- Chống răng cưa: dựng ở 2× (3840×2160) với nét LINE_AA rồi thu về 1920×1080 bằng INTER_AREA.
Chạy: <python> uv3d.py [--preview]  → uvshield_3d.mp4 (2,5 s, 25 fps) / preview_uv3d.jpg"""
import sys, math, subprocess, numpy as np, cv2
from pathlib import Path
D = Path(__file__).resolve().parent
IMG = D.parent / "anim_light/real/f_uv/f_uv.png"            # ảnh nền render kín khung (prompt: examples/anim_minh_hoa_sang/prompts/f_uv.txt)
W, H, FPS, SS = 1920, 1080, 25, 2
WS, HS = W * SS, H * SS
import os
DUR = float(os.environ.get("DUR", "2.5"))                   # DUR=10 → bản xem thử dài, tia bắn nhiều đợt
UV_CORE, UV_GLOW = np.array([255, 235, 255], np.float32), np.array([165, 90, 255], np.float32)   # RGB

def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def lin(t, a, b): return min(1, max(0, (t - a) / (b - a)))

src = cv2.cvtColor(cv2.imread(str(IMG)), cv2.COLOR_BGR2RGB).astype(np.float32)
ih, iw = src.shape[:2]
B = np.array([[WS / iw, 0, 0], [0, HS / ih, 0], [0, 0, 1]], np.float64)          # ảnh → khung 2×

def cam(t):
    """Máy quay ảo: yaw 2,2°→-0,6°, pitch nhẹ, tiến vào 1,10→1,17 quanh điểm nhìn (kính)."""
    u = ease(t / DUR); f = 1.25 * WS
    yaw = math.radians(2.2 - 2.8 * u); pit = math.radians(-0.8 + 1.0 * u)
    K = np.array([[f, 0, WS / 2], [0, f, HS / 2], [0, 0, 1]])
    Ry = np.array([[math.cos(yaw), 0, math.sin(yaw)], [0, 1, 0], [-math.sin(yaw), 0, math.cos(yaw)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(pit), -math.sin(pit)], [0, math.sin(pit), math.cos(pit)]])
    s = 1.10 + 0.07 * u; cx, cy = 0.36 * WS, 0.50 * HS
    Z = np.array([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)], [0, 0, 1]])
    return Z @ K @ Ry @ Rx @ np.linalg.inv(K) @ B

def P(Hm, pts):
    p = np.asarray(pts, np.float64).reshape(-1, 1, 2); return cv2.perspectiveTransform(p, Hm).reshape(-1, 2)

# mặt kính cửa trước (toạ độ ảnh gốc 1672×941) — 4 góc cho mặt phẳng + đa giác thật để cắt
GQ = np.array([[112, 196], [722, 330], [866, 640], [158, 616]], np.float64)
GPOLY = np.array([[100, 192], [470, 246], [722, 330], [860, 470], [868, 642], [158, 616], [88, 300]], np.float64)
TW, TH = 1600, 800                                                            # toạ độ phẳng của kính
HG = cv2.getPerspectiveTransform(np.float32([[0, 0], [TW, 0], [TW, TH], [0, TH]]), GQ.astype(np.float32)).astype(np.float64)
SUN = np.array([100, 32], np.float64)                                         # mặt trời trong ảnh
HITS = [(380, 230), (720, 330), (1060, 420), (560, 560), (930, 610)]          # điểm tia chạm (toạ độ kính)
RUN = 1.05 * 1.5                                                              # tia bay CHẬM hơn 1/3 (anh chốt 19/11)
_H0 = list(HITS); HITS = []; T0 = []
for c in range(max(1, int(DUR // 2.6) + 1)):                                  # mỗi 2,6 s một đợt tia mới
    for (hx, hy), h in zip(_H0, (1.05, 1.17, 1.29, 1.41, 1.53)):
        if h + c * 2.6 < DUR: HITS.append((hx + 40 * (c % 2), hy - 30 * (c % 2))); T0.append(h + c * 2.6 - RUN)
_T0_unused = [h - RUN for h in (1.05, 1.17, 1.29, 1.41, 1.53)]                         # tia đã bay sẵn từ trước khung đầu, chạm kính đúng mốc cũ

def hex_tex():
    """Lưới tổ ong mảnh (alpha) trên mặt phẳng kính, 2× để mịn."""
    k = 2; img = np.zeros((TH * k, TW * k), np.float32); r = 34 * k; dx = r * math.sqrt(3)
    for j in range(-1, int(TH * k / (1.5 * r)) + 2):
        for i in range(-1, int(TW * k / dx) + 2):
            cx = i * dx + (dx / 2 if j % 2 else 0); cy = j * 1.5 * r
            pts = np.array([[cx + r * math.cos(math.radians(60 * a + 30)), cy + r * math.sin(math.radians(60 * a + 30))] for a in range(6)], np.int32)
            cv2.polylines(img, [pts * 4], True, 1.0, 2 * k, cv2.LINE_AA, shift=2)
    return cv2.resize(img, (TW, TH), interpolation=cv2.INTER_AREA)
HEX = hex_tex()

def glass_layer(t, Hc):
    """Phim UV trên mặt kính: lưới tổ ong lan ra từ điểm chạm + vòng sóng + vệt bóng lướt — chiếu theo phối cảnh."""
    yy, xx = np.mgrid[0:TH, 0:TW].astype(np.float32)
    rev = np.zeros((TH, TW), np.float32); ring = np.zeros((TH, TW), np.float32)
    for (hx, hy), t0 in zip(HITS, T0):
        th = t0 + RUN; dt = t - th
        if dt <= 0: continue
        d = np.hypot(xx - hx, yy - hy)
        R = 520 * ease(dt / 1.0)
        rev = np.maximum(rev, np.clip((R - d) / 140, 0, 1))
        rr = 40 + 330 * ease(dt / 0.9); ring = np.maximum(ring, np.exp(-((d - rr) / 12) ** 2) * 0.6 * (1 - lin(dt, 0.15, 0.9)))
    gl = np.exp(-((xx + yy * 0.55 - (-300 + 2600 * lin(t, 1.3, 2.4))) / 90) ** 2) * (t > 1.3)   # vệt bóng lướt chéo
    a = HEX * rev * 0.42 + ring * 0.85 + rev * 0.10 + gl * rev * 0.45
    col = np.zeros((TH, TW, 3), np.float32); col[:] = (205, 170, 255)
    col = col * (1 - ring[..., None] * 0.6) + np.array([255, 245, 255], np.float32) * ring[..., None] * 0.6
    M = Hc @ HG
    A = cv2.warpPerspective(a, M, (WS, HS), flags=cv2.INTER_LINEAR)
    C = cv2.warpPerspective(col, M, (WS, HS), flags=cv2.INTER_LINEAR)
    m = np.zeros((HS, WS), np.uint8); cv2.fillPoly(m, [np.round(P(Hc, GPOLY) * 4).astype(np.int32)], 255, cv2.LINE_AA, shift=2)
    A *= cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 1.5)
    return C, np.clip(A, 0, 1)

def beams(t, Hc):
    """Chùm UV thuôn từ mặt trời tới điểm chạm; gói sáng trôi chậm; sau chạm → tia dội ngược mờ dần."""
    L = np.zeros((HS, WS), np.float32); core = np.zeros((HS, WS), np.float32)
    s = P(Hc, [SUN])[0]
    for (hx, hy), t0 in zip(HITS, T0):
        e = P(Hc @ HG, [(hx, hy)])[0]
        q = ease(lin(t, t0, t0 + RUN));
        if q <= 0: continue
        head = s + (e - s) * q
        fade = 1 - 0.75 * lin(t, t0 + RUN + 0.2, t0 + RUN + 1.0)
        n = 40
        for i in range(n):                                       # thân tia thuôn: nhỏ gần mặt trời, to gần máy
            a, b = i / n, (i + 1) / n
            if b > 1: break
            pa, pb = s + (head - s) * a, s + (head - s) * b
            wdt = (8 + 34 * b) * SS
            cv2.line(L, tuple(np.round(pa * 4).astype(int)), tuple(np.round(pb * 4).astype(int)), 0.42 * fade * (0.25 + 0.75 * b), int(wdt), cv2.LINE_AA, shift=2)
            cv2.line(core, tuple(np.round(pa * 4).astype(int)), tuple(np.round(pb * 4).astype(int)), 0.9 * fade * (0.3 + 0.7 * b), max(1, int(wdt * 0.16)), cv2.LINE_AA, shift=2)
        for ph in (0.0, 0.5):                                     # vệt sáng dài trôi CHẬM dọc tia (không chấm tròn)
            u = ((t - t0) * 0.27 + ph) % 1.0
            if u > q: continue
            for j in range(10):
                a, b = u - 0.10 * (j + 1) / 10, u - 0.10 * j / 10
                if a < 0: break
                pa, pb = s + (e - s) * a, s + (e - s) * b
                cv2.line(core, tuple(np.round(pa * 4).astype(int)), tuple(np.round(pb * 4).astype(int)), fade * (1 - j / 10), max(1, int((3 + 7 * b) * SS)), cv2.LINE_AA, shift=2)
        dt = t - (t0 + RUN)
        if dt > 0:                                                # dội ngược: phản xạ ra trước, lên trên
            v = (e - s) / np.linalg.norm(e - s); rdir = np.array([v[0] * 0.55, -abs(v[1]) - 0.35]); rdir /= np.linalg.norm(rdir)
            ln = 520 * SS * ease(dt / 1.5); ra = 0.75 * (1 - lin(dt, 0.7, 1.45))
            if ra > 0:
                for i in range(20):
                    a, b = i / 20, (i + 1) / 20
                    pa, pb = e + rdir * ln * a, e + rdir * ln * b
                    cv2.line(L, tuple(np.round(pa * 4).astype(int)), tuple(np.round(pb * 4).astype(int)), ra * (1 - a * 0.7) * 0.6, int((22 - 12 * a) * SS), cv2.LINE_AA, shift=2)
                    cv2.line(core, tuple(np.round(pa * 4).astype(int)), tuple(np.round(pb * 4).astype(int)), ra * (1 - a * 0.7), max(1, int((6 - 3 * a) * SS)), cv2.LINE_AA, shift=2)
            fl = math.exp(-dt * 4.0)                              # loé tại điểm chạm
            cv2.circle(core, tuple(np.round(e * 4).astype(int)), int((8 + 14 * (1 - fl)) * SS * 4), 0.8 * fl, -1, cv2.LINE_AA, shift=2)
    glow = cv2.GaussianBlur(L, (0, 0), 9 * SS) * 1.4 + cv2.GaussianBlur(core, (0, 0), 3 * SS)
    return np.clip(glow, 0, 1), np.clip(cv2.GaussianBlur(core, (0, 0), 0.8 * SS), 0, 1)

def frame(t):
    Hc = cam(t)
    bg = cv2.warpPerspective(src, Hc, (WS, HS), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    sun = P(Hc, [SUN])[0]; yy, xx = np.mgrid[0:HS, 0:WS].astype(np.float32)
    sg = np.exp(-((xx - sun[0]) ** 2 + (yy - sun[1]) ** 2) / (2 * (260 * SS) ** 2)) * 0.35
    bg = bg + (255 - bg) * sg[..., None]
    C, A = glass_layer(t, Hc); bg = bg * (1 - A[..., None]) + C * A[..., None]
    g, c = beams(t, Hc)
    bg = bg * (1 - g[..., None] * 0.85) + UV_GLOW * g[..., None] * 0.85
    bg = bg * (1 - c[..., None]) + UV_CORE * c[..., None]
    rs = 1 - lin(t, 0, 0.5) * 0                                    # vệt đỏ mảnh chân khung (thẳng, 4 px)
    y = int(HS - 34 * SS); x1 = int(WS * ease(lin(t, 0.1, 0.9)))
    if x1 > 0: cv2.line(bg, (0, y), (x1, y), (226, 32, 40), 4 * SS, cv2.LINE_AA)
    out = cv2.resize(np.clip(bg, 0, 255), (W, H), interpolation=cv2.INTER_AREA)
    return out.astype(np.uint8)

if __name__ == "__main__":
    if "--preview" in sys.argv:
        ts = [0.3, 0.8, 1.2, 1.6, 2.0, 2.4]
        tiles = [cv2.resize(frame(t), (960, 540), interpolation=cv2.INTER_AREA) for t in ts]
        sh = np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:])])
        cv2.imwrite(str(D / "preview_uv3d.jpg"), cv2.cvtColor(sh, cv2.COLOR_RGB2BGR), [1, 92])
        crop = frame(1.6)[200:740, 100:1060]                       # soi nét 100 %
        cv2.imwrite(str(D / "crop_uv3d.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)); print("preview ok"); sys.exit()
    n = round(DUR * FPS); out = D / ("uvshield_3d.mp4" if DUR == 2.5 else f"uvshield_3d_{DUR:g}s.mp4")
    sys.path.insert(0, str(D.parents[3] / "scripts")); import fast3d as FX   # <WS>/scripts
    FX.encode_auto(out, n, frame, FPS, W, H)                    # song song nhiều tiến trình (trần % máy) — 1.6.6
