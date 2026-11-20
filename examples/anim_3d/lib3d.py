#!/usr/bin/env python3
"""Thư viện DIỄN HOẠT 3D CÓ TRACKING dùng chung — Ford Everest x 3M (skill edit-auto365 v1.6.1, mẫu examples/anim_3d/uv3d.py).
- Ảnh nền: giữ ảnh render sáng của bản anim_light (work/anim_light/real/e_*), cùng khung cắt (view) + vá logo như anim_light.load().
  Toạ độ kính/tia viết theo khung 1920x1080 của ảnh nền đó (đo trên lưới 100 px: grid3d.py).
- Máy quay ảo: homography Z·K·R·K⁻¹·B (xoay yaw/pitch nhẹ + tiến vào) → nền và MỌI hiệu ứng chiếu chung một phép (tracking).
- Mặt kính = mặt phẳng: 4 góc → homography (toạ độ phẳng TW×TH); lớp phim/vòng sóng/vệt bóng vẽ trong toạ độ phẳng rồi chiếu, cắt theo đa giác kính.
- Tia: chùm thuôn (nhỏ ở xa, to gần), lõi + quầng, vệt sáng dài trôi chậm dọc tia (không chấm tròn), chạm kính → loé + vòng + dội ngược;
  tia "lọt" = mảnh, nhạt, đi tiếp qua kính. Màu theo chiều dài (vd. cam→đỏ).
- Lớp 2D phẳng cố định màn hình: panel trắng header đỏ có thanh đo, vệt đỏ mảnh chân khung (vẽ ở 2×).
- Chống răng cưa: dựng 2× (3840×2160), cv2 LINE_AA + shift=2, thu về 1920×1080 INTER_AREA, x264 crf 12."""
import math, subprocess, sys, numpy as np, cv2
from pathlib import Path
from PIL import Image, ImageDraw
D = Path(__file__).resolve().parent
LD = D.parent / "anim_light"
W, H, FPS, SS = 1920, 1080, 25, 2
WS, HS = W * SS, H * SS
RED, INK = (226, 32, 40), (14, 14, 16)
HEAT0, HEAT1 = (255, 190, 70), (232, 40, 30)
UV_CORE, UV_GLOW = (255, 235, 255), (165, 90, 255)
cv2.setNumThreads(3)

def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def lin(t, a, b): return min(1, max(0, (t - a) / (b - a)))
def I4(p): return tuple(int(round(v * 4)) for v in p)          # toạ độ cho shift=2

def load(n, patches=(), root=None):
    """Như anim_light.load() nhưng KHÔNG cắt khung: ảnh 1920x1080 (cover) + vá logo (inpaint). Toạ độ = lưới 100 px của ảnh gốc
    (anim_light/grid/<tên>.jpg). Khung cắt (view) đưa vào phép chiếu bằng viewM(). Trả float32 RGB."""
    im = Image.open((root or LD / "real") / f"{n}/{n}.png").convert("RGB")   # root: thư mục real khác (vd. anim_3d/real cho ảnh n_*)
    k = max(W / im.width, H / im.height); im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x0, y0 = (im.width - W) // 2, (im.height - H) // 2; a = np.asarray(im.crop((x0, y0, x0 + W, y0 + H))).copy()
    if patches:
        m = np.zeros(a.shape[:2], np.uint8)
        for cx, cy, rx, ry in patches: cv2.ellipse(m, (cx, cy), (rx, ry), 0, 0, 360, 255, -1)
        a = cv2.inpaint(a, m, 9, cv2.INPAINT_TELEA)
    return a.astype(np.float32)

def viewM(view=None):
    """Khung cắt (x0,y0,z) của anim_light → ma trận toạ độ ảnh gốc → khung 1920."""
    if not view: return np.eye(3)
    vx, vy, vz = view; return np.array([[vz, 0, -vx * vz], [0, vz, -vy * vz], [0, 0, 1]], np.float64)

B = np.array([[SS, 0, 0], [0, SS, 0], [0, 0, 1]], np.float64)   # khung nền 1920 → khung dựng 2×

def camera(t, dur, yaw=(2.0, -0.6), pitch=(-0.6, 0.4), zoom=(1.08, 1.15), c=(0.5, 0.5), f=1.25, roll=(0.0, 0.0)):
    """Máy quay ảo: yaw/pitch (độ) và tỉ lệ tiến vào nội suy ease theo t/dur, quanh điểm nhìn c (tỉ lệ khung)."""
    u = ease(t / dur); F = f * WS
    ya = math.radians(yaw[0] + (yaw[1] - yaw[0]) * u); pi = math.radians(pitch[0] + (pitch[1] - pitch[0]) * u)
    K = np.array([[F, 0, WS / 2], [0, F, HS / 2], [0, 0, 1]])
    Ry = np.array([[math.cos(ya), 0, math.sin(ya)], [0, 1, 0], [-math.sin(ya), 0, math.cos(ya)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(pi), -math.sin(pi)], [0, math.sin(pi), math.cos(pi)]])
    s = zoom[0] + (zoom[1] - zoom[0]) * u; cx, cy = c[0] * WS, c[1] * HS
    Z = np.array([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)], [0, 0, 1]])
    if roll != (0.0, 0.0):                                      # xoay quanh trục nhìn (quỹ đạo quanh vật, cảnh top view) — mặc định tắt
        r = math.radians(roll[0] + (roll[1] - roll[0]) * u); cr, sr = math.cos(r), math.sin(r)
        Z = Z @ np.array([[cr, -sr, cx * (1 - cr) + cy * sr], [sr, cr, cy * (1 - cr) - cx * sr], [0, 0, 1]])
    return Z @ K @ Ry @ Rx @ np.linalg.inv(K) @ B

def P(Hm, pts):
    p = np.asarray(pts, np.float64).reshape(-1, 1, 2); return cv2.perspectiveTransform(p, Hm).reshape(-1, 2)

class Plane:
    """Mặt kính phẳng: quad 4 góc (TL,TR,BR,BL, toạ độ nền 1920) ↔ toạ độ phẳng TW×TH; poly = đa giác thật để cắt."""
    def __init__(self, quad, poly, tw=1600, th=800):
        self.q = np.array(quad, np.float64); self.poly = np.array(poly, np.float64); self.tw, self.th = tw, th
        self.HG = cv2.getPerspectiveTransform(np.float32([[0, 0], [tw, 0], [tw, th], [0, th]]), self.q.astype(np.float32)).astype(np.float64)
        self.yy, self.xx = np.mgrid[0:th, 0:tw].astype(np.float32)
    def pt(self, Hc, uv): return P(Hc @ self.HG, [uv])[0]       # điểm phẳng → khung dựng
    def mask(self, Hc, feather=1.5):
        m = np.zeros((HS, WS), np.uint8); cv2.fillPoly(m, [np.round(P(Hc, self.poly) * 4).astype(np.int32)], 255, cv2.LINE_AA, shift=2)
        return cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), feather) if feather else m.astype(np.float32) / 255
    def warp(self, Hc, arr, interp=cv2.INTER_LINEAR):
        return cv2.warpPerspective(arr, Hc @ self.HG, (WS, HS), flags=interp)

import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
import fast3d as FX; FX.patch_cv2_blur()                    # RTX: trộn lớp + làm mờ trên GPU (anh chốt 20/11/2026), không có GPU → CPU
over = FX.over

def hex_tex(tw, th, r=34, wdt=2):
    k = 2; img = np.zeros((th * k, tw * k), np.float32); r *= k; dx = r * math.sqrt(3)
    for j in range(-1, int(th * k / (1.5 * r)) + 2):
        for i in range(-1, int(tw * k / dx) + 2):
            cx = i * dx + (dx / 2 if j % 2 else 0); cy = j * 1.5 * r
            pts = np.array([[cx + r * math.cos(math.radians(60 * a + 30)), cy + r * math.sin(math.radians(60 * a + 30))] for a in range(6)])
            cv2.polylines(img, [np.round(pts * 4).astype(np.int32)], True, 1.0, wdt * k, cv2.LINE_AA, shift=2)
    return cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)

class Light:
    """Bộ đệm ánh sáng cộng màu: G (quầng, màu×cường độ) + A (cường độ) ; C/CA (lõi). Quầng blur ở nửa độ phân giải."""
    def __init__(self):
        self.G = np.zeros((HS, WS, 3), np.float32); self.A = np.zeros((HS, WS), np.float32)
        self.C = np.zeros((HS, WS, 3), np.float32); self.CA = np.zeros((HS, WS), np.float32)
    def seg(self, pa, pb, col, a, w, core=False):
        if a <= 0.003: return
        A, Cc = (self.CA, self.C) if core else (self.A, self.G)
        w = max(1, int(round(w)))
        cv2.line(A, I4(pa), I4(pb), float(a), w, cv2.LINE_AA, shift=2)
        cv2.line(Cc, I4(pa), I4(pb), tuple(float(c) * a for c in col), w, cv2.LINE_AA, shift=2)
    def dot(self, p, r, col, a, core=True):
        if a <= 0.003: return
        A, Cc = (self.CA, self.C) if core else (self.A, self.G)
        cv2.circle(A, I4(p), int(r * 4), float(a), -1, cv2.LINE_AA, shift=2)
        cv2.circle(Cc, I4(p), int(r * 4), tuple(float(c) * a for c in col), -1, cv2.LINE_AA, shift=2)
    def apply(self, bg, glow_sigma=9, glow_k=1.4, glow_mix=0.85):
        def hblur(x, s):
            sm = cv2.resize(x, (WS // 2, HS // 2), interpolation=cv2.INTER_AREA); sm = cv2.GaussianBlur(sm, (0, 0), s / 2)
            return cv2.resize(sm, (WS, HS), interpolation=cv2.INTER_LINEAR)
        if self.A.any():
            ga = hblur(self.A, glow_sigma * SS) * glow_k + hblur(self.CA, 3 * SS); gc = hblur(self.G, glow_sigma * SS) * glow_k + hblur(self.C, 3 * SS)
        elif self.CA.any():
            ga = hblur(self.CA, 3 * SS); gc = hblur(self.C, 3 * SS)
        else: return bg
        col = gc / np.maximum(ga, 1e-4)[..., None]; ga = np.clip(ga, 0, 1)
        bg = bg * (1 - ga[..., None] * glow_mix) + col * ga[..., None] * glow_mix
        ca = cv2.GaussianBlur(self.CA, (0, 0), 0.8 * SS); cc = cv2.GaussianBlur(self.C, (0, 0), 0.8 * SS)
        ccol = cc / np.maximum(ca, 1e-4)[..., None]; ca = np.clip(ca, 0, 1)
        return bg * (1 - ca[..., None]) + ccol * ca[..., None]

def _cmix(c0, c1, u): return tuple(c0[i] + (c1[i] - c0[i]) * u for i in range(3))

def ray(Lt, t, s, e, t0, run, c0, c1, core=(255, 250, 235), w0=8, w1=34, k=1.0, reflect=True, rdir=(0.55, -1.0),
        thru=0.0, thru_len=380, fade_after=(0.2, 1.0), flash=True):
    """Một chùm tia từ s tới e (khung dựng 2×) bay trong `run` giây từ t0. Thuôn w0→w1 (px khung 1080), lõi sáng, 2 vệt sáng
    dài trôi chậm; chạm → loé + dội ngược (reflect) ; thru>0: một phần mảnh nhạt đi tiếp qua kính (lọt)."""
    q = ease(lin(t, t0, t0 + run))
    if q <= 0: return
    s = np.asarray(s, np.float64); e = np.asarray(e, np.float64); head = s + (e - s) * q
    fade = k * (1 - 0.72 * lin(t, t0 + run + fade_after[0], t0 + run + fade_after[1]))
    n = 36
    for i in range(n):
        a, b = i / n, (i + 1) / n
        if b > q + 1e-9: break
        pa, pb = s + (e - s) * a, s + (e - s) * b; col = _cmix(c0, c1, b)
        wd = (w0 + (w1 - w0) * b) * SS
        Lt.seg(pa, pb, col, 0.42 * fade * (0.25 + 0.75 * b), wd)
        Lt.seg(pa, pb, _cmix(core, col, 0.35), 0.9 * fade * (0.3 + 0.7 * b), max(1, wd * 0.16), core=True)
    for ph in (0.0, 0.5):                                       # vệt sáng dài trôi CHẬM (không chấm tròn)
        u = ((t - t0) * 0.27 + ph) % 1.0
        if u > q: continue
        for j in range(10):
            a, b = u - 0.10 * (j + 1) / 10, u - 0.10 * j / 10
            if a < 0: break
            pa, pb = s + (e - s) * a, s + (e - s) * b
            Lt.seg(pa, pb, core, fade * (1 - j / 10), (3 + 7 * b) * SS, core=True)
    dt = t - (t0 + run)
    if dt <= 0: return
    v = (e - s) / np.linalg.norm(e - s)
    if reflect:                                                 # dội ngược
        rd = np.array([v[0] * rdir[0], -abs(v[1]) + rdir[1] * 0.35]); rd /= np.linalg.norm(rd)
        ln = 520 * SS * ease(dt / 1.5) * k; ra = 0.75 * k * (1 - lin(dt, 0.7, 1.45))
        if ra > 0:
            for i in range(20):
                a, b = i / 20, (i + 1) / 20; pa, pb = e + rd * ln * a, e + rd * ln * b
                col = _cmix(c1, c0, a)
                Lt.seg(pa, pb, col, ra * (1 - a * 0.7) * 0.6, (22 - 12 * a) * SS)
                Lt.seg(pa, pb, _cmix(core, col, 0.3), ra * (1 - a * 0.7), max(1, (6 - 3 * a) * SS), core=True)
    if thru > 0:                                                # phần nhỏ LỌT qua kính: mảnh, nhạt, đi tiếp
        ln = thru_len * SS * ease(dt / 1.2); ta = thru * k * (1 - lin(dt, 1.0, 1.8))
        if ta > 0:
            for i in range(10):
                a, b = i / 10, (i + 1) / 10; pa, pb = e + v * ln * a, e + v * ln * b
                Lt.seg(pa, pb, c1, ta * (1 - a) * 0.5, 9 * SS)
                Lt.seg(pa, pb, _cmix(core, c1, 0.5), ta * (1 - a), max(1, 2.2 * SS), core=True)
    fl = math.exp(-dt * 4.0)                                    # loé tại điểm chạm
    if flash: Lt.dot(e, (8 + 14 * (1 - fl)) * SS, core, 0.8 * fl * k)

def rings(pl, t, hits, R=520, col_ring=0.6, spread=1.0):
    """Lan phủ + vòng sóng trên toạ độ phẳng từ các điểm chạm [(u,v,t_hit)] → (rev, ring) HxW phẳng."""
    rev = np.zeros((pl.th, pl.tw), np.float32); ring = np.zeros_like(rev)
    for hx, hy, th in hits:
        dt = t - th
        if dt <= 0: continue
        d = np.hypot(pl.xx - hx, pl.yy - hy)
        rev = np.maximum(rev, np.clip((R * spread * ease(dt / 1.0) - d) / 140, 0, 1))
        rr = 40 + 330 * ease(dt / 0.9); ring = np.maximum(ring, np.exp(-((d - rr) / 12) ** 2) * col_ring * (1 - lin(dt, 0.15, 0.9)))
    return rev, ring

def sweep(pl, t, a0, a1, dirn=(1, 0.25)):
    """Phim quét trên mặt phẳng kính: trả (cover 0..1, mép đỏ) toạ độ phẳng. dirn = hướng quét (phẳng)."""
    dx, dy = dirn; n = math.hypot(dx, dy); dx, dy = dx / n, dy / n
    proj = pl.xx * dx + pl.yy * dy; lo, hi = proj.min() - 40, proj.max() + 40
    p = ease(lin(t, a0, a1)); c = lo + (hi - lo) * p
    if p <= 0: return None, None
    cov = np.clip((c - proj) / 8, 0, 1)
    edge = np.exp(-((proj - c) / 7) ** 2) * (0 < p < 1)
    return cov, edge

def sheen(pl, t, a0, a1, width=90, slope=0.55):
    """Vệt bóng lướt chéo trên mặt kính (toạ độ phẳng)."""
    p = lin(t, a0, a1)
    if p <= 0 or p >= 1: return None
    pos = -300 + (pl.tw + pl.th * slope + 600) * p
    return np.exp(-((pl.xx + pl.yy * slope - pos) / width) ** 2) * math.sin(p * math.pi)

def sun_glow(bg, sun, r, a):
    if a <= 0: return bg
    yy, xx = np.ogrid[0:HS, 0:WS]
    g = np.exp(-((xx - sun[0]) ** 2 + (yy - sun[1]) ** 2) / (2 * (r * SS) ** 2)).astype(np.float32) * a
    return bg + (255 - bg) * g[..., None]

def shafts(bg, sun, angles, length, width, col, a):
    """Chùm nắng mềm (dải sáng rộng mờ) từ mặt trời — chiếu theo camera (sun đã ở khung dựng)."""
    if a <= 0: return bg
    L = np.zeros((HS // 4, WS // 4), np.float32)
    for ang, k in angles:
        e = (sun[0] + length * SS * math.cos(ang), sun[1] + length * SS * math.sin(ang))
        cv2.line(L, I4((sun[0] / 4, sun[1] / 4)), I4((e[0] / 4, e[1] / 4)), float(k), max(1, int(width * SS / 4)), cv2.LINE_AA, shift=2)
    L = cv2.resize(cv2.GaussianBlur(L, (0, 0), 6), (WS, HS), interpolation=cv2.INTER_LINEAR) * a
    return over(bg, col, L * 0.6)

# ---------------- lớp 2D phẳng cố định màn hình (vẽ 2×) ----------------
def _ico_heat(d, cx, cy, A, s):
    for k in (-14, 0, 14):
        d.line([((cx + k + 6 * math.sin(i / 5)) * s, (cy + 26 - i) * s) for i in range(0, 52, 2)], fill=RED + (A,), width=5 * s)
def _ico_eye(d, cx, cy, A, s):
    d.ellipse(((cx - 34) * s, (cy - 18) * s, (cx + 34) * s, (cy + 18) * s), outline=INK + (A,), width=5 * s)
    d.ellipse(((cx - 11) * s, (cy - 11) * s, (cx + 11) * s, (cy + 11) * s), fill=INK + (A,))
def _ico_uv(d, cx, cy, A, s):
    col = (150, 80, 230); d.ellipse(((cx - 17) * s, (cy - 17) * s, (cx + 17) * s, (cy + 17) * s), fill=col + (A,))
    for i in range(8):
        a = i * math.pi / 4
        d.line(((cx + 25 * math.cos(a)) * s, (cy + 25 * math.sin(a)) * s, (cx + 35 * math.cos(a)) * s, (cy + 35 * math.sin(a)) * s), fill=col + (A,), width=5 * s)
ICONS = dict(heat=_ico_heat, eye=_ico_eye, uv=_ico_uv)

def panel_bar(bg, t, x, y, w, val, a0, a1, icon=None, fill=RED, h=128):
    """Panel trắng bo góc viền mảnh + bóng nhẹ + dải header đỏ + thanh đo tới val (0..1); không chữ/số. Phẳng, cố định màn hình, vẽ 2×."""
    al = ease(lin(t, a0 - 0.6, a0 - 0.1))
    if al <= 0: return bg
    s = SS; dy = 18 * (1 - al); pad = 60
    X0, Y0, X1, Y1 = int((x - pad) * s), int((y - pad) * s), int((x + w + pad) * s), int((y + h + pad + 20) * s)
    pw, ph = X1 - X0, Y1 - Y0; ox, oy = x - pad, y - pad
    def R(a, b, c, d_): return ((a - ox) * s, (b - oy + dy) * s, (c - ox) * s, (d_ - oy + dy) * s)
    L = Image.new("RGBA", (pw, ph)); d = ImageDraw.Draw(L)
    d.rounded_rectangle(R(x, y, x + w, y + h), 22 * s, fill=(255, 255, 255, 255), outline=(215, 218, 224, 255), width=2 * s)
    hd = Image.new("RGBA", (pw, ph)); ImageDraw.Draw(hd).rounded_rectangle(R(x, y, x + w, y + h), 22 * s, fill=RED + (255,))
    cm = Image.new("L", (pw, ph)); ImageDraw.Draw(cm).rectangle(R(x, y, x + w, y + 22), fill=255)
    hd.putalpha(Image.fromarray(np.minimum(np.asarray(hd.getchannel("A")), np.asarray(cm)))); L.alpha_composite(hd)
    bx0 = x + (118 if icon else 34); bx1 = x + w - 34; by = y + 62; bh = 30
    if icon: ICONS[icon](d, (x + 62 - ox), (by + bh / 2 - oy + dy), 255, s)
    d.rounded_rectangle(R(bx0, by, bx1, by + bh), bh // 2 * s, fill=(232, 233, 236, 255))
    p = ease(lin(t, a0, a1)) * val
    if p > 0.005: d.rounded_rectangle(R(bx0, by, bx0 + max(bh, (bx1 - bx0) * p), by + bh), bh // 2 * s, fill=fill + (255,))
    for qq in (0.25, 0.5, 0.75):
        xq = bx0 + (bx1 - bx0) * qq; d.line(R(xq, by + bh + 8, xq, by + bh + 18)[:4], fill=(150, 152, 158, 205), width=2 * s)
    arr = np.asarray(L).astype(np.float32); a = arr[..., 3] / 255 * al
    sh = cv2.GaussianBlur(a, (0, 0), 16 * s); M = np.float32([[1, 0, 0], [0, 1, 10 * s]]); sh = cv2.warpAffine(sh, M, (pw, ph)) * 0.22
    reg = bg[Y0:Y1, X0:X1]; reg = reg * (1 - sh[..., None]); reg = reg * (1 - a[..., None]) + arr[..., :3] * a[..., None]
    bg[Y0:Y1, X0:X1] = reg; return bg

def red_line(bg, t, start=0.1, y=1046):
    """Một vệt đỏ MẢNH thẳng chân khung, quét trái→phải (cố định màn hình)."""
    x1 = WS * ease(lin(t, start, start + 0.8))
    if x1 > 1: cv2.line(bg, (0, int(y * SS)), (int(x1), int(y * SS)), (226, 32, 40), 4 * SS, cv2.LINE_AA)
    return bg

def lens(bg, img, lx, ly, r, al, anchor, col=RED):
    """Kính lúp tròn viền trắng + vòng đỏ (phẳng, cố định màn hình), dây đỏ mảnh nối tới điểm neo đã TRACK (anchor = khung dựng 2×)."""
    if al <= 0.01: return bg
    s = SS; L = Image.new("RGBA", (WS, HS)); d = ImageDraw.Draw(L); A = 255
    ang = math.atan2(anchor[1] / s - ly, anchor[0] / s - lx); ex, ey = lx + r * math.cos(ang), ly + r * math.sin(ang)
    d.line((anchor[0], anchor[1], ex * s, ey * s), fill=col + (A,), width=4 * s)
    d.ellipse((anchor[0] - 9 * s, anchor[1] - 9 * s, anchor[0] + 9 * s, anchor[1] + 9 * s), fill=col + (A,), outline=(255, 255, 255, A), width=3 * s)
    im = img.resize((2 * r * s, 2 * r * s), Image.LANCZOS).convert("RGBA"); m = Image.new("L", im.size); ImageDraw.Draw(m).ellipse((0, 0, im.width - 1, im.height - 1), fill=255); im.putalpha(m)
    L.alpha_composite(im, (int((lx - r) * s), int((ly - r) * s)))
    d.ellipse(((lx - r - 8) * s, (ly - r - 8) * s, (lx + r + 8) * s, (ly + r + 8) * s), outline=(255, 255, 255, A), width=10 * s)
    d.ellipse(((lx - r - 12) * s, (ly - r - 12) * s, (lx + r + 12) * s, (ly + r + 12) * s), outline=col + (A,), width=4 * s)
    a = np.asarray(L.getchannel("A")).astype(np.float32) / 255 * al; c = np.asarray(L.convert("RGB")).astype(np.float32)
    sh = cv2.GaussianBlur(a, (0, 0), 18 * s); sh = cv2.warpAffine(sh, np.float32([[1, 0, 0], [0, 1, 12 * s]]), (WS, HS)) * 0.3
    bg = bg * (1 - sh[..., None]); return bg * (1 - a[..., None]) + c * a[..., None]

def finish(bg):
    return cv2.resize(np.clip(bg, 0, 255), (W, H), interpolation=cv2.INTER_AREA).astype(np.uint8)

def encode(out, n, frame):
    """Render cảnh: hàm khung cấp module → song song nhiều tiến trình + RTX (fast3d.encode_auto); FX_SERIAL=1 → tuần tự."""
    return FX.encode_auto(out, n, frame, FPS, W, H)
