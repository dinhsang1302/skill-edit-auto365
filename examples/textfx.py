"""Chữ động + khung kính dùng chung, tách từ reference/build_f10_10s_textfx.py (anh Việt chốt 10/10/2026)."""
import os, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.environ.get("E365_ROOT", os.path.expanduser("~/Movies/Edit365"))   # thư mục xưởng
F = lambda p, s: ImageFont.truetype(p, s)
ANTON = f"{ROOT}/assets/fonts/Anton-Regular.ttf"
PLAY = f"{ROOT}/assets/fonts/PlayfairDisplay-Italic.ttf"
INTERB = os.path.expanduser("~/Library/Fonts/Inter-Bold.otf")
RED, WHITE, BLACK = (226, 32, 40), (246, 246, 244), (10, 10, 12)
STY = {"it": (PLAY, WHITE), "w": (ANTON, WHITE), "r": (ANTON, RED)}
ease = lambda x: 1 - (1 - min(max(x, 0), 1)) ** 3

class Word:
    """Anton trồi lên qua mask từ đáy chữ; chữ nghiêng trượt ngang ~70px + fade. Ra đi ngược hướng vào."""
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
        self.mask = sty != "it"; self.gh = b - t; self.clip = pad + (b - t) + 10
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

def line(words, y, x=None, align="center", gap=0.55, W=1920):
    widths = [w.adv for w in words]; sp = [w.space * gap * 2 for w in words]
    total = sum(widths) + sum(sp[:-1])
    x0 = {"center": (x or W / 2) - total / 2, "left": x, "right": (x or W) - total}[align]
    out = []
    for w, ww, s in zip(words, widths, sp):
        out.append((w, int(x0), y)); x0 += ww + s
    return out

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

def dark_bg(W, H):
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.45) / H) ** 2)
    v = np.clip(1 - d * 1.5, 0, 1) ** 1.6
    rgb = np.stack([10 + 34 * v, 10 + 32 * v, 12 + 36 * v], -1)
    return Image.fromarray(rgb.astype(np.uint8)).convert("RGBA")

def vignette(W, H, strength=0.55):
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    return (1 - strength * np.clip(d - 0.55, 0, 1) ** 1.5)[..., None]

def zoom_crop(big, z, cx, cy, W, H):
    bw, bh = big.size; base = min(bw / W, bh / H)
    cw, ch = W * base / z, H * base / z
    x = (bw - cw) * cx; y = (bh - ch) * cy
    return big.resize((W, H), Image.BICUBIC, box=(x, y, x + cw, y + ch))

def paste_scaled(canvas, im, cx, cy, s, a=1.0):
    if s != 1: im = im.resize((int(im.width * s), int(im.height * s)), Image.BICUBIC)
    if a < 1: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def cta(txt, size=40):
    f = F(INTERB, size); w = int(f.getlength(txt)) + 80
    im = Image.new("RGBA", (w, 84)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, 83), 42, fill=RED + (255,)); d.text((w / 2, 42), txt, font=f, fill=WHITE, anchor="mm")
    return im
