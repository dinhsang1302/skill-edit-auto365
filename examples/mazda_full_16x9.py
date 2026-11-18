#!/usr/bin/env python3
"""Mazda CX-5 · F10 Turbo V2 — bản đầy đủ theo kịch bản anh Việt (11/10/2026). 16:9 1920x1080 24fps.
Mỗi segment = 1 đoạn lời đọc (clip AI người dẫn hoặc mp3) + danh sách shot theo mốc thời gian NGUỒN.
Render tuần tự theo segment, cache trong work/full/seg_*.mp4 (đổi spec segment nào thì render lại segment đó).
GAP* = chỗ chừa cho 3 câu nối anh sẽ gửi (input/noi_1..3.mp3); có file thì tự thay bằng lời đọc.
Watermark ✦ ở góc phải dưới mọi clip AI → work/unwm.py. Chữ hiện chậm hơn bản 10s (anh yêu cầu 11/10).
Chạy (giới hạn tài nguyên, CLAUDE.md): taskpolicy -b ../../.venv/bin/python work/build_full.py [id…] — tuần tự, ffmpeg -threads 4,
trung gian videotoolbox, bản giao libx264 medium; kiểm ps mỗi phút, tổng > 50% máy thì chờ (log work/full/cpu.log)."""
import os, sys, json, hashlib, subprocess, numpy as np
import time
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PRJ = os.environ.get("PRJ", os.path.expanduser("~/Movies/Edit365/projects/2026-10-10_Mazda_CX-5_F10_Turbo_V2"))   # thư mục dự án
ROOT = os.environ.get("E365_ROOT", os.path.expanduser("~/Movies/Edit365"))   # thư mục xưởng
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # textfx.py cạnh file này
import textfx as T
from textfx import Word, ease, rounded, with_shadow, paste_scaled

IN, INS, SRCD = f"{PRJ}/input", f"{PRJ}/insert", f"{PRJ}/work/src"
OUT = f"{PRJ}/work/full"; os.makedirs(OUT, exist_ok=True)
FINAL = f"{PRJ}/output/F10_Turbo_V2_CX-5_full_16x9_v3.mp4"
W, H, FPS = 1920, 1080, 24
RENDER_VER = "r3"                                                   # r3: encode trung gian bằng videotoolbox (CLAUDE.md: giới hạn tài nguyên)
from unwm import unwm                                              # xoá ✦ Gemini (đảo alpha, xem work/unwm.py)
Word.IN_MASK, Word.IN_SLIDE, Word.OUT = 0.55, 0.80, 0.35          # chữ hiện chậm hơn (anh yêu cầu)
TAIL = 0.12

def ai(name): return f"{IN}/{name}"
V_NANGCAP = ai("Nâng_cấp_đèn_xe_ô_20261011114338.mp4")
V_TUVAN_MAU = ai("Tư_vấn_chọn_nhiệt_màu_20261011114718.mp4")
V_BODEN = ai("Giới_thiệu_bộ_đèn_LED_20261011114321.mp4")
V_BODY = ai("Reviewing_aluminum_flashlight_bo…_20261011114747.mp4")
V_CUM = ai("Người_nói_về_cụm_camera_20261011114740.mp4")
V_VITRI = ai("gioi_thieu_vi_tri_do.mp4")
V_GOC = ai("Presenting_car_headlight_design_…_20261011114800.mp4")
V_KIEMTRA = ai("Kiểm_tra_sau_khi_lắp_20261011114842.mp4")
V_BAMAU = ai("Giới_thiệu_đèn_xe_ô_20261011114859.mp4")
V_4300 = ai("Giới_thiệu_phiên_bản_màu_20261011114848.mp4")
V_TUVAN_SP = ai("Tư_vấn_chọn_sản_phẩm_20261011114901.mp4")
V_GIA = ai("Quảng_cáo_độ_đèn_ô_20261011114905.mp4")
A_COS, A_PHA = f"{IN}/Đây là ánh.mp3", f"{IN}/Còn đây là.mp3"
B_ZIN_COS, B_ZIN_PHA = f"{INS}/36506793.jpg", f"{INS}/36506794.jpg"     # anh xác nhận 11/10
B_F10_COS, B_F10_PHA = f"{INS}/36506846.jpg", f"{INS}/36506847.jpg"
ZIN_GAIN = 1.41                                                     # cân phơi sáng theo băng rôn (41 → 58)
K3000, K4300, K5500 = f"{INS}/03_beam_A_vang.png", f"{INS}/04_beam_A_am.png", f"{INS}/05_beam_A_trang.png"
K3000P, K4300P, K5500P = f"{INS}/06_beam_B_vang.png", f"{INS}/07_beam_B_am.png", f"{INS}/08_beam_B_trang.png"
POWER = f"{SRCD}/c9033_power.png"                                    # C9033 @23s, mặt bên hộp POWER 75/45W

# ---------------- Segments ----------------
def TL(y, x, align, *words):            # một dòng chữ động: words = (t, text, sty, size[, slide])
    return ("line", y, x, align, [w if len(w) == 5 else w + (-1 if align != "right" else 1,) for w in words])

SEGS = [
 dict(id="01_nangcap", src=V_NANGCAP, keep=[(0.28, 9.82)], shots=[
    (0.28, "cam", dict(z=(1.0, 1.0), c=(0.3, 0.35), grad="tr")),
    (2.10, "img", dict(p=B_ZIN_COS, c0=(0.42, 0.62, 0.80), c1=(0.40, 0.66, 0.66), chip="Đèn gầm zin · cos — bảng căn đèn")),
    (3.50, "img", dict(p=B_ZIN_PHA, c0=(0.42, 0.60, 0.80), c1=(0.42, 0.62, 0.68), chip="Đèn gầm zin · pha — bảng căn đèn")),
    (5.36, "cam", dict(z=(1.0, 1.0), c=(0.0, 0.3), grad="tr"))],
  titles=[TL(200, 1830, "right", (0.74, "MAZDA CX-5", "w", 120)),
          TL(250, 90, "left", (2.12, "đèn gầm", "it", 72), (2.30, "ZIN", "w", 130)),
          TL(130, 1870, "right", (7.36, "nâng cấp", "it", 64)),
          TL(250, 1870, "right", (7.70, "F10 TURBO V2", "r", 110))]),
 dict(id="02_tuvanmau", src=V_TUVAN_MAU, keep=[(0.30, 7.80)], shots=[
    (0.30, "cam", dict(z=(1.0, 1.0), c=(0.05, 0.3), grad="tr")),
    (3.36, "cardimg", dict(p=K4300, c=(0.5, 0.62, 0.9), chip="F10 Turbo V2 · 4300K · cos"))],
  titles=[TL(400, 1250, "left", (3.40, "phiên bản", "it", 72)),
          TL(620, 1240, "left", (3.84, "4300K", "r", 220)),
          TL(740, 1250, "left", (5.22, "sắc vàng nhẹ", "it", 70))]),
 dict(id="03_boden", src=V_BODEN, keep=[(0.0, 7.40)], shots=[
    (0.0, "cardvid", dict(p=f"{INS}/C9037.MP4", ss=6.0, c0=(0.5, 0.5, 1.0), c1=(0.45, 0.5, 0.8),
                          chip="Theo lời đọc · hộp in: LED 6 (BIG)+1+1")),
    (3.72, "img", dict(p=POWER, c0=(0.78, 0.66, 0.68), c1=(0.80, 0.88, 0.30), grad="tl", cap_top=False, nocap=True,
                       chip="Thông số in trên hộp: POWER 75/45W"))],
  titles=[TL(420, 1300, "left", (0.52, "LENS 3 INCH", "w", 100)),
          TL(540, 1300, "left", (1.34, "6 CHIP LED CHÍNH", "w", 76)),
          TL(650, 1300, "left", (2.60, "+ 2 MẮT TRỢ PHA", "r", 76)),
          TL(300, 90, "left", (4.70, "45W", "r", 160), (5.50, "ở cos", "it", 72)),
          TL(480, 90, "left", (5.88, "75W", "w", 160), (6.70, "ở pha", "it", 72))]),
 dict(id="04_noi1", src=f"{INS}/Person_speaking_about_lighting_c…_20261011122338.mp4", keep=[(0.80, 4.48), (4.68, 5.05)], shots=[   # cắt chữ "lắp" lặp
    (0.80, "cam", dict(z=(1.0, 1.0), c=(0.05, 0.3), grad="tr")),
    (2.20, "cardvid", dict(p=f"{INS}/C8770.MP4", ss=9.0, c0=(0.5, 0.5, 1.0), c1=(0.5, 0.5, 0.86)))],
  titles=[TL(420, 1300, "left", (2.42, "hoàn thiện", "it", 72)),
          TL(580, 1290, "left", (3.52, "ÁNH SÁNG", "w", 120))]),
 dict(id="05_body", src=V_BODY, keep=[(0.0, 9.00)], shots=[
    (0.0, "cam", dict(z=(1.0, 1.0), c=(0.5, 0.5), grad="tr")),
    (2.82, "cardvid", dict(p=f"{INS}/C9034.MP4", ss=44.0, c0=(0.5, 0.5, 1.0), c1=(0.5, 0.5, 0.8)))],
  titles=[TL(190, 1830, "right", (0.58, "BODY NHÔM", "w", 120)),
          TL(290, 1830, "right", (1.28, "màu xanh", "it", 70)),
          TL(420, 1300, "left", (4.14, "rãnh dọc thân", "it", 70)),
          TL(580, 1290, "left", (7.60, "TẢN NHIỆT", "r", 140))]),
 dict(id="06_cum", src=V_CUM, keep=[(0.0, 6.62)], shots=[
    (0.0, "cardvid", dict(p=f"{INS}/C9034.MP4", ss=18.0, c0=(0.5, 0.45, 0.9), c1=(0.5, 0.35, 0.62))),
    (3.90, "cardvid", dict(p=f"{INS}/C9034.MP4", ss=75.0, c0=(0.5, 0.5, 1.0), c1=(0.5, 0.45, 0.8)))],
  titles=[TL(460, 1300, "left", (1.02, "2 MẮT TRỢ PHA", "w", 96)),
          TL(570, 1300, "left", (2.48, "trên cụm lens", "it", 70)),
          TL(460, 1300, "left", (5.26, "QUẠT", "r", 150)),
          TL(570, 1300, "left", (5.52, "làm mát", "it", 72))]),
 dict(id="07_noi2", src=f"{INS}/Lắp_đặt_tản_nhiệt_xe_20261011122343.mp4", keep=[(1.20, 7.55)], shots=[
    (1.20, "cam", dict(z=(1.0, 1.0), c=(0.5, 0.4), grad="tl")),
    (3.04, "cardvid", dict(p=f"{INS}/IMG_3974.MOV", ss=2.0, c0=(0.5, 0.5, 1.0), c1=(0.5, 0.5, 0.9)))],
  titles=[TL(470, 1010, "left", (4.54, "chừa khoảng hở", "it", 76)),
          TL(640, 1000, "left", (5.08, "PHÍA SAU", "r", 150))]),
 dict(id="08_vitri", src=V_VITRI, keep=[(0.70, 7.75)], shots=[
    (0.70, "cam", dict(z=(1.0, 1.0), c=(0.45, 0.4), grad="tl")),
    (4.74, "cardvid", dict(p=f"{INS}/IMG_3971.MOV", ss=0.75, c0=(0.5, 0.5, 1.0), c1=(0.5, 0.5, 0.94))),
    (5.84, "cam", dict(z=(1.0, 1.0), c=(0.18, 0.42), grad="tl"))],
  titles=[TL(300, 90, "left", (0.80, "Đây là", "it", 72), (1.34, "VỊ TRÍ", "w", 130)),
          TL(470, 90, "left", (1.72, "F10 TURBO V2", "r", 150)),
          TL(470, 1010, "left", (4.80, "mặt đèn", "it", 80)),
          TL(720, 1000, "left", (5.14, "TRÒN", "r", 260)),
          TL(250, 90, "left", (5.90, "nằm trong", "it", 72)),
          TL(420, 90, "left", (6.00, "HỐC ĐÈN GẦM", "r", 150)),
          TL(520, 96, "left", (6.58, "phía dưới cản trước", "it", 66))]),
 dict(id="09_goc", src=V_GOC, keep=[(0.0, 5.30)], shots=[
    (0.0, "cam", dict(z=(1.0, 1.0), c=(0.18, 0.42), grad="tl"))],
  titles=[TL(260, 90, "left", (0.36, "nhìn từ", "it", 72), (0.46, "GÓC NÀY", "w", 130)),
          TL(420, 90, "left", (4.40, "mặt dưỡng", "it", 72))]),
 dict(id="10_noi3", src=f"{INS}/MC_presenting_car_lighting_perfo…_20261011122638.mp4", keep=[(0.55, 6.05)], shots=[
    (0.55, "cam", dict(z=(1.0, 1.0), c=(0.05, 0.3), grad="tl")),
    (3.28, "vid", dict(p=f"{INS}/DJI_20251211200549_0206_D.MP4", ss=5.0, c0=(0.5, 0.5, 1.0), c1=(0.5, 0.55, 0.92)))],
  titles=[]),                                        # chữ ở đây đè hộp trên capo → bỏ, chỉ phụ đề
 dict(id="11_cos", src=A_COS, keep=[(0.0, 6.58), (6.86, 11.50), (11.74, 15.93), (16.23, 19.98)], shots=[
    (0.0, "img", dict(p=B_F10_COS, c0=(0.42, 0.62, 0.80), c1=(0.42, 0.66, 0.64), grad="tl", chip="CX-5 sau khi lắp F10 Turbo V2 · cos · bảng căn đèn")),
    (6.80, "split", dict(a=B_ZIN_COS, b=B_F10_COS, la="ZIN", lb="F10 TURBO V2 · 4300K", chip="Cos trên bảng căn đèn · ảnh zin đã cân phơi sáng")),
    (11.66, "img", dict(p=K4300, c0=(0.5, 0.66, 0.55), c1=(0.5, 0.6, 1.0), chip="Cos 4300K")),
    (16.22, "vid", dict(p=f"{INS}/DJI_20251211200549_0206_D.MP4", ss=8.0, c0=(0.5, 0.55, 0.9), c1=(0.5, 0.5, 1.0)))],
  titles=[TL(260, 90, "left", (0.70, "ánh sáng", "it", 72), (0.70, "COS", "w", 150)),
          TL(430, 90, "left", (5.26, "nhiệt màu", "it", 72), (5.48, "4300K", "r", 150)),
          TL(260, 90, "left", (14.64, "từ giữa", "it", 72), (15.20, "tới mép đường", "it", 72))]),
 dict(id="12_pha", src=A_PHA, keep=[(0.0, 1.21), (1.40, 10.85), (11.20, 14.05)], shots=[
    (0.0, "img", dict(p=B_F10_PHA, c0=(0.42, 0.55, 0.80), c1=(0.42, 0.55, 0.66), grad="tl", chip="CX-5 · F10 Turbo V2 · pha · bảng căn đèn")),
    (1.48, "img", dict(p=K4300P, c0=(0.5, 0.6, 0.8), c1=(0.5, 0.45, 0.6), chip="Pha 4300K")),
    (3.46, "vid", dict(p=f"{INS}/DJI_20251211200507_0205_D.MP4", ss=16.3, c0=(0.5, 0.5, 1.0), c1=(0.5, 0.5, 0.9))),
    (6.82, "vid", dict(p=f"{INS}/DJI_20251211200507_0205_D.MP4", ss=21.0, c0=(0.28, 0.5, 0.62), c1=(0.72, 0.5, 0.62))),
    (11.04, "split", dict(a=B_ZIN_PHA, b=B_F10_PHA, la="ZIN", lb="F10 TURBO V2 · 4300K", chip="Kết quả tham khảo trên chiếc CX-5 này · ảnh zin đã cân phơi sáng"))],
  titles=[TL(260, 90, "left", (0.40, "ánh sáng", "it", 72), (0.56, "PHA", "w", 150)),
          TL(260, 90, "left", (1.62, "2 MẮT TRỢ PHA", "w", 110)),
          TL(370, 96, "left", (2.82, "chiếu xa", "it", 72)),
          TL(260, 90, "left", (5.60, "phủ mở", "it", 72), (6.18, "HAI BÊN", "r", 130))]),
 dict(id="13_kiemtra", src=V_KIEMTRA, keep=[(0.0, 9.62)], shots=[
    (0.0, "cam", dict(z=(1.0, 1.0), c=(0.5, 0.4), grad="tl")),
    (1.22, "img", dict(p=B_F10_COS, c0=(0.42, 0.66, 0.6), c1=(0.44, 0.66, 0.45), chip="Kiểm tra cos · pha · đường cắt trên bảng căn đèn")),
    (4.34, "cardvid", dict(p=f"{INS}/IMG_3981.MOV", ss=1.0, c0=(0.5, 0.5, 1.0), c1=(0.5, 0.5, 0.92))),
    (6.12, "cardvid", dict(p=f"{INS}/IMG_3983.MOV", ss=3.0, c0=(0.5, 0.5, 1.0), c1=(0.5, 0.5, 0.92))),
    (7.70, "cam", dict(z=(1.0, 1.0), c=(0.5, 0.4), grad="tl"))],
  titles=[TL(460, 1010, "left", (5.06, "DÂY · GIẮC", "w", 110)),
          TL(460, 1010, "left", (6.12, "QUẠT", "w", 130), (6.52, "độ kín", "it", 72))]),
 dict(id="14_bamau", src=V_BAMAU, keep=[(0.40, 10.0)], shots=[
    (0.40, "trip", dict(show={4300: 1.00, 3000: 5.54, 5500: 6.36}, hl=None))], titles=[]),
 dict(id="15_3000", src=A_PHA, keep=[(14.30, 20.53), (20.84, 24.30)], shots=[
    (14.30, "img", dict(p=K3000, c0=(0.5, 0.6, 0.8), c1=(0.5, 0.64, 0.66), chip="3000K · cos")),
    (16.48, "img", dict(p=K3000P, c0=(0.5, 0.55, 0.9), c1=(0.5, 0.5, 0.7), chip="3000K · pha")),
    (20.80, "img", dict(p=K3000, c0=(0.5, 0.66, 0.5), c1=(0.5, 0.6, 0.8), chip="3000K · cos"))],
  titles=[TL(280, 90, "left", (14.78, "3000K", "r", 170)),
          TL(390, 96, "left", (15.82, "vàng đậm", "it", 76)),
          TL(260, 90, "left", (17.20, "đường đèo", "it", 72), (18.26, "MƯA · SƯƠNG", "w", 110))]),
 dict(id="16_5500", src=A_PHA, keep=[(24.24, 24.52), (24.84, 27.59), (27.93, 32.40)], shots=[
    (24.24, "img", dict(p=K5500, c0=(0.5, 0.6, 0.8), c1=(0.5, 0.64, 0.66), chip="5500K · cos")),
    (27.44, "img", dict(p=K5500P, c0=(0.5, 0.55, 0.9), c1=(0.5, 0.5, 0.7), chip="5500K · pha"))],
  titles=[TL(280, 90, "left", (25.44, "5500K", "w", 170)),
          TL(390, 96, "left", (26.82, "ánh sáng trắng", "it", 76)),
          TL(260, 90, "left", (28.66, "đi phố", "it", 72), (29.70, "ĐƯỜNG KHÔ", "w", 110))]),
 dict(id="17_4300", src=V_4300, keep=[(0.0, 9.62)], shots=[
    (0.0, "trip", dict(show={3000: 0, 4300: 0, 5500: 0}, hl=4300)),
    (5.16, "cam", dict(z=(1.0, 1.0), c=(0.05, 0.3), grad="tr"))],
  titles=[TL(200, 1830, "right", (5.72, "nhiều cung đường", "it", 72)),
          TL(340, 1830, "right", (7.04, "VÀNG VỪA PHẢI", "w", 110))]),
 dict(id="18_tuvansp", src=V_TUVAN_SP, keep=[(0.0, 9.58)], shots=[
    (0.0, "cam", dict(z=(1.0, 1.0), c=(0.2, 0.3), grad="tr")),
    (6.12, "trip", dict(show={3000: 0, 4300: 0, 5500: 0}, hl=None))],
  titles=[TL(200, 1830, "right", (2.38, "hay đi đâu?", "it", 72)),
          TL(320, 1830, "right", (3.58, "ĐI ĐÊM NHIỀU?", "w", 100)),
          TL(420, 1830, "right", (4.76, "thích sắc sáng nào?", "it", 72))]),
 dict(id="19_gia", src=V_GIA, keep=[(0.50, 9.80)], shots=[
    (0.50, "cam", dict(z=(1.0, 1.0), c=(0.0, 0.3), grad="tr", chip="Giá và bảo hành theo lời đọc")),
    (4.40, "cam", dict(z=(1.0, 1.0), c=(0.3, 0.35), grad="tr"))],
  titles=[TL(170, 1870, "right", (1.94, "6 TRIỆU", "r", 130)),
          TL(245, 1870, "right", (2.34, "đồng / cặp", "it", 62)),
          TL(345, 1870, "right", (3.04, "BẢO HÀNH 24 THÁNG", "w", 70))]),
 dict(id="20_end", gap=3.0, shots=[(0.0, "end", {})], titles=[]),
]

# ---------------- Timeline helpers ----------------
def seg_len(s): return s["gap"] if "gap" in s else sum(b - a for a, b in s["keep"]) + TAIL
def s2o(s, t):
    if "gap" in s: return t
    o = 0
    for a, b in s["keep"]:
        if t < a: return o
        if t <= b: return o + t - a
        o += b - a
    return o
def o2s(s, o):
    if "gap" in s: return o
    for a, b in s["keep"]:
        if o <= b - a: return a + o
        o -= b - a
    return s["keep"][-1][1] + o

# ---------------- Captions ----------------
FIX = [("len 3 in", "lens 3 inch"), ("cụm len", "cụm lens"), ("căng chỉnh", "căn chỉnh"), ("CX5", "CX-5"), ("CX -5", "CX-5"),
       ("xe X5", "xe CX-5"), ("4 .300", "4300"), ("3 .000K", "3000K"), ("bảng 4300k", "bản 4300K"), ("4300k", "4300K"),
       ("3000k", "3000K"), ("5500k", "5500K"), ("nhơm", "nhôm"), ("rảnh", "rãnh"), ("tảng", "tản"), ("dắt", "giắc"),
       ("độ kính", "độ kín"), ("cạn", "cản"), ("đi lại hơn nha", "đi lại nha"), ("cốt", "cos"), ("Thì có", "thì có"),
       ("trắng Nếu", "trắng. Nếu"), ("trắng Thì", "trắng thì"), ("lắp lắp", "lắp"), ("Nên khi mà", "Nên khi")]
def words_of(path):
    b = os.path.splitext(os.path.basename(path))[0]
    d = json.load(open(f"{PRJ}/work/tx/{b}.json"))
    return [w for sg in d["segments"] for w in sg.get("words", [])]
BAD = {("nâng", "cấp"), ("ánh", "sáng"), ("cung", "đường"), ("có", "thể"), ("chiếc", "xe"), ("căn", "chỉnh"), ("căng", "chỉnh"),
       ("mặt", "đường"), ("đèn", "gầm"), ("nhiệt", "màu"), ("phía", "dưới"), ("yên", "tâm"), ("đi", "lại"), ("thực", "tế"),
       ("tư", "vấn"), ("phiên", "bản"), ("hoàn", "thiện"), ("kỹ", "thuật"), ("hệ", "thống"), ("tản", "nhiệt"), ("tảng", "nhiệt"),
       ("chiếu", "sáng"), ("khoảng", "hở"), ("trợ", "pha"), ("vàng", "đậm"), ("đường", "cắt"), ("quan", "sát"), ("phân", "bổ"),
       ("tham", "khảo"), ("F10", "Turbo"), ("Turbo", "V2"), ("Mazda", "CX"), ("CX", "-5"), ("lựa", "chọn"), ("làm", "mát")}
KEEPCAP = {"F10", "Turbo", "V2", "V2,", "LED", "Mazda", "CX", "CX5", "CX-5", "X5", "Ở"}
def _txt(c): return " ".join(x["w"] for x in c)
def captions(s):
    if "gap" in s: return []
    ws = [w for w in words_of(s["src"]) if w["e"] > s["keep"][0][0] + 0.02 and w["s"] < s["keep"][-1][1] - 0.04]
    ph, cur = [], []                                  # 1) cụm theo dấu câu / chỗ ngừng / chữ hoa đầu câu
    for w in ws:
        if cur and (w["s"] - cur[-1]["e"] > 0.3 or (w["w"][:1].isupper() and w["w"] not in KEEPCAP)): ph.append(cur); cur = []
        cur.append(w)
        if w["w"][-1] in ",.": ph.append(cur); cur = []
    if cur: ph.append(cur)
    out = []                                          # 2) gộp cụm ngắn (không vượt dấu chấm)
    for c in ph:
        if out and len(_txt(c)) < 16 and not _txt(out[-1]).endswith(".") and len(_txt(out[-1])) + len(_txt(c)) <= 48:
            out[-1] = out[-1] + c
        else: out.append(c)
    i = 0
    while i < len(out) - 1:                           # cụm ngắn sau dấu chấm → gộp với cụm sau
        if len(_txt(out[i])) < 14 and len(_txt(out[i])) + len(_txt(out[i + 1])) <= 48 and not _txt(out[i]).endswith("."):
            out[i:i + 2] = [out[i] + out[i + 1]]
        else: i += 1
    chunks = []                                       # 3) cụm dài → chia đều, tránh tách từ ghép
    for c in out:
        n = -(-len(_txt(c)) // 46)
        while n > 1:
            target = len(_txt(c)) / n; best = None
            for k in range(1, len(c)):
                cost = abs(len(_txt(c[:k])) - target) + (25 if (c[k - 1]["w"].strip(",."), c[k]["w"].strip(",.")) in BAD else 0)
                if best is None or cost < best[0]: best = (cost, k)
            chunks.append(c[:best[1]]); c = c[best[1]:]; n -= 1
        chunks.append(c)
    res = []
    for i, c in enumerate(chunks):
        txt = _txt(c)
        for a, b in FIX: txt = txt.replace(a, b)
        txt = txt.rstrip(",.")
        if i == 0 or _txt(chunks[i - 1]).endswith(".") or c[0]["w"][:1].isupper(): txt = txt[0].upper() + txt[1:]
        t0 = s2o(s, c[0]["s"]); t1 = s2o(s, chunks[i + 1][0]["s"]) if i + 1 < len(chunks) else seg_len(s)
        res.append((t0, t1, txt))
    return res

CAPF = lambda: ImageFont.truetype(os.path.expanduser("~/Library/Fonts/InterDisplay-ExtraBold.otf"), 54)
def cap_img(txt):
    f = CAPF(); w = int(f.getlength(txt)) + 60; im = Image.new("RGBA", (w, 110))
    sh = Image.new("RGBA", im.size); ImageDraw.Draw(sh).text((30, 22), txt, font=f, fill=(0, 0, 0, 230), stroke_width=6, stroke_fill=(0, 0, 0, 230))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(im).text((30, 18), txt, font=f, fill=(250, 250, 248, 255), stroke_width=3, stroke_fill=(12, 12, 14, 255))
    return im

def chip_img(txt):
    f = ImageFont.truetype(os.path.expanduser("~/Library/Fonts/Inter-SemiBold.otf"), 26)
    w = int(f.getlength(txt)) + 40; im = Image.new("RGBA", (w, 50)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, 49), 25, fill=(12, 12, 14, 170), outline=(255, 255, 255, 70), width=2)
    d.text((20, 25), txt, font=f, fill=(240, 240, 238, 255), anchor="lm"); return im

# ---------------- Media ----------------
class VReader:
    """Đọc frame tuần tự (chỉ tiến) từ ffmpeg, fps 24, khỏi giữ cả clip trong RAM."""
    def __init__(self, path, ss, w, h, vf_pre=""):
        self.w, self.h, self.i, self.last = w, h, -1, None
        vf = (vf_pre + "," if vf_pre else "") + f"fps={FPS},scale={w}:{h}:flags=lanczos"
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-threads", "4", "-ss", f"{ss:.3f}", "-i", path, "-vf", vf, "-f", "rawvideo",
                                   "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    def get(self, idx):
        n = self.w * self.h * 3
        while self.i < idx:
            b = self.p.stdout.read(n)
            if len(b) < n: break
            self.last = np.frombuffer(b, np.uint8).reshape(self.h, self.w, 3); self.i += 1
        return Image.fromarray(self.last)
    def close(self): self.p.kill()

def probe_wh(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation",
                        "-of", "json", path], capture_output=True, text=True)
    st = json.loads(r.stdout)["streams"][0]; w, h = st["width"], st["height"]
    rot = any(abs(int(sd.get("rotation", 0))) == 90 for sd in st.get("side_data_list", []))
    return (h, w) if rot else (w, h)

_IMG = {}
def load_img(p, gain=1.0):
    k = (p, gain)
    if k not in _IMG:
        im = Image.open(p).convert("RGB")
        if gain != 1: im = Image.fromarray(np.clip(np.asarray(im, np.float32) * gain, 0, 255).astype(np.uint8))
        _IMG[k] = im
    return _IMG[k]

def kb(im, c0, c1, p, ow=W, oh=H):
    """Ken Burns: c = (cx, cy, độ rộng khung theo tỉ lệ ảnh); nội suy ease theo p; giữ tỉ lệ ow:oh, kẹp trong ảnh."""
    q = ease(p) * 0.85 + p * 0.15
    cx, cy, wf = [a + (b - a) * q for a, b in zip(c0, c1)]
    iw, ih = im.size; cw = min(iw * wf, iw); ch = cw * oh / ow
    if ch > ih: ch = ih; cw = ch * ow / oh
    x = min(max(cx * iw - cw / 2, 0), iw - cw); y = min(max(cy * ih - ch / 2, 0), ih - ch)
    return im.resize((ow, oh), Image.BICUBIC, box=(x, y, x + cw, y + ch))

BG = None; VIG = None
def grade(img, k=1.05, lift=-6, grad=None):
    a = np.asarray(img.convert("RGB"), np.float32)
    a = np.clip((a - 128) * k + 128 + lift, 0, 255) * VIG
    if grad:
        gy, gx = np.mgrid[0:H, 0:W]
        gxx = (1150 - gx) / 1150 if grad == "tl" else (gx - 770) / 1150
        g = np.clip(gxx, 0, 1) * np.clip((640 - gy) / 640, 0, 1)
        a = a * (1 - 0.55 * g[..., None])
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")

def dark_blur(im):
    return Image.fromarray((np.asarray(im.convert("RGB").resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(10))
                            .resize((W, H), Image.BILINEAR), np.float32) * 0.36).astype(np.uint8)).convert("RGBA")

def card(im, maxw, maxh):
    s = min(maxw / im.width, maxh / im.height)
    return with_shadow(rounded(im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS), 30, 3, 140))

def trip_cards():
    out = {}
    for k, p in [(3000, K3000), (4300, K4300), (5500, K5500)]:
        im = load_img(p); s = min(im.size)
        sq = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2)).resize((500, 500), Image.LANCZOS)
        out[k] = with_shadow(rounded(sq, 28, 3, 140))
    return out

def end_assets():
    box = Image.open(f"{SRCD}/endcard_src.png").convert("RGB").crop((640, 120, 3200, 2160)).resize((720, 574), Image.LANCZOS)
    return with_shadow(rounded(box, 32, 3, 140)), T.cta("TƯ VẤN TẠI AUTO365")

# ---------------- Giới hạn tài nguyên (CLAUDE.md) ----------------
CPU_CAP = 50 * os.cpu_count()          # trần tổng 50% máy, tính bằng %CPU của ps (10 nhân → 500)
_last_chk = [0.0]
def cpu_total():
    out = subprocess.run(["ps", "-axo", "pcpu,comm"], capture_output=True, text=True).stdout.splitlines()[1:]
    return sum(float(l.split(None, 1)[0]) for l in out if "ffmpeg" in l or "Python" in l or "python" in l)
def cpu_guard(force=False):
    """Mỗi phút đọc ps; tổng ffmpeg + python (mọi job) vượt trần → dừng render của mình, chờ xuống dưới trần."""
    now = time.time()
    if not force and now - _last_chk[0] < 60: return
    _last_chk[0] = now
    tot = cpu_total()
    with open(f"{OUT}/cpu.log", "a") as f: f.write(f"{time.strftime('%H:%M:%S')} tổng {tot:.0f}% / trần {CPU_CAP}%\n")
    while tot > CPU_CAP:
        time.sleep(15); tot = cpu_total()
        with open(f"{OUT}/cpu.log", "a") as f: f.write(f"{time.strftime('%H:%M:%S')}   chờ: {tot:.0f}%\n")

# ---------------- Render 1 segment ----------------
def render_seg(s, path):
    global BG, VIG
    BG = T.dark_bg(W, H); VIG = T.vignette(W, H)
    D = seg_len(s); N = round(D * FPS)
    shots = [(round(s2o(s, t) * FPS), kind, prm) for t, kind, prm in s["shots"]]
    shots[0] = (0,) + shots[0][1:]
    bounds = [sh[0] for sh in shots] + [N]
    # chữ động
    words = []
    for _, y, x, align, ws in s["titles"]:
        objs = []
        for t, text, sty, size, slide in ws:
            to = s2o(s, t); end_f = min(b for b in bounds if b > round(to * FPS))
            objs.append(Word(text, sty, size, to, end_f / FPS - Word.OUT - 0.05, slide=slide))
        words += T.line(objs, y, x, align)
    caps = [(a, b, cap_img(txt)) for a, b, txt in captions(s)]
    TRIP = trip_cards() if any(k == "trip" for _, k, _ in shots) else None
    ENDA = end_assets() if any(k == "end" for _, k, _ in shots) else None
    readers = {}
    enc = subprocess.Popen(f"ffmpeg -y -loglevel error -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - "
                           f"-c:v h264_videotoolbox -b:v 12M -pix_fmt yuv420p -r {FPS} {path}", shell=True, stdin=subprocess.PIPE)
    for i in range(N):
        if i % 24 == 0: cpu_guard()
        t = i / FPS
        k = max(j for j in range(len(shots)) if shots[j][0] <= i)
        f0, kind, prm = shots[k]; f1 = bounds[k + 1]; lp = (i - f0) / max(f1 - f0, 1); li = i - f0
        nocap = prm.get("nocap", False)
        if kind == "cam":
            key = ("cam", k)
            if key not in readers: readers[key] = VReader(s["src"], 0, 1280, 720)
            src_t = o2s(s, t); fr = Image.fromarray(unwm(np.asarray(readers[key].get(int(round(src_t * FPS))))))
            z = prm["z"][0] + (prm["z"][1] - prm["z"][0]) * ease(lp)
            c = grade(T.zoom_crop(fr, z, prm["c"][0], prm["c"][1], W, H), grad=prm.get("grad"))
        elif kind == "img":
            c = grade(kb(load_img(prm["p"], prm.get("gain", 1.0)), prm["c0"], prm["c1"], lp), 1.03, -4, prm.get("grad"))
        elif kind in ("vid", "cardvid"):
            key = ("v", k)
            if key not in readers:
                vw, vh = probe_wh(prm["p"]); sc = min(1, 2560 / max(vw, vh)); readers[key] = VReader(prm["p"], prm["ss"], int(vw * sc) // 2 * 2, int(vh * sc) // 2 * 2)
            fr = readers[key].get(li)
            if kind == "vid":
                c = grade(kb(fr, prm["c0"], prm["c1"], lp), 1.03, -4)
            else:
                portrait = fr.height > fr.width
                inner = kb(fr, prm["c0"], prm["c1"], lp, *((540, 960) if portrait else (1280, 720)))
                c = dark_blur(inner); cd = card(inner, 500 if portrait else 1120, 880 if portrait else 630)
                p = ease(li / FPS / 0.4); paste_scaled(c, cd, 700 if portrait else 720, 520, (0.95 + 0.05 * p) * (1 + 0.02 * lp), p)
        elif kind == "cardimg":
            im = load_img(prm["p"]); inner = kb(im, (prm["c"][0], prm["c"][1], prm["c"][2]), (prm["c"][0], prm["c"][1], prm["c"][2] * 0.9), lp, 1120, 630)
            c = dark_blur(inner); p = ease(li / FPS / 0.4)
            paste_scaled(c, card(inner, 1000, 562), 640, 520, (0.95 + 0.05 * p) * (1 + 0.02 * lp), p)
        elif kind == "split":
            c = BG.copy()
            for j, (pp, lab, g) in enumerate([(prm["a"], prm["la"], ZIN_GAIN), (prm["b"], prm["lb"], 1.0)]):
                inner = kb(load_img(pp, g), (0.42, 0.66, 0.62), (0.42, 0.66, 0.56), lp, 880, 495)
                p = ease((li / FPS - 0.15 * j) / 0.45)
                paste_scaled(c, card(inner, 880, 495), 500 + 920 * j, 470, 0.95 + 0.05 * p, p)
                lw = Word(lab, "w" if j == 0 else "r", 64, f0 / FPS + 0.2 + 0.2 * j)
                lw.draw(c, t, int(90 + 920 * j), 820)
        elif kind == "trip":
            c = BG.copy(); xs = {3000: 400, 4300: 960, 5500: 1520}
            for kk in (3000, 5500, 4300):
                ta = s2o(s, prm["show"][kk]) if prm["show"][kk] else f0 / FPS
                if t < ta: continue
                p = ease((t - ta) / 0.5); hl = prm["hl"]
                sc = (1.08 if hl == kk else (0.92 if hl else 1.0)) * (0.94 + 0.06 * p)
                cd = TRIP[kk]
                if hl and hl != kk: cd = Image.fromarray((np.asarray(cd, np.float32) * [0.55, 0.55, 0.55, 1]).astype(np.uint8))
                paste_scaled(c, cd, xs[kk], 470, sc, p)
                Word(f"{kk}K", "r" if kk == 4300 else "w", 84, ta + 0.15).draw(c, t, xs[kk] - (110 if kk != 4300 else 120), 860)
        elif kind == "end":
            c = BG.copy(); p = ease(li / FPS / 0.3); box, cta = ENDA
            paste_scaled(c, box, 600, 540, 0.92 + 0.08 * p, p)
            for w_, x_, y_ in [(Word("X-LIGHT", "w", 80, f0 / FPS + 0.05), 1080, 420), (Word("F10", "r", 190, f0 / FPS + 0.1), 1076, 640),
                               (Word("TURBO V2", "w", 110, f0 / FPS + 0.15), 1320, 640)]: w_.draw(c, t, x_, y_)
            paste_scaled(c, cta, 1080 + cta.width / 2, 780, 1, ease((li / FPS - 0.3) / 0.3))
        if prm.get("chip"):
            ch = chip_img(prm["chip"]); a = ease(li / FPS / 0.4)
            paste_scaled(c, ch, 60 + ch.width / 2, 70, 1, a)
        for w_, x_, y_ in words: w_.draw(c, t, x_, y_)
        if not nocap:
            for a, b, im in caps:
                if a <= t < b:
                    p = ease((t - a) / 0.35); q = ease((t - (b - 0.2)) / 0.2) if t > b - 0.2 else 0
                    paste_scaled(c, im, W / 2, 985 + int(10 * (1 - p)), 1, p * (1 - q))
        if li < 4 and kind not in ("trip",): c = c.filter(ImageFilter.GaussianBlur(10 * (1 - li / 4)))
        enc.stdin.write(c.convert("RGB").tobytes())
        if li == (f1 - f0) // 2: c.convert("RGB").save(f"{OUT}/chk_{s['id']}_{k}.jpg", quality=85)
    enc.stdin.close(); enc.wait()
    for r in readers.values(): r.close()
    return path

def seg_hash(s):
    h = hashlib.md5((RENDER_VER + repr(s) + open(f"{PRJ}/work/textfx.py").read()).encode()).hexdigest()[:10]
    return f"{OUT}/seg_{s['id']}_{h}.mp4"

def job(s):
    p = seg_hash(s)
    if not os.path.exists(p): render_seg(s, p + ".tmp.mp4"); os.replace(p + ".tmp.mp4", p)
    return p

def resolve_gaps():
    """Có file noi_X.mp3 thì biến GAP thành segment lời đọc (giữ shot, đổi độ dài theo tiếng)."""
    for s in SEGS:
        if "gap" in s and s.get("alt") and os.path.exists(s["alt"]):
            d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", s["alt"]],
                                     capture_output=True, text=True).stdout)
            s.pop("gap"); s["src"] = s["alt"]; s["keep"] = [(0.0, d)]
            s["shots"] = [(0.0, k, {kk: vv for kk, vv in p.items() if kk != "chip"}) for _, k, p in s["shots"]]

# ---------------- Audio ----------------
def run(cmd):
    cpu_guard()
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode: raise SystemExit(cmd + "\n" + r.stderr[-2000:])
    return r

def voice_track(total):
    parts = []
    for j, s in enumerate(SEGS):
        f = f"{OUT}/v_{j:02d}.wav"; D = round(seg_len(s) * FPS) / FPS
        if "gap" in s:
            run(f"ffmpeg -y -v error -f lavfi -i anullsrc=r=48000:cl=stereo -t {D:.4f} {f}")
        else:
            tr = ";".join(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={b - a - 0.015:.3f}:d=0.015[a{i}]"
                          for i, (a, b) in enumerate(s["keep"]))
            cat = "".join(f"[a{i}]" for i in range(len(s["keep"])))
            tmp = f"{OUT}/v_{j:02d}_raw.wav"
            run(f"ffmpeg -y -v error -i \"{s['src']}\" -filter_complex \"{tr};{cat}concat=n={len(s['keep'])}:v=0:a=1,"
                f"aresample=48000,aformat=channel_layouts=stereo,highpass=f=80[o]\" -map \"[o]\" {tmp}")
            r = run(f"ffmpeg -hide_banner -i {tmp} -af loudnorm=print_format=json -f null - ")
            js = r.stderr[r.stderr.rfind("{"):]; li = float(json.loads(js[:js.index("}") + 1])["input_i"])
            run(f"ffmpeg -y -v error -i {tmp} -af \"volume={-17 - li:.2f}dB,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120,"
                f"apad=pad_dur=2,atrim=0:{D:.4f}\" -ar 48000 -ac 2 {f}")
        parts.append(f)
    lst = f"{OUT}/v_list.txt"; open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    run(f"ffmpeg -y -v error -f concat -safe 0 -i {lst} -c pcm_s16le {OUT}/voice.wav")

def music_sfx(total, starts):
    from scipy.io import wavfile
    from scipy.signal import butter, sosfilt
    SR = 48000; NS = int(total * SR); rng = np.random.default_rng(7); t = np.arange(NS) / SR
    # nhạc nền: Mixkit "Deep Urban" (Eugenio Mininni, Mixkit Stock Music Free License) — assets/music/_downloaded/SOURCES.md
    # bài 95 s → nối vòng đúng nhịp: 0→82.446 rồi quay về 9.300 (tương quan 0.90), crossfade 60 ms
    MF = f"{ROOT}/assets/music/_downloaded/mixkit_deep_urban_1167.mp3"
    trk = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", MF, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                       capture_output=True).stdout, np.float32).astype(np.float64)
    A, B, xf = int(9.300 * SR), int(82.446 * SR), int(0.06 * SR)
    mus = trk[:B].copy()
    while len(mus) < NS:
        nxt = trk[A:B]; r = np.linspace(0, 1, xf)
        mus[-xf:] = mus[-xf:] * (1 - r) + nxt[:xf] * r; mus = np.concatenate([mus, nxt[xf:]])
    mus = mus[:NS] / (np.abs(trk).max() + 1e-9)
    mus *= np.clip(t / .5, 0, 1) * np.clip((total - t) / 2.0, 0, 1) * 0.30
    sfx = np.zeros(NS)
    def place(rel, at, g, align="peak", maxlen=None):
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", f"{ROOT}/assets/sfx/{rel}", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True)
        x = np.frombuffer(r.stdout, np.float32).astype(np.float64); x /= np.abs(x).max() + 1e-9
        pk = int(np.convolve(np.abs(x), np.ones(480) / 480, "same").argmax())
        if maxlen: n = int(maxlen * SR); x = x[:n] * np.r_[np.ones(max(n - 2400, 0)), np.linspace(1, 0, min(2400, n))][:len(x[:n])]
        i = int(at * SR) - (pk if align == "peak" else 0)
        if i < 0: x = x[-i:]; i = 0
        seg = x[:max(0, NS - i)]; sfx[i:i + len(seg)] += seg * g
    big = {"03_boden", "11_cos", "12_pha", "14_bamau", "15_3000", "16_5500", "20_end"}
    for s, st in zip(SEGS, starts):
        if s["id"] in big: place("whoosh/Transitions SFX_13.wav", st, 0.22)
    sid = {s["id"]: st for s, st in zip(SEGS, starts)}
    for sg, tk in [("03_boden", 4.70), ("03_boden", 5.88), ("19_gia", 1.94), ("19_gia", 3.04)]:
        s = next(x for x in SEGS if x["id"] == sg); place("tick_click/Click_16.wav", sid[sg] + s2o(s, tk) + 0.1, 0.22, "start")
    place("impact/Subdrop_06.wav", sid["20_end"], 0.38, "start", 1.0)
    sfx *= 0.5
    for name, sig in [("sfx", sfx), ("music", mus)]:
        wavfile.write(f"{OUT}/{name}.wav", SR, np.repeat((np.clip(sig, -1, 1) * 32767).astype(np.int16)[:, None], 2, 1))

if __name__ == "__main__":
    resolve_gaps()
    only = sys.argv[1:]                                   # tuỳ chọn: chỉ render các id này (xem nháp)
    todo = [s for s in SEGS if not only or s["id"] in only]
    paths = [job(s) for s in todo]                        # tuần tự: 1 render + 1 ffmpeg (CLAUDE.md)
    if only: print("\n".join(paths)); sys.exit()
    lst = f"{OUT}/list.txt"; open(lst, "w").write("".join(f"file '{p}'\n" for p in paths))
    run(f"ffmpeg -y -v error -f concat -safe 0 -i {lst} -c copy {OUT}/video.mp4")
    starts = list(np.cumsum([0] + [round(seg_len(s) * FPS) / FPS for s in SEGS])[:-1])
    total = sum(round(seg_len(s) * FPS) for s in SEGS) / FPS
    voice_track(total); music_sfx(total, starts)
    run(f"ffmpeg -y -v error -i {OUT}/voice.wav -i {OUT}/sfx.wav -i {OUT}/music.wav -filter_complex "
        f"\"[0:a]asplit=2[vo][vk];[2:a][vk]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[md];"
        f"[vo][1:a][md]amix=inputs=3:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=9[m]\" -map \"[m]\" -ar 48000 {OUT}/mix.wav")
    run(f"ffmpeg -y -v error -i {OUT}/video.mp4 -i {OUT}/mix.wav -map 0:v -map 1:a -c:v libx264 -crf 18 -preset medium -threads 4 -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart {FINAL}")
    print("OK", FINAL, f"{total:.2f}s")
