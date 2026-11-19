#!/usr/bin/env python3
"""Thư viện hiệu ứng minh hoạ NỀN SÁNG theo style brand phim cách nhiệt 3M (đỏ–trắng–đen) — 19/11/2026.
Ảnh render chân thực nền trắng/xám nhạt (Codex) + hiệu ứng code:
  heat_waves  : sóng nhiệt cam→đỏ có đầu mũi tên (xuyên kính tới ghế / dừng ở kính rồi dội ngược)
  shield      : khiên bạc kim loại hiện trên mặt kính
  reflect     : tia sáng trắng-bạc dội ngược khỏi kính (có mũi tên)
  film_sweep  : lớp phim phủ qua kính, mép quét màu đỏ
  beams       : chùm nắng mềm
  panel_bar   : panel trắng bo góc viền mảnh đổ bóng nhẹ + dải header đỏ + thanh đo đỏ (không chữ/số)
  red_sweep   : vệt đỏ quét ở chân khung
  outline     : viền nhấn kính
Không chữ/số trong hình (số nằm ở chữ kin của build). Dùng chung được cho dịch vụ khác (phim, PPF, đèn…)."""
import math, subprocess, numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

W, H, FPS = 1920, 1080, 25
RED, RED2, INK, PAPER = (226, 32, 40), (190, 18, 28), (14, 14, 16), (246, 246, 248)
HEAT0, HEAT1 = (255, 196, 80), (232, 40, 30)                 # cam → đỏ
UV0, UV1 = (200, 150, 255), (130, 60, 230)

def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def lin(t, a, b): return min(1, max(0, (t - a) / (b - a)))
def mix(c0, c1, u): return tuple(int(c0[i] + (c1[i] - c0[i]) * u) for i in range(3))

def base(path, fade=None, white=0.92, crop=None, veil=0.0, veil_x=(0.58, 0.78)):
    """Ảnh nền 16:9 kín khung (cover). fade=(x0,x1): phủ trắng dần sang phải (bản cũ, KHÔNG dùng nữa — anh không muốn mảng trắng trơn).
    veil>0: chỉ làm dịu nhẹ vùng chữ bên phải (pha ảnh mờ + sáng nhẹ, vẫn thấy cảnh thật)."""
    im = Image.open(path).convert("RGB")
    if crop: im = im.crop(crop)
    k = max(W / im.width, H / im.height); im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x0, y0 = (im.width - W) // 2, (im.height - H) // 2; im = im.crop((x0, y0, x0 + W, y0 + H))
    a = np.asarray(im).astype(np.float32)
    if fade:
        g = np.linspace(0, 1, W)[None, :, None]; m = np.clip((g - fade[0]) / (fade[1] - fade[0]), 0, 1) * white
        a = a * (1 - m) + np.array(PAPER, np.float32) * m
    if veil:
        b = np.asarray(im.filter(ImageFilter.GaussianBlur(5))).astype(np.float32)
        g = np.linspace(0, 1, W)[None, :, None]; m = np.clip((g - veil_x[0]) / (veil_x[1] - veil_x[0]), 0, 1)
        m = m * m * (3 - 2 * m)
        a = a * (1 - m) + (b * (1 - veil) + 255 * veil) * m
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")

def push(img, t, dur, cx, cy, z0=1.0, z1=1.06):
    z = z0 + (z1 - z0) * ease(t / dur); w, h = W / z, H / z
    x0 = min(max(cx - w / 2, 0), W - w); y0 = min(max(cy - h / 2, 0), H - h)
    return img.crop((round(x0), round(y0), round(x0 + w), round(y0 + h))).resize((W, H), Image.BILINEAR)

def layer(draw_fn, k=2, glow=0, glow_a=0.6):
    """Vẽ ở 1/k độ phân giải rồi phóng (nhanh); glow>0 thêm quầng mờ cùng màu."""
    L = Image.new("RGBA", (W // k, H // k)); draw_fn(ImageDraw.Draw(L), 1 / k)
    if glow:
        g = L.filter(ImageFilter.GaussianBlur(glow / k))
        if glow_a != 1: g.putalpha(g.getchannel("A").point(lambda v: int(v * glow_a)))
        L = Image.alpha_composite(g, L)
    return L.resize((W, H), Image.BILINEAR)

def shadow_of(L, blur=10, dy=6, a=0.35):
    s = Image.new("RGBA", L.size, (0, 0, 0, 0)); al = L.getchannel("A").point(lambda v: int(v * a))
    s.putalpha(al); s = s.filter(ImageFilter.GaussianBlur(blur)); out = Image.new("RGBA", L.size); out.alpha_composite(s, (0, dy)); return out

def poly_mask(pts, x_cut=None, feather=5, y_cut=None):
    m = Image.new("L", (W, H)); ImageDraw.Draw(m).polygon([tuple(p) for p in pts], fill=255)
    a = np.asarray(m).copy()
    if x_cut is not None: a[:, max(0, int(x_cut)):] = 0
    if y_cut is not None: a[max(0, int(y_cut)):, :] = 0
    return Image.fromarray(a).filter(ImageFilter.GaussianBlur(feather))

def _arrow(d, tip, ux, uy, size, col, s):
    nx, ny = -uy, ux; b = (tip[0] - ux * size, tip[1] - uy * size)
    d.polygon([(tip[0] * s, tip[1] * s), ((b[0] + nx * size * 0.62) * s, (b[1] + ny * size * 0.62) * s),
               ((b[0] - nx * size * 0.62) * s, (b[1] - ny * size * 0.62) * s)], fill=col)

def wavy(src, dst, prog, ph, amp=12, wl=110, off=0.0):
    """Điểm trên đường sóng src→dst (đã chạy tới prog 0..1), lệch ngang off."""
    dx, dy = dst[0] - src[0], dst[1] - src[1]; Ln = math.hypot(dx, dy); ux, uy = dx / Ln, dy / Ln; nx, ny = -uy, ux
    pts = []
    for i in range(0, max(2, int(Ln * prog)), 5):
        w = amp * math.sin((i - ph) / wl * 2 * math.pi) * min(1, i / 40)
        pts.append((src[0] + ux * i + nx * (off + w), src[1] + uy * i + ny * (off + w)))
    return pts, ux, uy

RAYS = True                                                   # True: tia thẳng bay chậm · False: sóng uốn lượn (bản v7)
def heat_waves(fr, t, src, dst, n, start, run=1.0, spread=200, amp=13, wl=120, c0=HEAT0, c1=HEAT1, width=8,
               alpha=1.0, fade_out=None, stagger=0.12, arrow=True, speed=360):
    """n sóng cam→đỏ có đầu mũi tên chạy từ src tới dst trong `run` giây (lệch nhau stagger)."""
    def dr(d, s):
        for k in range(n):
            off = (k - (n - 1) / 2) * spread / max(1, n - 1); t0 = start + k * stagger
            prog = ease(lin(t, t0, t0 + run * (1.35 if RAYS else 1.0)))   # bay chậm hơn
            if prog <= 0.02: continue
            al = alpha * min(1, (t - t0) / 0.25)
            if fade_out: al *= 1 - ease(lin(t, *fade_out))
            if al <= 0.01: continue
            if RAYS: pts, ux, uy = wavy(src, dst, prog, 0, 0, wl, off)          # tia THẲNG, không uốn lượn (anh chốt 19/11)
            else: pts, ux, uy = wavy(src, dst, prog, t * speed, amp, wl, off)
            N = len(pts)
            for j in range(N - 1):
                u = j / max(1, N - 1); c = mix(c0, c1, u)
                d.line([(pts[j][0] * s, pts[j][1] * s), (pts[j + 1][0] * s, pts[j + 1][1] * s)], fill=c + (int(255 * al * min(1, u * 4 + 0.15)),), width=max(1, round(width * s)))
            if RAYS and N > 6:                                                   # đốm sáng trôi CHẬM dọc tia
                for ph in (0.0, 0.5):
                    q = ((t - t0) * 0.35 + ph) % 1.0; j = int(q * (N - 2))
                    a2 = int(200 * al * math.sin(q * math.pi))
                    j2 = min(N - 1, j + 5)
                    d.line([(pts[j][0] * s, pts[j][1] * s), (pts[j2][0] * s, pts[j2][1] * s)], fill=(255, 245, 220, a2), width=max(1, round((width + 2) * s)))
            if arrow and N > 3:
                a, b = pts[-4], pts[-1]; L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
                _arrow(d, (b[0] + (b[0] - a[0]) / L * 14, b[1] + (b[1] - a[1]) / L * 14), (b[0] - a[0]) / L, (b[1] - a[1]) / L, 30, c1 + (int(255 * al),), s)
    fr.alpha_composite(layer(dr, 2, 16, 0.55))

def reflect(fr, t, pts_from, direction, start, length=360, col=(255, 255, 255), edge=(170, 190, 215), width=7, stagger=0.1, run=0.7, alpha=1.0, fade_out=None):
    """Tia sáng thẳng có mũi tên dội ngược khỏi kính (style mẫu 6): lõi trắng, viền bạc-xanh nhạt."""
    ux, uy = direction; Ln = math.hypot(ux, uy); ux, uy = ux / Ln, uy / Ln
    def dr(d, s):
        for k, p in enumerate(pts_from):
            q = ease(lin(t, start + k * stagger, start + k * stagger + run))
            if q <= 0.02: continue
            al = alpha * (1 - (ease(lin(t, *fade_out)) if fade_out else 0))
            e = (p[0] + ux * length * q, p[1] + uy * length * q)
            d.line([(p[0] * s, p[1] * s), (e[0] * s, e[1] * s)], fill=edge + (int(230 * al),), width=max(1, round((width + 6) * s)))
            d.line([(p[0] * s, p[1] * s), (e[0] * s, e[1] * s)], fill=col + (int(255 * al),), width=max(1, round(width * s)))
            _arrow(d, (e[0] + ux * 22, e[1] + uy * 22), ux, uy, 30, edge + (int(240 * al),), s)
            _arrow(d, (e[0] + ux * 16, e[1] + uy * 16), ux, uy, 20, col + (int(255 * al),), s)
    L = layer(dr, 2, 14, 0.8); fr.alpha_composite(shadow_of(L, 8, 4, 0.18)); fr.alpha_composite(L)

def _shield_poly(cx, cy, r):
    pts = []
    for i in range(41):                                       # mép trên lõm nhẹ giữa
        x = -1 + i / 20; pts.append((x, -0.92 + 0.10 * (1 - x * x)))
    for i in range(1, 41):                                    # sườn phải thẳng rồi cong về mũi nhọn
        u = i / 40; y = -0.92 + 1.92 * u
        x = 1.0 if y < -0.15 else (1 - ((y + 0.15) / 1.15) ** 1.7) ** 0.75
        pts.append((x, y))
    for x, y in reversed(pts[42:-1]): pts.append((-x, y))
    return [(cx + r * 0.80 * x, cy + r * y) for x, y in pts]

def shield(fr, t, cx, cy, r, start, dur=0.5, alpha=1.0, glass_tint=0.55):
    """Khiên bạc kim loại: viền bạc dày + mặt kính trong suốt hơi xanh bạc, có vệt bóng. Hiện bằng scale + fade."""
    p = ease(lin(t, start, start + dur))
    if p <= 0: return
    sc = 0.75 + 0.25 * p; R = r * sc; A = alpha * p
    k = 2; S = 1 / k; big = Image.new("RGBA", (W // k, H // k)); d = ImageDraw.Draw(big)
    outer = [(x * S, y * S) for x, y in _shield_poly(cx, cy, R)]; inner = [(x * S, y * S) for x, y in _shield_poly(cx, cy + R * 0.02, R * 0.84)]
    d.polygon(outer, fill=(150, 160, 172, int(255 * A)))
    rim = Image.new("RGBA", big.size, (190, 196, 205, 255)); dr = ImageDraw.Draw(rim)             # vành bạc: gradient sáng-tối theo đường chéo
    x0 = min(p[0] for p in outer); x1 = max(p[0] for p in outer); y0 = min(p[1] for p in outer); y1 = max(p[1] for p in outer)
    for i in range(56):
        u = i / 47 - 0.08; c = mix((250, 252, 255), (120, 130, 145), abs(math.sin(u * math.pi * 1.4)))
        dr.polygon([(x0 + (x1 - x0) * u - 30, y0), (x0 + (x1 - x0) * (u + 1 / 47) - 30, y0), (x0 + (x1 - x0) * (u + 1 / 47) + 30, y1), (x0 + (x1 - x0) * u + 30, y1)], fill=c + (255,))
    m = Image.new("L", big.size); ImageDraw.Draw(m).polygon(outer, fill=int(255 * A)); rim.putalpha(m)
    big = Image.alpha_composite(big, rim)
    gl = Image.new("RGBA", big.size); dg = ImageDraw.Draw(gl)
    for i in range(30):
        u = i / 29; c = mix((235, 245, 252), (175, 195, 215), u)
        dg.rectangle((x0, y0 + (y1 - y0) * u, x1, y0 + (y1 - y0) * (u + 1 / 29) + 1), fill=c + (255,))
    m2 = Image.new("L", big.size); ImageDraw.Draw(m2).polygon(inner, fill=int(255 * A * glass_tint)); gl.putalpha(m2)
    big = Image.alpha_composite(big, gl)
    hl = Image.new("RGBA", big.size); ImageDraw.Draw(hl).polygon([(x0 + (x1 - x0) * 0.25, y0), (x0 + (x1 - x0) * 0.45, y0), (x0 + (x1 - x0) * 0.2, y1), (x0, y1)], fill=(255, 255, 255, int(120 * A)))
    m3 = Image.new("L", big.size); ImageDraw.Draw(m3).polygon(inner, fill=255); hl.putalpha(Image.fromarray(np.minimum(np.asarray(hl.getchannel("A")), np.asarray(m3))))
    big = Image.alpha_composite(big, hl.filter(ImageFilter.GaussianBlur(4)))
    L = big.resize((W, H), Image.BILINEAR)
    fr.alpha_composite(shadow_of(L, 14, 10, 0.35)); fr.alpha_composite(L)

def film_sweep(fr, pts, t, a0, a1, tint=(30, 34, 42), dark=0.3, edge=RED, vertical=False):
    """Lớp phim phủ kính từ trái→phải (hoặc trên→dưới): phủ màu khói + mép quét đỏ."""
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    lo, hi = (min(ys) - 30, max(ys) + 30) if vertical else (min(xs) - 30, max(xs) + 30)
    p = ease(lin(t, a0, a1)); c = lo + (hi - lo) * p
    if p <= 0: return
    m = poly_mask(pts, None if vertical else c, 5, c if vertical else None)
    L = Image.new("RGBA", (W, H), tint + (0,)); L.putalpha(m.point(lambda v: int(v * dark))); fr.alpha_composite(L)
    if p < 1:
        e = Image.new("RGBA", (W, H)); de = ImageDraw.Draw(e)
        if vertical: de.line((0, c, W, c), fill=edge + (255,), width=7)
        else: de.line((c, 0, c, H), fill=edge + (255,), width=7)
        e.putalpha(Image.fromarray(np.minimum(np.asarray(e.getchannel("A")), np.asarray(poly_mask(pts, None, 1)))))
        fr.alpha_composite(e.filter(ImageFilter.GaussianBlur(6))); fr.alpha_composite(e)

def beams(fr, sun, angles, length, width, col, al):
    if al <= 0: return
    def dr(d, s):
        for a, k in angles:
            x1 = sun[0] + length * math.cos(a); y1 = sun[1] + length * math.sin(a)
            for j in range(6):
                d.line([(sun[0] * s, sun[1] * s), (x1 * s, y1 * s)], fill=col + (int(al * k * 255 / 6),), width=max(1, round((width - j * width / 7) * s)))
    L = Image.new("RGBA", (W // 4, H // 4)); dr(ImageDraw.Draw(L), 1 / 4)
    fr.alpha_composite(L.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR))

def sun_glow(fr, cx, cy, r, al):
    if al <= 0: return
    L = Image.new("RGBA", (W // 4, H // 4)); d = ImageDraw.Draw(L)
    for i in range(10, 0, -1):
        rr = r * i / 10 / 4; d.ellipse((cx / 4 - rr, cy / 4 - rr, cx / 4 + rr, cy / 4 + rr), fill=(255, 250, 225, int(al * 255 * (1 - i / 11) ** 1.5)))
    fr.alpha_composite(L.filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BILINEAR))

def tint(fr, col, a):
    if a > 0: fr.alpha_composite(Image.new("RGBA", (W, H), col + (int(255 * a),)))

def red_sweep(fr, t, start=0.0, y=1046, alpha=0.85):
    """Một vệt đỏ MẢNH, thẳng, quét từ trái sang ở chân khung (anh: vạch đỏ chéo cũ rối → gọn 1 vệt)."""
    p = ease(lin(t, start, start + 0.8))
    if p <= 0: return
    def dr(d, s):
        d.line(((0, y * s), (W * p * s, y * s)), fill=RED + (int(255 * alpha),), width=max(1, round(4 * s)))
    fr.alpha_composite(layer(dr, 1, 6, 0.6))

def panel_bar(fr, t, x, y, w, val, a0, a1, icon=None, fill=RED, h=128):
    """Panel trắng bo góc, viền mảnh, đổ bóng nhẹ, dải header đỏ; thanh đo chạy tới val (0..1). Không chữ/số."""
    al = ease(lin(t, a0 - 0.6, a0 - 0.1))
    if al <= 0: return
    dy = int(18 * (1 - al))
    L = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(L); A = int(255 * al)
    d.rounded_rectangle((x, y + dy, x + w, y + h + dy), 22, fill=(255, 255, 255, int(A * 0.96)), outline=(215, 218, 224, A), width=2)
    hd = Image.new("RGBA", (W, H)); ImageDraw.Draw(hd).rounded_rectangle((x, y + dy, x + w, y + h + dy), 22, fill=RED + (A,))
    cm = Image.new("L", (W, H)); ImageDraw.Draw(cm).rectangle((x, y + dy, x + w, y + dy + 22), fill=255); hd.putalpha(Image.fromarray(np.minimum(np.asarray(hd.getchannel("A")), np.asarray(cm))))
    L.alpha_composite(hd)
    bx0 = x + (118 if icon else 34); bx1 = x + w - 34; by = y + dy + 62; bh = 30
    if icon: icon(d, x + 62, by + bh / 2, A)
    d.rounded_rectangle((bx0, by, bx1, by + bh), bh // 2, fill=(232, 233, 236, A))
    p = ease(lin(t, a0, a1)) * val
    if p > 0.005: d.rounded_rectangle((bx0, by, bx0 + max(bh, (bx1 - bx0) * p), by + bh), bh // 2, fill=fill + (A,))
    for q in (0.25, 0.5, 0.75): d.line((bx0 + (bx1 - bx0) * q, by + bh + 8, bx0 + (bx1 - bx0) * q, by + bh + 18), fill=(150, 152, 158, int(A * 0.8)), width=2)
    fr.alpha_composite(shadow_of(L, 16, 10, 0.22)); fr.alpha_composite(L)

def ico_sun(d, cx, cy, A, col=(240, 150, 30)):
    d.ellipse((cx - 17, cy - 17, cx + 17, cy + 17), fill=col + (A,))
    for i in range(8):
        a = i * math.pi / 4; d.line((cx + 25 * math.cos(a), cy + 25 * math.sin(a), cx + 35 * math.cos(a), cy + 35 * math.sin(a)), fill=col + (A,), width=5)
def ico_heat(d, cx, cy, A):
    for k in (-14, 0, 14):
        pts = [(cx + k + 6 * math.sin(i / 5), cy + 26 - i) for i in range(0, 52, 2)]; d.line(pts, fill=RED + (A,), width=5)
def ico_eye(d, cx, cy, A):
    d.ellipse((cx - 34, cy - 18, cx + 34, cy + 18), outline=INK + (A,), width=5); d.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), fill=INK + (A,))
def ico_uv(d, cx, cy, A):
    ico_sun(d, cx, cy, A, (150, 80, 230))

def outline(fr, pts, col, a, w=6):
    if a <= 0: return
    L = Image.new("RGBA", (W, H)); ImageDraw.Draw(L).line([tuple(p) for p in pts] + [tuple(pts[0])], fill=col + (int(255 * a),), width=w, joint="curve")
    fr.alpha_composite(L.filter(ImageFilter.GaussianBlur(5))); fr.alpha_composite(L)

def lens(fr, img, lx, ly, r, al, anchor, col=RED):
    """Kính lúp tròn viền trắng + vòng đỏ, nối điểm neo bằng đường đỏ mảnh + chấm."""
    if al <= 0: return
    L = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(L); A = int(255 * al)
    ang = math.atan2(anchor[1] - ly, anchor[0] - lx); ex, ey = lx + r * math.cos(ang), ly + r * math.sin(ang)
    d.line((anchor[0], anchor[1], ex, ey), fill=col + (A,), width=4); d.ellipse((anchor[0] - 9, anchor[1] - 9, anchor[0] + 9, anchor[1] + 9), fill=col + (A,), outline=(255, 255, 255, A), width=3)
    im = img.resize((2 * r, 2 * r)); m = Image.new("L", (2 * r, 2 * r)); ImageDraw.Draw(m).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=A); im.putalpha(m)
    L.alpha_composite(im, (int(lx - r), int(ly - r)))
    d.ellipse((lx - r - 8, ly - r - 8, lx + r + 8, ly + r + 8), outline=(255, 255, 255, A), width=10)
    d.ellipse((lx - r - 12, ly - r - 12, lx + r + 12, ly + r + 12), outline=col + (A,), width=4)
    fr.alpha_composite(shadow_of(L, 18, 12, 0.3)); fr.alpha_composite(L)

def framed(photo, x, y, w, h, r=36):
    """Đặt ảnh vào panel trắng bo góc đổ bóng trên nền giấy sáng (style mẫu 6). Trả (khung nền, hàm chiếu toạ độ ảnh→khung)."""
    bg = Image.new("RGBA", (W, H), PAPER + (255,))
    g = np.linspace(0, 1, H)[:, None, None]; a = np.asarray(bg).astype(np.float32)
    a[..., :3] = a[..., :3] * (1 - 0.06 * g) ; bg = Image.fromarray(a.astype(np.uint8), "RGBA")
    ph = photo.convert("RGB").resize((w, h), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (w, h)); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255); ph.putalpha(m)
    card = Image.new("RGBA", (W, H)); ImageDraw.Draw(card).rounded_rectangle((x - 10, y - 10, x + w + 10, y + h + 10), r + 8, fill=(255, 255, 255, 255))
    bg.alpha_composite(shadow_of(card, 22, 14, 0.25)); bg.alpha_composite(card); bg.alpha_composite(ph, (x, y))
    sx, sy = w / photo.width, h / photo.height
    return bg, (lambda px, py: (x + px * sx, y + py * sy))

def encode(out, n, frame):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-threads", "4", str(out)], stdin=subprocess.PIPE)
    for i in range(n): p.stdin.write(frame(i / FPS).convert("RGBA").tobytes())
    p.stdin.close(); p.wait(); print("OK", out, f"{n / FPS:.2f}s", flush=True)
