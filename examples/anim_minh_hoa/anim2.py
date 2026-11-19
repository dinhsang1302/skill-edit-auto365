#!/usr/bin/env python3
"""Hoạt hình minh hoạ tính năng TRÊN ẢNH RENDER CHÂN THỰC (Codex vẽ, work/anim/real/r_*/r_*.png) — anh chốt 18/11/2026.
Mỗi cảnh: ảnh render + đẩy máy chậm + hiệu ứng code (tia nắng/nhiệt/UV, lớp phim quét qua kính, kính lúp hạt nano, thanh đo).
Không có chữ/số trong hình: số lớn nằm ở lớp chữ kin của build. Tỉ lệ thanh đo = đúng số lời thuyết minh.
Chạy: .venv\\Scripts\\python projects\\2026-11-18_CorollaCross3M_v15\\work\\anim\\anim2.py [tên…] → work/anim/<tên>.mp4"""
import sys, math, numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D)); import anim as A                 # dùng lại: ease, lin, put, glow_layer, bar, encode, NANO, lens_img
W, H, ease, lin = A.W, A.H, A.ease, A.lin

def real(name):
    im = Image.open(D / f"real/{name}/{name}.png").convert("RGB").resize((W, H), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32); g = np.linspace(0, 1, W)[None, :, None]
    a = a * (1 - 0.62 * np.clip((g - 0.55) / 0.3, 0, 1))      # tối dần sang phải: chỗ chữ kin
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")

def push(img, t, dur, cx, cy, z0=1.0, z1=1.07):
    """Đẩy máy chậm về (cx,cy)."""
    z = z0 + (z1 - z0) * ease(t / dur); w, h = W / z, H / z
    x0 = min(max(cx - w / 2, 0), W - w); y0 = min(max(cy - h / 2, 0), H - h)
    return img.crop((round(x0), round(y0), round(x0 + w), round(y0 + h))).resize((W, H), Image.BILINEAR)

def beams(sun, angles, length, width, col, al):
    """Chùm tia nắng mềm toả từ mặt trời (god rays)."""
    def dr(d, s):
        for a, k in angles:
            x1 = sun[0] + length * math.cos(a); y1 = sun[1] + length * math.sin(a)
            for j in range(6):
                d.line([(sun[0] * s, sun[1] * s), (x1 * s, y1 * s)], fill=col + (int(al * k * 255 / 6),), width=max(1, round((width - j * width / 7) * s)))
    return A.glow_layer(dr, 26, 4)

def poly_mask(pts, x_cut=None, feather=6):
    m = Image.new("L", (W, H)); ImageDraw.Draw(m).polygon(pts, fill=255)
    if x_cut is not None:
        c = Image.new("L", (W, H))
        if x_cut > 0: ImageDraw.Draw(c).rectangle((0, 0, int(x_cut), H), fill=255)
        m = Image.fromarray(np.minimum(np.asarray(m), np.asarray(c)))
    return m.filter(ImageFilter.GaussianBlur(feather))

def film_sweep(fr, pts, t, a0, a1, tint, dark):
    """Lớp phim quét qua kính từ trái sang phải: phủ màu tối + viền sáng đầu quét."""
    xs = [p[0] for p in pts]; xa, xb = min(xs) - 40, max(xs) + 40
    p = ease(lin(t, a0, a1)); xc = xa + (xb - xa) * p
    if p <= 0: return
    m = poly_mask(pts, xc); L = Image.new("RGBA", (W, H), tint + (0,)); L.putalpha(m.point(lambda v: int(v * dark)))
    fr.alpha_composite(L)
    if p < 1:
        e = Image.new("RGBA", (W, H)); ImageDraw.Draw(e).line((xc, 0, xc, H), fill=(200, 235, 255, 230), width=6)
        e.putalpha(Image.fromarray(np.minimum(np.asarray(e.getchannel("A")), np.asarray(poly_mask(pts, None, 2)))))
        fr.alpha_composite(e.filter(ImageFilter.GaussianBlur(3))); fr.alpha_composite(e)

def waves(fr, t, src, dst, n, col, start, stop_frac=1.0, bounce=0.0, amp=12, wl=34, spread=160):
    """n sóng chạy từ src tới dst (dừng ở stop_frac quãng), phần 'bounce' dội ngược lên."""
    ra = ease(lin(t, start, start + 0.5))
    if ra <= 0: return
    dx, dy = dst[0] - src[0], dst[1] - src[1]; Ln = math.hypot(dx, dy); ux, uy = dx / Ln, dy / Ln; nx, ny = -uy, ux
    def dr(d, s):
        for k in range(n):
            off = (k - (n - 1) / 2) * spread / max(1, n - 1)
            prog = min(1, (t - start) / 1.1) * stop_frac
            pts = []
            for i in range(0, int(Ln * prog), 6):
                w = amp * math.sin((i - t * 420) / wl * 2 * math.pi / 3)
                pts.append(((src[0] + ux * i + nx * (off + w)) * s, (src[1] + uy * i + ny * (off + w)) * s))
            if len(pts) > 1: d.line(pts, fill=col + (int(235 * ra),), width=max(1, round(6 * s)))
            if bounce > 0 and prog >= stop_frac and k < round(n * bounce):
                q = min(1, (t - start - 1.1) / 0.8); ex, ey = pts[-1][0] / s, pts[-1][1] / s
                bx, by = ux - 2 * (ux * 0 + uy * 1) * 0, -abs(uy) - 0.4      # dội lên trên
                bl = 300 * ease(q); bp = []
                for i in range(0, int(bl), 6):
                    w = amp * math.sin((i + t * 420) / wl * 2 * math.pi / 3)
                    bp.append(((ex + ux * i * 0.6 + nx * w) * s, (ey + by * i * 0.9) * s))
                if len(bp) > 1: d.line(bp, fill=(255, 110, 60, int(220 * ra * (1 - 0.5 * q))), width=max(1, round(6 * s)))
    fr.alpha_composite(A.glow_layer(dr, 12))

def sparks(fr, t, cx, cy, r, col, n=26, start=0.0):
    al = ease(lin(t, start, start + 0.4))
    if al <= 0: return
    def dr(d, s):
        for j in range(n):
            ang = j * 2.399 + t * 2.5; rr = r * (0.3 + 0.7 * ((j * 0.37 + t * 1.7) % 1))
            x, y = cx + rr * math.cos(ang) * 0.35, cy + rr * math.sin(ang)
            d.ellipse(((x - 4) * s, (y - 4) * s, (x + 4) * s, (y + 4) * s), fill=col + (int(220 * al),))
    fr.alpha_composite(A.glow_layer(dr, 10))

BAR = (1180, 250, 560)                                       # thanh đo ở cột phải, trên chữ kin

# 1. Quang học ĐA LỚP + NANO GỐM — cận lớp phim bóc mép
R1 = real("r_multilayer"); LENS = A.lens_img(170)
def f_multilayer(t):
    fr = push(R1, t, 6.3, 640, 420, 1.0, 1.08).convert("RGBA")
    fr.alpha_composite(beams((60, 40), [(0.62, 1), (0.72, .8), (0.82, .7), (0.52, .6)], 1100, 70, (255, 215, 150), 0.95 * ease(lin(t, 0.2, 1.0))))
    # vệt sáng chạy dọc các lớp phim (lộ từng lớp)
    for i in range(4):
        p = lin(t, 0.6 + 0.35 * i, 1.6 + 0.35 * i)
        if 0 < p < 1:
            L = Image.new("RGBA", (W, H)); x = 260 + 900 * p
            ImageDraw.Draw(L).line((x - 240, 760 - 120 * i, x + 140, 300 - 70 * i), fill=(200, 245, 255, int(230 * math.sin(p * math.pi))), width=18)
            fr.alpha_composite(L.filter(ImageFilter.GaussianBlur(10)))
    la = ease(lin(t, 2.0, 2.6)) * (1 - ease(lin(t, 5.6, 6.1)))
    if la > 0:
        lx, ly = 860, 790; sc = 0.8 + 0.2 * ease(lin(t, 2.0, 2.9))
        L = Image.new("RGBA", (W, H)); ImageDraw.Draw(L).line((780, 560, lx - 60, ly - 150 * sc), fill=(150, 225, 255, int(200 * la)), width=3); fr.alpha_composite(L)
        ImageDraw.Draw(L).ellipse((774, 552, 786, 568), fill=(150, 225, 255, int(230 * la)))
        fr.alpha_composite(L)
        A.put(fr, LENS.resize((round(LENS.width * (1 + 0.06 * t / 6)),) * 2), lx, ly, sc, la)
        r = 170 * sc; L = Image.new("RGBA", (W, H)); ImageDraw.Draw(L).ellipse((lx - r, ly - r, lx + r, ly + r), outline=(150, 225, 255, int(235 * la)), width=4); fr.alpha_composite(L)
    return fr

# 2a. Truyền sáng 48 % — nhìn qua kính lái, lớp phim quét qua, tia nắng trong cabin dịu còn 48 %
R2 = real("r_vlt48"); WS = [(200, 95), (1400, 95), (1520, 560), (90, 560)]
def f_vlt48(t):
    fr = push(R2, t, 5.6, 640, 400).convert("RGBA")
    k = 1 - 0.52 * ease(lin(t, 1.2, 2.6))                       # sau khi phim phủ: còn 48 %
    fr.alpha_composite(beams((235, 125), [(0.55, 1), (0.75, .9), (0.95, .7), (0.38, .6)], 1250, 80, (255, 236, 190), 0.7 * k * ease(lin(t, 0.1, 0.8))))
    film_sweep(fr, WS, t, 1.2, 2.6, (25, 30, 40), 0.30)
    A.bar(fr, t, *BAR, 0.48, 2.6, 3.4, (255, 236, 170)); return fr

# 2b. Loại bỏ 56 % tổng năng lượng mặt trời — xe dưới nắng, sóng nhiệt dội khỏi kính lái
R3 = real("r_tser56"); WS3 = [(330, 330), (1110, 300), (1160, 470), (300, 480)]
def f_tser56(t):
    fr = push(R3, t, 5.1, 700, 450).convert("RGBA")
    waves(fr, t, (170, 120), (700, 380), 4, (255, 150, 70), 0.2, 1.0, bounce=0.56, spread=300, amp=9, wl=40)
    film_sweep(fr, WS3, t, 0.4, 1.4, (20, 24, 32), 0.22)
    A.bar(fr, t, *BAR, 0.56, 1.9, 2.8, (235, 60, 50)); return fr

# 3. Truyền sáng ~14 % — kính sau tối riêng tư: lớp phim quét, ánh sáng lọt rất ít, vệt bóng kính lướt qua
R4 = real("r_vlt14"); WS4 = [(330, 330), (1170, 320), (1190, 450), (300, 470)]
def f_vlt14(t):
    fr = push(R4, t, 4.7, 700, 450).convert("RGBA")
    fr.alpha_composite(beams((70, 55), [(0.45, 1), (0.6, .8), (0.3, .6)], 1000, 70, (255, 236, 190), 0.95 * (1 - 0.86 * ease(lin(t, 0.8, 2.0))) * ease(lin(t, 0, 0.6))))
    film_sweep(fr, WS4, t, 0.6, 1.8, (8, 10, 14), 0.45)
    p = lin(t, 2.4, 3.6)                                       # bóng kính lướt
    if 0 < p < 1:
        L = Image.new("RGBA", (W, H)); x = 260 + 1000 * p
        ImageDraw.Draw(L).polygon([(x, 300), (x + 90, 300), (x - 30, 500), (x - 120, 500)], fill=(255, 255, 255, int(160 * math.sin(p * math.pi))))
        L.putalpha(Image.fromarray(np.minimum(np.asarray(L.getchannel("A")), np.asarray(poly_mask(WS4, None, 2)))))
        fr.alpha_composite(L.filter(ImageFilter.GaussianBlur(6)))
    A.bar(fr, t, *BAR, 0.14, 1.5, 2.4, (255, 236, 170)); return fr

# 4. Cản tia UV 99,9 % — sóng UV tím bị kính sườn chặn trước khi tới tay người lái
R5 = real("r_uv")
def f_uv999(t):
    fr = push(R5, t, 4.0, 700, 450).convert("RGBA")
    waves(fr, t, (240, 140), (640, 460), 6, (185, 105, 255), 0.0, 0.72, spread=200, amp=10, wl=22)
    sparks(fr, t, 540, 380, 170, (205, 150, 255), start=0.9)
    # tấm chắn mờ trên mặt kính khi tia chạm
    sa = ease(lin(t, 0.8, 1.2)) * (0.55 + 0.15 * math.sin(t * 6))
    m = poly_mask([(150, 0), (1050, 0), (980, 560), (120, 600)], None, 30)
    L = Image.new("RGBA", (W, H), (170, 120, 255, 0)); L.putalpha(m.point(lambda v: int(v * 0.16 * sa))); fr.alpha_composite(L)
    A.bar(fr, t, *BAR, 0.999, 0.9, 1.9, (175, 110, 255)); return fr


def tint(fr, col, a):
    """Phủ màu cả khung (ấm → nóng, lạnh → mát)."""
    if a <= 0: return
    L = Image.new("RGBA", (W, H), col + (int(255 * a),)); fr.alpha_composite(L)

# ---- v4 (anh duyệt 19/11/2026: minh hoạ mức HIGH, không số) ----
# 5. Giảm nhiệt — cabin nắng gắt, phim phủ kính lái, sóng nhiệt dội ra, cabin dịu lại
R6 = real("r_heat"); WS6 = [(142, 120), (1162, 128), (1080, 405), (225, 398)]
def f_heat(t, dur=2.2, slow=1.0):
    fr = push(R6, t, dur, 650, 450, 1.0, 1.06).convert("RGBA")
    tint(fr, (255, 120, 30), 0.16 * (1 - ease(lin(t, 0.9 * slow, 2.0 * slow))))
    film_sweep(fr, WS6, t, 0.15 * slow, 0.9 * slow, (20, 26, 36), 0.26)
    waves(fr, t, (270, 165), (700, 640), 5, (255, 140, 60), 0.0, 0.62, bounce=0.6, spread=360, amp=10, wl=36)
    tint(fr, (90, 150, 255), 0.07 * ease(lin(t, 1.0 * slow, 2.0 * slow))); return fr

# 6. Hạn chế nhiệt lượng vào cabin (thoại "theo thông số 3M") — dài hơn, một phần sóng vẫn lọt (không số)
def f_heatcabin(t):
    fr = push(R6, t, 4.4, 600, 520, 1.03, 1.10).convert("RGBA")
    tint(fr, (255, 120, 30), 0.18 * (1 - 0.6 * ease(lin(t, 1.4, 3.0))))
    waves(fr, t, (270, 165), (760, 700), 6, (255, 140, 60), 0.1, 0.62, bounce=0.56, spread=420, amp=10, wl=36)
    film_sweep(fr, WS6, t, 0.5, 1.4, (20, 26, 36), 0.26)
    return fr

# 7. Chống tia UV — sóng UV tím bị kính sườn chặn (không số)
def f_uvshield(t):
    fr = push(R5, t, 2.5, 700, 450, 1.02, 1.08).convert("RGBA")
    waves(fr, t, (240, 140), (640, 460), 6, (185, 105, 255), 0.0, 0.72, spread=200, amp=10, wl=22)
    sparks(fr, t, 540, 380, 170, (205, 150, 255), start=0.6)
    sa = ease(lin(t, 0.6, 1.0)) * (0.55 + 0.15 * math.sin(t * 6))
    m = poly_mask([(150, 0), (1050, 0), (980, 560), (120, 600)], None, 30)
    L = Image.new("RGBA", (W, H), (170, 120, 255, 0)); L.putalpha(m.point(lambda v: int(v * 0.16 * sa))); fr.alpha_composite(L); return fr

# 8. UV + hồng ngoại đều bị cản ("cản nhiệt") — 2 loại sóng, không số
def f_irheat(t):
    fr = push(R5, t, 3.6, 700, 450, 1.0, 1.06).convert("RGBA")
    waves(fr, t, (200, 110), (640, 470), 4, (255, 95, 45), 0.0, 0.72, spread=170, amp=12, wl=30)
    waves(fr, t, (300, 90), (700, 430), 4, (185, 105, 255), 0.5, 0.72, spread=170, amp=9, wl=22)
    sparks(fr, t, 560, 390, 170, (255, 140, 80), start=0.7); sparks(fr, t, 600, 360, 150, (205, 150, 255), n=18, start=1.2)
    return fr

# 9. Cửa sổ trời — nắng rọi từ trên, phim phủ 2 tấm kính, tia nắng dịu, sóng nhiệt dội lên
R7 = real("r_sunroof"); SR1 = [(38, 262), (975, 8), (1155, 532), (308, 660)]; SR2 = [(345, 660), (1170, 578), (1252, 832), (495, 915)]
def f_sunroof(t):
    fr = push(R7, t, 4.8, 640, 460, 1.0, 1.07).convert("RGBA")
    k = 1 - 0.75 * ease(lin(t, 0.8, 2.0))
    fr.alpha_composite(beams((270, 338), [(0.35, 1), (0.6, .9), (0.85, .7), (1.1, .6)], 1100, 80, (255, 230, 170), 0.85 * k * ease(lin(t, 0.0, 0.6))))
    film_sweep(fr, SR1, t, 0.6, 1.6, (12, 16, 24), 0.42); film_sweep(fr, SR2, t, 1.0, 2.0, (12, 16, 24), 0.42)
    waves(fr, t, (270, 300), (760, 760), 4, (255, 140, 60), 1.6, 0.55, bounce=0.7, spread=300, amp=9, wl=36)
    return fr


# 10. Sơ đồ phim từng vị trí kính (nhìn từ trên) — kính lái phim sáng hơn (BLK50), kính còn lại + cửa sổ trời phim tối (BLK15)
R8 = real("r_topview")
G_WS = [(318, 320), (548, 322), (540, 705), (318, 728)]
G_REST = [[(593, 368), (968, 368), (968, 648), (597, 648)],              # cửa sổ trời
          [(1080, 330), (1200, 375), (1200, 675), (1088, 705)],          # kính hậu (kính sườn: nhìn từ trên gần như không thấy → không vẽ)
          ]
def outline(fr, pts, col, a, w=5):
    if a <= 0: return
    L = Image.new("RGBA", (W, H)); ImageDraw.Draw(L).line(pts + [pts[0]], fill=col + (int(235 * a),), width=w, joint="curve")
    fr.alpha_composite(L.filter(ImageFilter.GaussianBlur(4))); fr.alpha_composite(L)
def f_filmall(t):                                            # toàn bộ kính + cửa sổ trời cùng được dán
    fr = push(R8, t, 2.8, 760, 520, 1.0, 1.05).convert("RGBA")
    for i, g in enumerate([G_WS] + G_REST):
        film_sweep(fr, g, t, 0.1 + 0.12 * i, 0.8 + 0.12 * i, (10, 14, 22), 0.40 if i else 0.22)
        outline(fr, g, (150, 225, 255), ease(lin(t, 0.8 + 0.12 * i, 1.2 + 0.12 * i)) * (0.6 + 0.4 * math.sin(t * 5 + i)))
    return fr
def f_filmmap(t):                                            # BLK50 kính lái (xanh nhạt) · BLK15 phần còn lại (đỏ)
    fr = push(R8, t, 5.2, 760, 520, 1.0, 1.06).convert("RGBA")
    film_sweep(fr, G_WS, t, 0.2, 1.0, (10, 14, 22), 0.22)
    outline(fr, G_WS, (150, 225, 255), ease(lin(t, 0.9, 1.3)) * (0.65 + 0.35 * math.sin(t * 5)), 6)
    for i, g in enumerate(G_REST):
        film_sweep(fr, g, t, 1.2 + 0.15 * i, 2.0 + 0.15 * i, (6, 8, 12), 0.50)
        outline(fr, g, (235, 60, 50), ease(lin(t, 2.0 + 0.15 * i, 2.4 + 0.15 * i)) * (0.65 + 0.35 * math.sin(t * 5 + 1)), 6)
    return fr

# 11. Đi đêm — nhìn gương chiếu hậu qua kính sườn trước tối: phim phủ, gương mờ đi, vòng nhắc chú ý quanh gương
R9 = real("r_night"); SIDE = [(0, 30), (390, 8), (990, 585), (0, 840)]
def f_night(t):
    fr = push(R9, t, 2.6, 450, 560, 1.02, 1.10).convert("RGBA")
    film_sweep(fr, SIDE, t, 0.1, 0.9, (4, 6, 10), 0.38)
    a = ease(lin(t, 0.9, 1.3)); r = 250 + 16 * math.sin(t * 6)
    if a > 0:
        L = Image.new("RGBA", (W, H)); ImageDraw.Draw(L).ellipse((450 - r * 1.25, 555 - r * 0.72, 450 + r * 1.25, 555 + r * 0.72), outline=(255, 190, 70, int(230 * a)), width=6)
        fr.alpha_composite(L.filter(ImageFilter.GaussianBlur(5))); fr.alpha_composite(L)
    return fr

SCENES = dict(multilayer=(f_multilayer, 6.3, 1.0), vlt48=(f_vlt48, 5.6, 1.0), tser56=(f_tser56, 5.1, 1.0), vlt14=(f_vlt14, 4.7, 1.0),
              uv999=(f_uv999, 4.0, 1.0), heat=(f_heat, 2.2, 1.0), heatcabin=(f_heatcabin, 4.4, 1.0), uvshield=(f_uvshield, 2.5, 1.0),
              irheat=(f_irheat, 3.6, 1.0), sunroof=(f_sunroof, 4.8, 1.0), filmall=(f_filmall, 2.8, 1.0), filmmap=(f_filmmap, 5.2, 1.0),
              night=(f_night, 2.6, 1.0))
if __name__ == "__main__":
    import concurrent.futures as CF
    ks = sys.argv[1:] or list(SCENES)
    if "--preview" in ks:
        ks = [k for k in ks if k != "--preview"] or list(SCENES); w, h = 640, 360; sh = Image.new("RGB", (w * len(ks), h * 2))
        for i, k in enumerate(ks):
            f, dur, sp = SCENES[k]
            for j, tt in enumerate((dur * 0.3, dur * 0.75)): sh.paste(f(tt * sp).convert("RGB").resize((w, h)), (i * w, j * h))
        sh.save(D / "preview3.jpg"); print("preview3.jpg"); sys.exit()
    def one(k):
        f, dur, sp = SCENES[k]; A.encode(k, round(dur * A.FPS), lambda t: f(t * sp))
    with CF.ThreadPoolExecutor(3) as ex: list(ex.map(one, ks))
