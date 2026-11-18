#!/usr/bin/env python3
"""Bản thử 10s X-Light F10 Turbo V2 (16:9 1920x1080, 24fps) theo clip mẫu tham khảo (Skill Edit Auto365):
chữ động từng từ (Anton trắng/đỏ + Playfair nghiêng), thẻ ảnh bay có độ sâu, khung kính, nền tối.
Nguồn: input/F10_Turbo_V2_goc.mp4 (0–9.9s, sạch lỗi AI) + insert/*.png. Không dùng thông số."""
import os, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

ROOT = os.environ.get("E365_ROOT", os.path.expanduser("~/Movies/Edit365"))   # thư mục xưởng
SRC = f"{ROOT}/input/F10_Turbo_V2_goc.mp4"
INS = f"{ROOT}/insert"
OUT = f"{ROOT}/work/f10/build"; os.makedirs(OUT, exist_ok=True)
FINAL = f"{ROOT}/output/F10_Turbo_V2_10s_16x9_v3.mp4"
W, H, FPS = 1920, 1080, 24

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode: raise SystemExit(cmd + "\n" + r.stderr[-2000:])

# ---------- Timeline ----------
AUD = [(0.00, 4.55), (4.76, 9.90)]          # bỏ khoảng lặng 4.55–4.76 (chừa 0.1s mỗi bên)
def s2o(t): return t if t <= 4.55 else t - 0.21
fr = lambda t: round(t * FPS)
CUTS = [0, fr(1.833), fr(4.542), fr(6.833), fr(9.625), fr(10.625)]   # S1..S5
N = CUTS[-1]; TOTAL = N / FPS

# ---------- Fonts / màu ----------
F = lambda p, s: ImageFont.truetype(p, s)
ANTON = f"{ROOT}/assets/fonts/Anton-Regular.ttf"
PLAY = f"{ROOT}/assets/fonts/PlayfairDisplay-Italic.ttf"
INTERB = os.path.expanduser("~/Library/Fonts/Inter-Bold.otf")
RED, WHITE, BLACK = (226, 32, 40), (246, 246, 244), (10, 10, 12)
STY = {"it": (PLAY, WHITE), "w": (ANTON, WHITE), "r": (ANTON, RED)}

ease = lambda x: 1 - (1 - min(max(x, 0), 1)) ** 3

class Word:
    """Sprite một từ/cụm, có bóng mềm. Vị trí theo baseline.
    Hiệu ứng (học từ clip mẫu 1010.mp4): chữ Anton trồi lên qua mask, chữ nghiêng trượt ngang + fade.
    slide=-1 trượt từ trái, +1 từ phải. Ra: đi ngược hướng vào (mask chìm xuống / trượt tiếp + mờ)."""
    IN_MASK, IN_SLIDE, OUT = 0.30, 0.45, 0.20
    def __init__(self, text, sty, size, t_in, t_out=99, slide=-1, pad=40):
        path, col = STY[sty]; f = F(path, size)
        l, t, r, b = f.getbbox(text, anchor="ls")
        w, h = r - l + 2 * pad, b - t + 2 * pad
        txt = Image.new("RGBA", (w, h)); ImageDraw.Draw(txt).text((pad - l, pad - t), text, font=f, fill=col + (255,), anchor="ls")
        sh = Image.new("RGBA", (w, h)); ImageDraw.Draw(sh).text((pad - l, pad - t + 4), text, font=f, fill=(0, 0, 0, 200), anchor="ls")
        sh = sh.filter(ImageFilter.GaussianBlur(9))
        self.img = Image.alpha_composite(sh, txt)
        self.off = (l - pad, t - pad); self.adv = f.getlength(text)
        self.t_in, self.t_out, self.slide = t_in, t_out, slide
        self.mask = sty != "it"; self.gh = b - t; self.clip = pad + (b - t) + 10   # đường mask = đáy chữ
        self.space = f.getlength(" ")
    def draw(self, canvas, t, x, y):
        if t < self.t_in or t > self.t_out + self.OUT: return
        im = self.img; X = x + self.off[0]; Y = y + self.off[1]
        if self.mask:
            p = ease((t - self.t_in) / self.IN_MASK)
            q = ((t - self.t_out) / self.OUT) ** 2 if t > self.t_out else 0
            dy = int(self.gh * 1.05 * ((1 - p) + q))
            if dy:
                vis = self.clip - dy
                if vis <= 0: return
                im = im.crop((0, 0, im.width, vis)); Y += dy
            a = min(1, (t - self.t_in) / 0.1)
        else:
            p = ease((t - self.t_in) / self.IN_SLIDE)
            q = ease((t - self.t_out) / self.OUT) if t > self.t_out else 0
            X += int(self.slide * (70 * (1 - p) - 50 * q))
            a = min(1, (t - self.t_in) / 0.25) * (1 - q)
            if p < 0.6: im = im.filter(ImageFilter.GaussianBlur(3 * (1 - p / 0.6)))
        if a < 1:
            im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
        canvas.alpha_composite(im, (max(X, 0), max(Y, 0)))

def line(words, y, x=None, align="center", gap=0.55):
    """Đặt các từ cùng baseline. Trả list (word, x, y)."""
    widths = [w.adv for w in words]; sp = [w.space * gap * 2 for w in words]
    total = sum(widths) + sum(sp[:-1])
    x0 = {"center": (x or W / 2) - total / 2, "left": x, "right": (x or W) - total}[align]
    out = []
    for w, ww, s in zip(words, widths, sp):
        out.append((w, int(x0), y)); x0 += ww + s
    return out

# ---------- Tài nguyên ảnh ----------
def load(name): return Image.open(f"{INS}/{name}").convert("RGB")
def rounded(im, r, border=2, balpha=110):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, fill=255)
    o = im.convert("RGBA"); o.putalpha(m)
    if border: ImageDraw.Draw(o).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, outline=(255, 255, 255, balpha), width=border)
    return o
def with_shadow(card, blur=28, alpha=170, pad=60):
    c = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad))
    sh = Image.new("RGBA", c.size); m = Image.new("L", c.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((pad, pad + 14, pad + card.width, pad + card.height + 14), 36, fill=alpha)
    sh.putalpha(m.filter(ImageFilter.GaussianBlur(blur)))
    c.alpha_composite(sh); c.alpha_composite(card, (pad, pad)); return c

def dark_bg():
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.45) / H) ** 2)
    v = np.clip(1 - d * 1.5, 0, 1) ** 1.6
    rgb = np.stack([10 + 34 * v, 10 + 32 * v, 12 + 36 * v], -1)
    return Image.fromarray(rgb.astype(np.uint8)).convert("RGBA")
BG = dark_bg()

def vignette(strength=0.55):
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    return (1 - strength * np.clip(d - 0.55, 0, 1) ** 1.5)[..., None]
VIG = vignette()

# S1: beam (ảnh 08), push-in
beam = load("08_beam_B_trang.png").crop((0, 540, 2000, 1665)).resize((2304, 1296), Image.LANCZOS)
S1 = line([Word("một bộ", "it", 76, 0.00), Word("BI GẦM", "w", 150, 0.46)], 330) + \
     line([Word("cos đã", "it", 76, 1.12), Word("MẠNH", "r", 200, 1.56)], 540)

# S2: thẻ ảnh beam bay, 3 lớp độ sâu
rng = np.random.default_rng(3)
CARDS = []
spec = [("03_beam_A_vang.png", 280, 230, 0.62, -9, 2), ("06_beam_B_vang.png", 1650, 220, 0.58, 11, 2),
        ("05_beam_A_trang.png", 290, 830, 0.85, 7, 1), ("07_beam_B_am.png", 1640, 840, 0.88, -8, 1),
        ("04_beam_A_am.png", 960, 110, 0.42, 4, 3), ("08_beam_B_trang.png", 960, 990, 0.45, -5, 3)]
for name, cx, cy, sc, rot, depth in spec:
    im = load(name).crop((200, 520, 1800, 1720)).resize((int(820 * sc), int(615 * sc)), Image.LANCZOS)
    im = Image.eval(im, lambda v, k={1: 1.0, 2: 0.8, 3: 0.6}[depth]: int(v * k))
    c = with_shadow(rounded(im, int(26 * sc)), blur=20, pad=40).rotate(rot, Image.BICUBIC, expand=True)
    if depth > 1: c = c.filter(ImageFilter.GaussianBlur({2: 2.5, 3: 6}[depth]))
    drift = np.array([rng.uniform(-1, 1), rng.uniform(-1, 1)]) * {1: 60, 2: 38, 3: 22}[depth]
    CARDS.append((c, cx, cy, drift, depth))
CARDS.sort(key=lambda k: -k[4])
S2 = line([Word("và còn", "it", 76, 1.84)], 395) + \
     line([Word("ẤN TƯỢNG", "r", 210, 2.40)], 620) + \
     line([Word("HƠN NỮA", "w", 100, 2.78), Word("thì sẽ như thế nào?", "it", 70, 3.22)], 760)

# S3: reveal sản phẩm trong khung kính
prod = rounded(load("01_san_pham_cap.png").crop((0, 250, 2000, 1750)).resize((900, 675), Image.LANCZOS), 36, 3, 140)
PROD = with_shadow(prod)
S3 = [(Word("Đây là", "it", 64, s2o(4.84)), 150, 360), (Word("X-LIGHT", "w", 84, s2o(5.48)), 150, 470),
      (Word("F10", "r", 270, s2o(5.80)), 140, 760), (Word("TURBO V2", "w", 128, s2o(6.22)), 150, 900)]

# S4: người dẫn, chữ góc phải dưới (trên áo đen, không đè sản phẩm/hộp)
g1o = s2o(8.34) - 0.22
S4 = line([Word("phiên bản", "it", 70, s2o(7.18), g1o, slide=1)], 850, 1830, "right") + \
     line([Word("NÂNG CẤP", "r", 170, s2o(7.76), g1o)], 1010, 1830, "right") + \
     line([Word("của dòng bi gầm", "it", 64, s2o(8.34), slide=1)], 850, 1830, "right") + \
     line([Word("F10 TURBO", "w", 150, s2o(9.06))], 1010, 1830, "right")
cam_n = CUTS[4] - CUTS[3]
raw = subprocess.run(f"ffmpeg -loglevel error -ss {CUTS[3] / FPS + 0.21:.4f} -i {SRC} -frames:v {cam_n} "
                     f"-vf scale=2112:1214:flags=lanczos -f rawvideo -pix_fmt rgb24 -", shell=True, capture_output=True).stdout
CAM = np.frombuffer(raw, np.uint8).reshape(-1, 1214, 2112, 3)

# S5: end card
box = rounded(load("02_hop_san_pham.png").crop((180, 80, 2000, 1720)).resize((660, 595), Image.LANCZOS), 32, 3, 140)
BOX = with_shadow(box)
T5 = CUTS[4] / FPS
S5 = [(Word("X-LIGHT", "w", 80, T5 + 0.04), 1060, 420), (Word("F10", "r", 190, T5 + 0.08), 1056, 640),
      (Word("TURBO V2", "w", 110, T5 + 0.12), 1300, 640)]
def cta():
    f = F(INTERB, 40); txt = "TƯ VẤN TẠI AUTO365"; w = int(f.getlength(txt)) + 80
    im = Image.new("RGBA", (w, 84)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, 83), 42, fill=RED + (255,)); d.text((w / 2, 42), txt, font=f, fill=WHITE, anchor="mm")
    return im
CTA = cta()

# ---------- Render ----------
def zoom_crop(big, z, cx, cy):
    bw, bh = big.size; base = min(bw / W, bh / H)
    cw, ch = W * base / z, H * base / z
    x = (bw - cw) * cx; y = (bh - ch) * cy
    return big.resize((W, H), Image.BICUBIC, box=(x, y, x + cw, y + ch))

def paste_scaled(canvas, im, cx, cy, s, a=1.0):
    if s != 1: im = im.resize((int(im.width * s), int(im.height * s)), Image.BICUBIC)
    if a < 1: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def frame(i):
    t = i / FPS
    sc = max(k for k in range(5) if CUTS[k] <= i); ls = (i - CUTS[sc]) / (CUTS[sc + 1] - CUTS[sc]); lt = t - CUTS[sc] / FPS
    if sc == 0:
        c = zoom_crop(beam, 1.0 + 0.07 * ls, 0.5, 0.55).convert("RGBA"); words = S1
    elif sc == 1:
        c = BG.copy()
        for im, cx, cy, dr, dp in CARDS:
            paste_scaled(c, im, cx + dr[0] * ls, cy + dr[1] * ls, 1 + 0.04 * ls / dp)
        sh = Image.new("RGBA", (W, H)); ImageDraw.Draw(sh).ellipse((360, 250, 1560, 850), fill=(0, 0, 0, 150))
        c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(90))); words = S2
    elif sc == 2:
        c = BG.copy(); p = ease(lt / 0.35)
        paste_scaled(c, PROD, 1310, 540, (0.9 + 0.1 * p) * (1 + 0.03 * ls), p); words = S3
    elif sc == 3:
        z = 1.0 + 0.06 * ls; fimg = Image.fromarray(CAM[min(i - CUTS[3], len(CAM) - 1)])
        a = np.asarray(zoom_crop(fimg, z, 0.55, 0.4), np.float32)
        a = np.clip((a - 128) * 1.08 + 128 - 10, 0, 255) * VIG
        gy, gx = np.mgrid[0:H, 0:W]                      # gradient tối góc phải dưới cho chữ
        g = np.clip((gx - 1150) / 770, 0, 1) * np.clip((gy - 560) / 520, 0, 1)
        a = a * (1 - 0.5 * g[..., None])
        c = Image.fromarray(a.astype(np.uint8)).convert("RGBA"); words = S4
    else:
        c = BG.copy(); p = ease(lt / 0.3)
        paste_scaled(c, BOX, 600, 540, 0.92 + 0.08 * p, p)
        paste_scaled(c, CTA, 1060 + CTA.width / 2, 780, 1, ease((lt - 0.2) / 0.2)); words = S5
    for w, x, y in words: w.draw(c, t, x, y)
    # blur-in 4 frame đầu mỗi cảnh (S1: fade từ đen)
    k = i - CUTS[sc]
    if sc and k < 4: c = c.filter(ImageFilter.GaussianBlur(14 * (1 - k / 4)))
    c = c.convert("RGB")
    if sc == 0 and k < 6: c = Image.eval(c, lambda v, a=k / 6: int(v * a))
    if i >= N - 4: c = Image.eval(c, lambda v, a=(N - i) / 5: int(v * a))
    return c

enc = subprocess.Popen(f"ffmpeg -y -loglevel error -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {FPS} -i - "
                       f"-c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p {OUT}/video.mp4", shell=True, stdin=subprocess.PIPE)
for i in range(N):
    enc.stdin.write(frame(i).tobytes())
    if i in (20, 80, 130, 200, 245): frame(i).save(f"{OUT}/check_{i:03d}.jpg", quality=88)
enc.stdin.close(); enc.wait()

# ---------- Âm thanh ----------
parts = [f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={b - a - 0.015:.3f}:d=0.015[a{j}]"
         for j, (a, b) in enumerate(AUD)]
run(f"ffmpeg -y -loglevel error -i {SRC} -filter_complex \"{';'.join(parts)};[a0][a1]concat=n=2:v=0:a=1,"
    f"highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=3dB,apad=whole_dur={TOTAL:.3f},"
    f"atrim=0:{TOTAL:.3f}[v]\" -map \"[v]\" -ar 48000 -ac 2 {OUT}/voice.wav")

SR = 48000; rng = np.random.default_rng(7); NS = int(TOTAL * SR)
SFXD = f"{ROOT}/assets/sfx"
def sfx_load(rel):
    """Đọc SFX thư viện (mono 48k), chuẩn đỉnh = 1. Trả (tín hiệu, mẫu đỉnh envelope)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", f"{SFXD}/{rel}", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True)
    x = np.frombuffer(r.stdout, np.float32).astype(np.float64); x /= np.abs(x).max() + 1e-9
    e = np.convolve(np.abs(x), np.ones(480) / 480, "same"); return x, int(e.argmax())
sfx = np.zeros(NS)
def place(rel, at, g, align="peak", maxlen=None):
    """align='peak': đỉnh SFX rơi đúng mốc `at` (whoosh vào cắt); 'start': bắt đầu tại `at` (hit)."""
    x, pk = sfx_load(rel)
    if maxlen: n = int(maxlen * SR); x = x[:n] * np.r_[np.ones(max(n - 2400, 0)), np.linspace(1, 0, min(2400, n))][:len(x[:n])]
    i = int(at * SR) - (pk if align == "peak" else 0)
    if i < 0: x = x[-i:]; i = 0
    seg = x[:max(0, NS - i)]; sfx[i:i + len(seg)] += seg * g
c = [k / FPS for k in CUTS]
place("whoosh/Swoosh_20.wav", c[1], 0.30)                          # vào thẻ bay
place("whoosh/Transitions SFX_01.wav", c[2], 0.40)                 # reveal sản phẩm
place("impact/Short Bass Hit .wav", c[2], 0.38, "start", 1.4)
place("whoosh/Transitions SFX_13.wav", c[3], 0.25)                 # về người dẫn
place("whoosh/Transitions SFX_37.wav", c[4], 0.38)                 # end card
place("impact/Subdrop_06.wav", c[4], 0.42, "start", 1.0)
for tk in (1.56, 2.40, s2o(7.76)):                                 # chữ keyword trồi lên (tiết chế)
    place("text_slide/Swoosh_27.wav", tk + 0.12, 0.12)
place("tick_click/Click_16.wav", c[4] + 0.30, 0.25, "start")       # nút CTA
# nhạc nền tạm: pad tối + nhịp sub 100 BPM (tự tổng hợp — thay bằng nhạc trong assets/music khi có)
t = np.arange(NS) / SR; mus = np.zeros(NS)
for f, g in [(73.42, .5), (110, .35), (146.83, .3), (174.61, .2), (220, .15)]:
    mus += g * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * (1 + .15 * np.sin(2 * np.pi * .2 * t + f))
mus = sosfilt(butter(2, 1200, "low", fs=SR, output="sos"), mus); mus /= np.abs(mus).max()
beat = 60 / 100
for k in np.arange(0, TOTAL, beat):
    n = int(.35 * SR); tt = np.arange(n) / SR; i0 = int(k * SR)
    kick = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-tt * 18) + 45) / SR) * np.exp(-tt * 9)
    mus[i0:i0 + n] += kick[:max(0, NS - i0)] * .6
mus *= np.clip(t / .4, 0, 1) * np.clip((TOTAL - t) / .5, 0, 1) * .22
sfx *= 0.5                                                        # bus SFX -6 dB, dưới giọng
for name, sig in [("sfx", sfx), ("music", mus)]:
    wavfile.write(f"{OUT}/{name}.wav", SR, np.repeat((np.clip(sig, -1, 1) * 32767).astype(np.int16)[:, None], 2, 1))
run(f"ffmpeg -y -loglevel error -i {OUT}/voice.wav -i {OUT}/sfx.wav -i {OUT}/music.wav -filter_complex "
    f"\"[0:a]asplit=2[vo][vk];[2:a][vk]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[md];"
    f"[vo][1:a][md]amix=inputs=3:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=9[m]\" "
    f"-map \"[m]\" -ar 48000 {OUT}/mix.wav")
run(f"ffmpeg -y -loglevel error -i {OUT}/video.mp4 -i {OUT}/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k "
    f"-shortest -movflags +faststart {FINAL}")
print("OK", FINAL, f"{TOTAL:.3f}s", N, "frames")
