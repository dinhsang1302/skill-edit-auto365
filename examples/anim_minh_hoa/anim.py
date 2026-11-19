#!/usr/bin/env python3
"""Hoạt hình minh hoạ thông số phim (Corolla v15). Chi tiết rời do Codex vẽ trên nền đen (mặt trời, 1 tấm phim, hạt nano gốm)
+ khung hình thật trích từ clip làm nền; ghép + chuyển động + tia sáng/nhiệt/UV + thanh đo bằng code. KHÔNG có chữ số trong hình
(số lớn nằm ở lớp chữ động kin của build → sửa được trong CapCut). Tỉ lệ thanh đo = đúng số trong lời thuyết minh.
Chạy: .venv\\Scripts\\python projects\\2026-11-18_CorollaCross3M_v15\\work\\anim\\anim.py [tên cảnh…]  → work/anim/<tên>.mp4 (1920x1080, 25 fps)"""
import sys, math, subprocess, numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

D = Path(__file__).resolve().parent; PT = D / "parts"
W, H, FPS = 1920, 1080, 25
ROOT = D.parents[3]; sys.path.insert(0, str(ROOT / "scripts")); import e365 as E

def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def lin(t, a, b): return min(1, max(0, (t - a) / (b - a)))

def load_black(p, w=None):
    """Ảnh nền đen → RGBA (alpha = độ sáng) để chồng kiểu screen."""
    im = Image.open(p).convert("RGB")
    if w: im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32); al = np.clip(a.max(2) * 1.6, 0, 255)
    rgb = np.where(al[..., None] > 0, a * 255 / np.maximum(al[..., None], 1), 0)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al]).astype(np.uint8), "RGBA")

def bg_real(name, dark=0.42, blur=3):
    im = Image.open(PT / f"bg_{name}.jpg").convert("RGB").resize((W, H))
    im = ImageEnhance.Brightness(im.filter(ImageFilter.GaussianBlur(blur))).enhance(dark)
    g = np.linspace(0, 1, W)[None, :, None]; a = np.asarray(im).astype(np.float32)
    a = a * (1 - 0.55 * np.clip((g - 0.5) / 0.3, 0, 1))      # tối dần sang phải (chỗ chữ kin)
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")

def put(fr, im, cx, cy, sc=1.0, al=1.0):
    if al <= 0.01: return
    if sc != 1: im = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.BILINEAR)
    if al < 1: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * al)))
    fr.alpha_composite(im, (round(cx - im.width / 2), round(cy - im.height / 2)))

def glow_layer(draw_fn, blur=10, k=2):
    """Vẽ nét ở 1/k độ phân giải + quầng sáng → RGBA cỡ W×H."""
    L = Image.new("RGBA", (W // k, H // k)); draw_fn(ImageDraw.Draw(L), 1 / k)
    g = L.filter(ImageFilter.GaussianBlur(blur / k)); out = Image.alpha_composite(g, L)
    return out.resize((W, H), Image.BILINEAR)

def bar(fr, t, x, y, w, val, a0, a1, col, label_al=1.0):
    """Thanh đo bo tròn chạy tới val (0..1) trong [a0,a1] giây."""
    h = 26; L = Image.new("RGBA", fr.size); d = ImageDraw.Draw(L); p = ease(lin(t, a0, a1)) * val
    al = int(255 * min(1, lin(t, a0 - 0.5, a0)) * label_al)
    if al <= 0: return
    d.rounded_rectangle((x, y, x + w, y + h), h // 2, fill=(255, 255, 255, int(al * 0.16)), outline=(255, 255, 255, int(al * 0.45)), width=2)
    if p > 0.005: d.rounded_rectangle((x, y, x + max(h, int(w * p)), y + h), h // 2, fill=col + (al,))
    for q in (0.25, 0.5, 0.75): d.line((x + w * q, y + h + 6, x + w * q, y + h + 14), fill=(255, 255, 255, int(al * 0.4)), width=2)
    fr.alpha_composite(L)

def glass(fr, x, y0, y1, tint, al=1.0, thick=34):
    """Tấm kính + phim nhìn ngang (mặt cắt) ở cột x."""
    L = Image.new("RGBA", fr.size); d = ImageDraw.Draw(L); A = int(255 * al)
    d.rounded_rectangle((x - thick // 2, y0, x + thick // 2, y1), 10, fill=(170, 200, 220, int(A * 0.22)), outline=(220, 235, 245, int(A * 0.7)), width=2)
    d.rectangle((x + thick // 2 - 9, y0 + 6, x + thick // 2 - 2, y1 - 6), fill=tint + (int(A * 0.85),))   # lớp phim mặt trong
    fr.alpha_composite(L)

def encode(name, n, frame):
    out = D / f"{name}.mp4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-threads", "4", str(out)], stdin=subprocess.PIPE)
    for i in range(n): p.stdin.write(frame(i / FPS).convert("RGBA").tobytes())
    p.stdin.close(); p.wait(); print("OK", out, f"{n / FPS:.2f}s", flush=True)

SUN = load_black(PT / "sun/sun.png", 760)
FILM = load_black(PT / "film_layer/film_layer.png", 980)
NANO = Image.open(PT / "nano/nano.png").convert("RGB")
BG0 = Image.new("RGBA", (W, H), (9, 11, 15, 255))

def tinted(im, col, k=1.0):
    a = np.asarray(im).astype(np.float32); c = np.array(col, np.float32)
    rgb = a[..., :3] * 0.45 + c * 0.55; al = np.clip(a[..., 3] * k, 0, 255)
    return Image.fromarray(np.dstack([rgb, al]).astype(np.uint8), "RGBA")

# ---------- 1. Quang học ĐA LỚP + NANO GỐM (đoạn 06, 0–5,71 s) ----------
LAYERS = [((200, 210, 225), 1.6), ((120, 170, 230), 1.5), ((90, 110, 140), 1.6), ((150, 225, 255), 1.4), ((210, 190, 150), 1.5)]
FILMS = [tinted(FILM, c, k) for c, k in LAYERS]
def lens_img(r):
    im = NANO.resize((r * 2 * 16 // 9 + 40, r * 2 + 40)).crop((40, 20, 40 + 2 * r, 20 + 2 * r)).convert("RGBA")
    m = Image.new("L", (2 * r, 2 * r)); ImageDraw.Draw(m).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255); im.putalpha(m)
    return im
LENS = lens_img(200)
def f_multilayer(t):
    fr = BG0.copy(); CX, CY = 600, 560
    put(fr, SUN, 230, 160, 0.6 + 0.02 * math.sin(t * 3), min(1, t / 0.5))
    ex = ease(lin(t, 0.4, 2.4))                               # tách lớp
    n = len(FILMS)
    for i in range(n - 1, -1, -1):
        dy = (i - (n - 1) / 2) * (24 + 92 * ex); a = min(1, lin(t, 0.1 + 0.12 * i, 0.5 + 0.12 * i))
        put(fr, FILMS[i], CX, CY + dy, 0.72, a)
    # tia nắng xuyên qua từng lớp, yếu dần (kiểm soát năng lượng truyền qua kính)
    ra = lin(t, 2.6, 3.3)
    if ra > 0:
        ys = [CY + (i - (n - 1) / 2) * (24 + 92 * ex) for i in range(n)]
        def rays(d, s):
            for k in range(5):
                x0 = 300 + k * 22; x1 = CX - 160 + k * 70; ph = (t * 1.3 + k * 0.17) % 1
                pts = [(x0, 230), (x0 + (x1 - x0) * 0.35, ys[0] - 60)] + [(x1 + (y - ys[0]) * 0.18, y) for y in ys] + [(x1 + (ys[-1] + 160 - ys[0]) * 0.18, ys[-1] + 160)]
                for j in range(len(pts) - 1):
                    lv = max(0.08, 1 - 0.19 * max(0, j - 1)) * ra
                    d.line([(p[0] * s, p[1] * s) for p in pts[j:j + 2]], fill=(255, 200 - 18 * j, 90, int(255 * lv)), width=max(1, round(5 * s * lv + 1)))
        fr.alpha_composite(glow_layer(rays, 14))
    # kính lúp hạt nano gốm
    la = ease(lin(t, 1.7, 2.3)) * (1 - ease(lin(t, 5.4, 5.8)))
    if la > 0:
        lx, ly = CX + 270, CY + 90; sc = 0.75 + 0.25 * ease(lin(t, 1.7, 2.6))
        L = Image.new("RGBA", fr.size); ImageDraw.Draw(L).line((CX + 60, CY, lx - 200 * sc, ly), fill=(150, 225, 255, int(160 * la)), width=3); fr.alpha_composite(L)
        lz = LENS.resize((round(LENS.width * (1 + 0.08 * t / 6)),) * 2)
        put(fr, lz, lx, ly, sc, la)
        r = 200 * sc; L = Image.new("RGBA", fr.size); ImageDraw.Draw(L).ellipse((lx - r, ly - r, lx + r, ly + r), outline=(150, 225, 255, int(230 * la)), width=4); fr.alpha_composite(L)
    return fr

# ---------- khung chung cho kính + tia: nền thật, mặt trời trái, kính giữa, cabin phải ----------
GX, GY0, GY1 = 760, 250, 860
def rays_through(t, fr, start, val, col, n=7, bounce=0.0, wave=False, block_sparks=False):
    """n tia từ mặt trời tới kính; sau kính còn 'val' (độ dày/sáng), phần 'bounce' dội ngược."""
    ra = ease(lin(t, start, start + 0.6))
    if ra <= 0: return
    def dr(d, s):
        for k in range(n):
            y = GY0 + 60 + k * (GY1 - GY0 - 120) / (n - 1); x0 = 330
            prog = min(1, (t - start) / 0.9)                   # tia chạy tới kính
            xa = x0 + (GX - x0) * ease(prog)
            if wave:
                pts = [(x, y + 14 * math.sin((x - t * 380) / 26)) for x in range(int(x0), int(xa), 6)]
            else:
                pts = [(x0, y), (xa, y)]
            if len(pts) > 1: d.line([(p[0] * s, p[1] * s) for p in pts], fill=col + (int(230 * ra),), width=max(1, round(7 * s)))
            if prog >= 1:
                q = min(1, (t - start - 0.9) / 0.8)
                if val > 0.02:
                    xb = GX + (1180 - GX) * ease(q)
                    d.line([(GX * s, y * s), (xb * s, y * s)], fill=col + (int(230 * ra * (0.25 + 0.75 * val)),), width=max(1, round(7 * val * s + 1)))
                if bounce > 0:
                    xr = GX - 260 * ease(q)
                    d.line([(GX * s, y * s), (xr * s, (y - 120 * ease(q) * (1 if k % 2 else -1) * 0.5) * s)], fill=(255, 120, 60, int(220 * ra * bounce)), width=max(1, round(6 * s)))
                if block_sparks:
                    for j in range(3):
                        ang = (k * 1.7 + j * 2.1 + t * 7) % (2 * math.pi); rr = 18 + 10 * ((t * 5 + j) % 1)
                        d.ellipse(((GX - 30 + rr * math.cos(ang) - 3) * s, (y + rr * math.sin(ang) - 3) * s,
                                   (GX - 30 + rr * math.cos(ang) + 3) * s, (y + rr * math.sin(ang) + 3) * s), fill=(220, 160, 255, int(200 * ra)))
    fr.alpha_composite(glow_layer(dr, 12))

def scene(bgname, tint, sun_al=1.0):
    B = bg_real(bgname)
    def base(t):
        fr = B.copy(); put(fr, SUN, 230, 330, 0.5 + 0.015 * math.sin(t * 3), min(1, t / 0.4) * sun_al)
        glass(fr, GX, GY0, GY1, tint, min(1, t / 0.5)); return fr
    return base

# ---------- 2a. BLK50 truyền sáng 48 % (đoạn 07: số ở giây 3,1 của cảnh) ----------
b50 = scene("C8581", (70, 80, 95))
def f_vlt48(t):
    fr = b50(t); rays_through(t, fr, 0.3, 0.48, (255, 244, 200)); bar(fr, t, 330, 160, 560, 0.48, 2.5, 3.4, (255, 236, 170)); return fr
# ---------- 2b. BLK50 loại bỏ 56 % tổng năng lượng mặt trời (đoạn 08: số ở giây 2,7) ----------
def f_tser56(t):
    fr = b50(t); rays_through(t, fr, 0.2, 0.44, (255, 150, 70), wave=True, bounce=0.56); bar(fr, t, 330, 160, 560, 0.56, 1.9, 2.8, (235, 60, 50)); return fr
# ---------- 3. BLK15 truyền sáng ~14 % (đoạn 10: số ở giây 2,3) ----------
b15 = scene("C8671", (35, 38, 45))
def f_vlt14(t):
    fr = b15(t); rays_through(t, fr, 0.2, 0.14, (255, 244, 200)); bar(fr, t, 330, 160, 560, 0.14, 1.5, 2.4, (255, 236, 170)); return fr
# ---------- 4. Cản UV 99,9 % (đoạn 11: số ở giây 1,5) ----------
buv = scene("C8670", (60, 66, 80), sun_al=0.8)
def f_uv999(t):
    fr = buv(t); rays_through(t, fr, 0.0, 0.0, (190, 110, 255), wave=True, block_sparks=True); bar(fr, t, 330, 160, 560, 0.999, 0.9, 1.9, (175, 110, 255)); return fr

SCENES = dict(multilayer=(f_multilayer, 6.3), vlt48=(f_vlt48, 5.6), tser56=(f_tser56, 5.1), vlt14=(f_vlt14, 4.7), uv999=(f_uv999, 4.0))
if __name__ == "__main__":
    E.start_cpu_watch(D.parents[1] / "work/cpu_watch.log", 50) if hasattr(E, "start_cpu_watch") else None
    for k in (sys.argv[1:] or SCENES):
        f, dur = SCENES[k]; encode(k, round(dur * FPS), f)
