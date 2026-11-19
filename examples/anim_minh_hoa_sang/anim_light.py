#!/usr/bin/env python3
"""Minh hoạ tính năng NỀN SÁNG style brand phim cách nhiệt 3M (đỏ–trắng–đen) — Corolla Cross x 3M, anh yêu cầu 19/11/2026.
Mỗi cảnh = ảnh render chân thực nền trắng/xám nhạt (Codex, real/l_*/l_*.png) + hiệu ứng code (fx_light.py):
sóng nhiệt cam→đỏ có mũi tên, khiên bạc chặn + tia dội ngược, lớp phim quét kính mép đỏ, panel trắng header đỏ có thanh đo,
vệt đỏ chân khung. Không chữ/số trong hình (số ở chữ kin của build — chữ kin tự đổi đen/hộp đỏ trên các cảnh này).
Tỉ lệ thanh đo = đúng số lời thoại; độ dài + mốc thanh đo giữ như bản tối cũ (work/anim/anim2.py).
Chép vào <dự án>/work/anim_light/ cùng scripts/fx_light.py, ảnh nền ở real/<tên>/<tên>.png. Chạy: <python> anim_light.py [tên…] [--preview]
      → work/anim_light/<tên>.mp4 (1920x1080 25 fps) · --preview → preview_sheet.jpg (6 khung mỗi cảnh)"""
import sys, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
D = Path(__file__).resolve().parent; sys.path.insert(0, str(D))
import fx_light as F
from fx_light import W, H, ease, lin, RED, INK
R = lambda n, **k: F.base(D / f"real/{n}/{n}.png", **k)
BAR = (1180, 140, 560)                                       # panel thanh đo: cột phải, trên chữ kin

# 1. Quang học ĐA LỚP + NANO GỐM — mép phim bóc lộ nhiều lớp, vệt sáng chạy dọc từng lớp, kính lúp hạt nano gốm
R1 = R("f_multilayer")
NANO = Image.open(D.parent / "anim/parts/nano/nano.png").convert("RGB").crop((450, 330, 950, 830))
EDGE = [(285, 880), (500, 705), (700, 565), (850, 445), (975, 335)]          # mép phim bóc (đo lưới 100px trên f_multilayer)
def along(pts, u):
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]; L = sum(seg) * u
    for i, s in enumerate(seg):
        if L <= s: k = L / s; return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k)
        L -= s
    return pts[-1]
def f_multilayer(t):
    fr = F.push(R1, t, 6.3, 760, 470, 1.0, 1.07).convert("RGBA")
    F.sun_glow(fr, 40, 60, 480, 0.6 * ease(lin(t, 0, 0.6)))
    for i, (dy, col) in enumerate([(0, (255, 255, 255)), (26, (226, 32, 40)), (52, (200, 220, 240)), (78, (226, 32, 40))]):   # vệt sáng dọc từng lớp
        p = lin(t, 0.5 + 0.4 * i, 1.9 + 0.4 * i)
        if 0 < p < 1:
            pts = [(x, y + dy * 0.6) for x, y in EDGE]; a = along(pts, max(0, p - 0.3)); b = along(pts, p)
            def dr(d, s, a=a, b=b, col=col, p=p): d.line((a[0] * s, a[1] * s, b[0] * s, b[1] * s), fill=col + (int(255 * math.sin(p * math.pi)),), width=max(1, round(9 * s)))
            fr.alpha_composite(F.layer(dr, 2, 18, 0.9))
    la = ease(lin(t, 2.0, 2.6)) * (1 - ease(lin(t, 5.7, 6.2)))
    F.lens(fr, NANO.resize((round(NANO.width * (1 + 0.05 * t)),) * 2).crop((0, 0, 500, 500)), 1000, 760, round(150 + 20 * ease(lin(t, 2.0, 2.9))), la, (760, 520))
    F.red_sweep(fr, t, 0.2); return fr

# 2a. Truyền sáng 48 % — nhìn qua kính lái: phim phủ, nắng trong cabin dịu lại, thanh đo 48 %
R2 = R("f_vlt48"); WS2 = [(155, 140), (790, 100), (1390, 40), (1920, 30), (1920, 560), (1800, 662), (900, 655), (390, 600)]
def f_vlt48(t):
    fr = F.push(R2, t, 5.6, 700, 420).convert("RGBA")
    k = 1 - 0.52 * ease(lin(t, 1.2, 2.6))
    F.sun_glow(fr, 270, 150, 480, 0.8 * k)
    F.beams(fr, (270, 150), [(0.55, 1), (0.8, .9), (1.05, .7), (0.35, .6)], 1100, 70, (255, 236, 190), 0.75 * k * ease(lin(t, 0.1, 0.8)))
    F.film_sweep(fr, WS2, t, 1.2, 2.6, (40, 46, 56), 0.30)
    F.panel_bar(fr, t, *BAR, 0.48, 2.6, 3.4, F.ico_eye, INK); F.red_sweep(fr, t, 0.3); return fr

# 2b. Loại bỏ 56 % tổng năng lượng mặt trời — sóng nhiệt tới kính lái, phim + khiên bạc, ~56 % sóng dội ngược
R3 = R("f_tser56"); WS3 = [(385, 280), (770, 268), (985, 438), (470, 442)]
def f_tser56(t):
    fr = F.push(R3, t, 5.1, 700, 450).convert("RGBA")
    F.sun_glow(fr, 200, 130, 520, 0.8)
    F.film_sweep(fr, WS3, t, 0.3, 1.2, (30, 34, 42), 0.22)
    for k, (a, b) in enumerate([((-60, 40), (560, 280)), ((-60, 150), (620, 320)), ((-60, 260), (600, 380)), ((-60, 370), (540, 400))]):
        F.heat_waves(fr, t, a, b, 1, 0.2 + 0.1 * k, run=0.9, spread=0)
    F.heat_waves(fr, t, (760, 360), (900, 400), 2, 1.6, run=0.6, spread=40, width=4, alpha=0.5, c0=(255, 210, 140), c1=(240, 120, 70))
    F.shield(fr, t, 660, 330, 82, 1.0, 0.5, 1.0, 0.45)
    F.reflect(fr, t, [(570, 290), (610, 330), (600, 380)], (-0.55, -1.0), 1.4, length=300)
    F.panel_bar(fr, t, *BAR, 0.56, 1.9, 2.8, F.ico_heat); F.red_sweep(fr, t, 0.2); return fr

# 3. Truyền sáng ~14 % — kính sau phủ phim tối riêng tư, ánh sáng lọt rất ít, bóng kính lướt
R4 = R("f_vlt14"); WS4a = [(210, 115), (770, 200), (855, 530), (270, 600)]; WS4b = [(820, 215), (1000, 290), (1125, 375), (1070, 495), (985, 522), (905, 525)]
def f_vlt14(t):
    fr = F.push(R4, t, 4.7, 650, 420).convert("RGBA")
    F.sun_glow(fr, 30, 20, 520, 0.9)
    F.beams(fr, (30, 20), [(0.45, 1), (0.6, .8), (0.3, .6)], 1000, 70, (255, 236, 190), 0.9 * (1 - 0.86 * ease(lin(t, 0.8, 2.0))) * ease(lin(t, 0, 0.6)))
    F.film_sweep(fr, WS4a, t, 0.6, 1.6, (10, 12, 16), 0.62); F.film_sweep(fr, WS4b, t, 0.9, 1.8, (10, 12, 16), 0.62)
    p = lin(t, 2.4, 3.6)
    if 0 < p < 1:
        import numpy as np
        L = Image.new("RGBA", (W, H)); x = 120 + 1000 * p
        ImageDraw.Draw(L).polygon([(x, 110), (x + 90, 110), (x - 50, 600), (x - 140, 600)], fill=(255, 255, 255, int(150 * math.sin(p * math.pi))))
        m = np.maximum(np.asarray(F.poly_mask(WS4a, None, 2)), np.asarray(F.poly_mask(WS4b, None, 2)))
        L.putalpha(Image.fromarray(np.minimum(np.asarray(L.getchannel("A")), m))); fr.alpha_composite(L.filter(ImageFilter.GaussianBlur(5)))
    F.panel_bar(fr, t, *BAR, 0.14, 1.5, 2.4, F.ico_eye, INK); F.red_sweep(fr, t, 0.2); return fr

# 4. Cản tia UV 99,9 % — sóng UV tím tới kính sườn, khiên bạc chặn, tia dội ngược, không tới tay người lái
R5 = R("f_uv"); WS5 = [(110, 215), (500, 250), (720, 340), (990, 540), (1000, 735), (190, 712)]
def uv_block(fr, t, s0):
    F.film_sweep(fr, WS5, t, s0, s0 + 0.8, (30, 34, 50), 0.16)
    F.heat_waves(fr, t, (-60, 60), (330, 400), 5, s0, run=0.8, spread=300, amp=10, wl=70, c0=F.UV0, c1=F.UV1, stagger=0.08)
    F.shield(fr, t, 440, 450, 150, s0 + 0.6)
    F.reflect(fr, t, [(350, 360), (390, 420), (430, 480)], (-0.75, -1.0), s0 + 0.9, length=300, edge=(190, 160, 240))
def f_uv999(t):
    fr = F.push(R5, t, 4.0, 650, 450).convert("RGBA"); F.sun_glow(fr, 120, 40, 420, 0.7)
    uv_block(fr, t, 0.0); F.panel_bar(fr, t, *BAR, 0.999, 0.9, 1.9, F.ico_uv, RED); F.red_sweep(fr, t, 0.2); return fr
def f_uvshield(t):
    fr = F.push(R5, t, 2.5, 650, 450, 1.02, 1.08).convert("RGBA"); F.sun_glow(fr, 120, 40, 420, 0.7)
    uv_block(fr, t, 0.0); F.red_sweep(fr, t, 0.1); return fr

# 5. Giảm nhiệt (style mẫu 4) — sóng nhiệt cam→đỏ xuyên kính sườn tới ghế; phim phủ → khiên bạc chặn, sóng dội ngược
R6 = R("f_heat"); WS6 = [(60, 560), (230, 290), (500, 125), (1000, 120), (1110, 180), (1215, 460), (1165, 615), (480, 795), (170, 660)]
SEAT = [(800, 330), (820, 420), (800, 520), (780, 610)]
def seat_waves(fr, t, start, n, run, fade_out=None, alpha=1.0):
    for k in range(n):
        F.heat_waves(fr, t, (-80, 260 + 95 * k), SEAT[k % 4], 1, start + 0.1 * k, run=run, spread=0, alpha=alpha, fade_out=fade_out)
def f_heat(t):
    fr = F.push(R6, t, 2.2, 650, 450, 1.0, 1.05).convert("RGBA")
    F.tint(fr, (255, 140, 40), 0.10 * (1 - ease(lin(t, 0.9, 1.8))))
    seat_waves(fr, t, 0.0, 4, 0.7, fade_out=(0.9, 1.3))
    F.film_sweep(fr, WS6, t, 0.6, 1.3, (30, 34, 42), 0.22)
    F.shield(fr, t, 560, 450, 150, 1.0, 0.4)
    F.heat_waves(fr, t, (-80, 330), (430, 440), 3, 1.2, run=0.5, spread=200)
    F.reflect(fr, t, [(470, 380), (480, 450), (490, 520)], (-0.8, -1.0), 1.5, length=260, run=0.5)
    F.red_sweep(fr, t, 0.0); return fr

# 6. Hạn chế MỘT PHẦN nhiệt lượng vào cabin — sau phim: đa số sóng dội ngược, vài sóng mảnh nhạt vẫn tới ghế (không số)
def f_heatcabin(t):
    fr = F.push(R6, t, 4.4, 640, 470, 1.03, 1.09).convert("RGBA")
    F.tint(fr, (255, 140, 40), 0.10 * (1 - 0.7 * ease(lin(t, 1.4, 2.8))))
    seat_waves(fr, t, 0.1, 4, 0.8, fade_out=(1.3, 1.8))
    F.film_sweep(fr, WS6, t, 0.6, 1.5, (30, 34, 42), 0.22)
    F.shield(fr, t, 560, 450, 150, 1.4, 0.5)
    F.heat_waves(fr, t, (-80, 300), (430, 440), 4, 1.8, run=0.6, spread=260)
    F.reflect(fr, t, [(470, 370), (480, 440), (490, 510)], (-0.8, -1.0), 2.2, length=280, run=0.6)
    F.heat_waves(fr, t, (640, 520), (850, 600), 1, 2.6, run=0.8, spread=0, width=4, alpha=0.55, c0=(255, 210, 140), c1=(240, 120, 70))
    F.red_sweep(fr, t, 0.0); return fr

# 7. Cửa sổ trời — nắng rọi từ trên, phim phủ 2 tấm kính (mép quét đỏ), nắng dịu, sóng nhiệt dội ngược lên
R7 = R("l_sunroof"); SR1 = [(240, 80), (1690, 80), (1440, 465), (490, 465)]; SR2 = [(510, 505), (1410, 505), (1300, 690), (605, 690)]
def f_sunroof(t):
    fr = F.push(R7, t, 4.8, 960, 420, 1.0, 1.06).convert("RGBA")
    k = 1 - 0.7 * ease(lin(t, 0.8, 2.0))
    F.beams(fr, (420, 140), [(1.0, 1), (1.25, .9), (1.5, .7), (0.75, .6)], 1000, 80, (255, 236, 190), 0.8 * k * ease(lin(t, 0, 0.6)))
    F.film_sweep(fr, SR1, t, 0.6, 1.6, (20, 24, 32), 0.45); F.film_sweep(fr, SR2, t, 1.0, 2.0, (20, 24, 32), 0.45)
    F.heat_waves(fr, t, (420, 120), (900, 470), 4, 0.1, run=0.8, spread=360, fade_out=(1.6, 2.2))
    F.shield(fr, t, 960, 380, 130, 1.9)
    F.reflect(fr, t, [(880, 330), (960, 300), (1040, 330)], (0.15, -1.0), 2.2, length=260)
    F.red_sweep(fr, t, 0.2); return fr

# 8. Phim cho TOÀN BỘ kính + cửa sổ trời (nhìn từ trên) · sơ đồ mã phim: kính lái phim sáng (viền đen), còn lại phim tối (viền đỏ)
R8 = R("f_topview2"); G_WS = [(345, 325), (528, 345), (528, 700), (330, 765), (270, 620), (268, 450)]
G_REST = [[(568, 388), (915, 395), (918, 650), (568, 655)],                       # cửa sổ trời
          [(1020, 365), (1090, 370), (1145, 430), (1155, 640), (1110, 725), (1025, 705)],   # kính hậu
          [(440, 310), (1000, 322), (950, 345), (530, 350)],                     # kính sườn trái
          [(440, 770), (700, 708), (990, 712), (1005, 742), (905, 770), (470, 778)]]                     # kính sườn phải
def f_filmall(t):
    fr = F.push(R8, t, 2.8, 620, 540, 1.0, 1.04).convert("RGBA")
    for i, g in enumerate([G_WS] + G_REST):
        F.film_sweep(fr, g, t, 0.1 + 0.12 * i, 0.8 + 0.12 * i, (10, 12, 16), 0.30 if i == 0 else 0.45)
        F.outline(fr, g, RED, ease(lin(t, 0.8 + 0.12 * i, 1.2 + 0.12 * i)) * (0.7 + 0.3 * math.sin(t * 5 + i)))
    F.red_sweep(fr, t, 0.0); return fr
def f_filmmap(t):
    fr = F.push(R8, t, 5.2, 620, 540, 1.0, 1.05).convert("RGBA")
    F.film_sweep(fr, G_WS, t, 0.2, 1.0, (10, 12, 16), 0.25)
    F.outline(fr, G_WS, INK, ease(lin(t, 0.9, 1.3)) * (0.75 + 0.25 * math.sin(t * 5)), 6)
    for i, g in enumerate(G_REST):
        F.film_sweep(fr, g, t, 1.2 + 0.15 * i, 2.0 + 0.15 * i, (6, 8, 10), 0.55)
        F.outline(fr, g, RED, ease(lin(t, 2.0 + 0.15 * i, 2.4 + 0.15 * i)) * (0.75 + 0.25 * math.sin(t * 5 + 1)), 6)
    F.red_sweep(fr, t, 0.0); return fr

# 9. Đi đêm — ảnh đêm KÍN KHUNG (v7: bỏ panel trắng trên nền giấy): phim phủ kính sườn, gương mờ đi, vòng đỏ nhắc quan sát gương
NB = R("l_night")
SIDE = [(0, 0), (1290, 0), (1350, 600), (1340, 705), (0, 890)]
def f_night(t):
    fr = F.push(NB, t, 2.6, 700, 450, 1.0, 1.05).convert("RGBA")
    F.film_sweep(fr, SIDE, t, 0.1, 0.9, (4, 6, 10), 0.40)
    a = ease(lin(t, 0.9, 1.3)); cx, cy = 675, 435; r = 1 + 0.03 * math.sin(t * 6)
    if a > 0:
        L = Image.new("RGBA", (W, H)); ImageDraw.Draw(L).ellipse((cx - 390 * r, cy - 295 * r, cx + 390 * r, cy + 295 * r), outline=RED + (int(255 * a),), width=7)
        fr.alpha_composite(L.filter(ImageFilter.GaussianBlur(6))); fr.alpha_composite(L)
    F.red_sweep(fr, t, 0.0); return fr

# 10. Kiểm soát năng lượng mặt trời truyền qua kính — nắng chiếu kính sườn: sóng nhiệt + tia sáng; phim phủ → phần lớn dội ra, ánh sáng dịu vào cabin
R10 = R("f_solar"); WS10 = [(110, 300), (480, 345), (700, 440), (930, 610), (830, 700), (830, 790), (170, 775)]
def f_solar(t):
    fr = F.push(R10, t, 3.2, 700, 520, 1.0, 1.05).convert("RGBA")
    k = 1 - 0.6 * ease(lin(t, 0.9, 1.9))
    F.sun_glow(fr, 120, 50, 380, 0.5 * k); F.beams(fr, (120, 50), [(0.55, 1), (0.75, .9), (0.95, .7), (1.15, .5)], 1000, 70, (255, 236, 190), 0.7 * k * ease(lin(t, 0, 0.6)))
    F.heat_waves(fr, t, (60, 40), (380, 470), 4, 0.1, run=0.8, spread=300, fade_out=(1.4, 1.9))
    F.film_sweep(fr, WS10, t, 0.8, 1.7, (30, 34, 42), 0.24)
    F.shield(fr, t, 430, 540, 140, 1.5)
    F.heat_waves(fr, t, (60, 40), (330, 440), 3, 1.6, run=0.6, spread=180)
    F.reflect(fr, t, [(350, 470), (390, 530), (430, 590)], (-0.7, -1.0), 1.8, length=300)
    F.red_sweep(fr, t, 0.1); return fr

# 11. UV + hồng ngoại ("cản nhiệt") — hai loại sóng (cam→đỏ, tím) cùng bị khiên bạc chặn và dội ngược (không số)
def f_irheat(t):
    fr = F.push(R10, t, 3.6, 700, 520, 1.0, 1.05).convert("RGBA")
    F.film_sweep(fr, WS10, t, 0.0, 0.8, (30, 34, 42), 0.22)
    F.heat_waves(fr, t, (40, 120), (330, 520), 3, 0.0, run=0.8, spread=200)
    F.heat_waves(fr, t, (160, 0), (420, 450), 3, 0.5, run=0.8, spread=200, amp=10, wl=70, c0=F.UV0, c1=F.UV1)
    F.shield(fr, t, 440, 540, 150, 0.8)
    F.reflect(fr, t, [(350, 470), (390, 530), (430, 590)], (-0.7, -1.0), 1.2, length=300)
    F.reflect(fr, t, [(470, 450), (510, 500)], (-0.3, -1.0), 1.6, length=280, edge=(190, 160, 240))
    F.red_sweep(fr, t, 0.1); return fr

SCENES = dict(multilayer=(f_multilayer, 6.3), vlt48=(f_vlt48, 5.6), tser56=(f_tser56, 5.1), vlt14=(f_vlt14, 4.7),
              uv999=(f_uv999, 4.0), heat=(f_heat, 2.2), heatcabin=(f_heatcabin, 4.4), uvshield=(f_uvshield, 2.5),
              irheat=(f_irheat, 3.6), sunroof=(f_sunroof, 4.8), filmall=(f_filmall, 2.8), filmmap=(f_filmmap, 5.2),
              night=(f_night, 2.6), solar=(f_solar, 3.32))   # timeline CapCut dùng 3.24 s
if __name__ == "__main__":
    args = sys.argv[1:]; prev = "--preview" in args; ks = [k for k in args if not k.startswith("--")] or list(SCENES)
    if prev:
        w, h, n = 480, 270, 6; sh = Image.new("RGB", (w * n, h * len(ks)), "white")
        for i, k in enumerate(ks):
            f, dur = SCENES[k]
            for j in range(n): sh.paste(f(dur * (j + 0.5) / n).convert("RGB").resize((w, h)), (j * w, i * h))
            ImageDraw.Draw(sh).text((6, i * h + 4), k, fill=(255, 0, 0))
        out = D / f"preview_{'_'.join(ks) if len(ks) < 4 else 'all'}.jpg"; sh.save(out, quality=85); print(out); sys.exit()
    import concurrent.futures as CF
    import os; OD = D / os.environ.get("OUT_SUB", ""); OD.mkdir(exist_ok=True)   # OUT_SUB=_new → render chờ chép (CapCut đang mở)
    def one(k): f, dur = SCENES[k]; F.encode(OD / f"{k}.mp4", round(dur * F.FPS), f)
    with CF.ThreadPoolExecutor(3) as ex: list(ex.map(one, ks))
