#!/usr/bin/env python3
"""e365 — thư viện dựng clip của Skill Edit Auto365 (bản chuẩn, gom từ các job Auto365 10–11/2026).

Chạy được trên macOS (Apple Silicon) và Windows (GPU NVIDIA). Tự nhận nền tảng (biến HW), ép bằng biến môi trường E365_HW=vt|cuda|none.
  - Mac:     giải mã videotoolbox + scale_vt; nháp h264_videotoolbox.
  - Windows: giải mã NVDEC (-hwaccel cuda) + scale_cuda; nháp h264_nvenc. scale_cuda lỗi → tự lùi về cuda + scale CPU → CPU.

Làm gì:
  - VReader: giải mã bằng phần cứng + scale ngay trên GPU về đúng cỡ cần, grade trên frame nhỏ.
  - Encoder: nhận frame RGB từ python, nháp encode GPU / bản giao libx264 ít luồng (giữ trần 70% CPU máy).
  - Word / layout_line: chữ động (đậm trồi lên qua mask, nghiêng trượt ngang + fade), có kẹp vùng an toàn chống tràn khung.
  - cap_img: phụ đề PNG (Pillow, KHÔNG dùng libass), tự bẻ 2 dòng, tự thu cỡ khi quá rộng.
  - boxes_overlap / check_layout: soát chữ đè chữ, phụ đề đè chữ động, CTA sát phụ đề trước khi render.
  - rounded / with_shadow / cta / soft_bg: khung kính bo góc, bóng đổ, nút CTA, nền mờ.
  - cut_voice / loudness / final_mix / mux: âm thanh theo quy trình (fade 12/15 ms mỗi mối cắt, nén nhẹ, duck nhạc, -14 LUFS / TP -1.5).
  - start_cpu_watch: bật scripts/cpu_watch.py canh trần CPU suốt job.
  - find_font: tìm font trong assets/fonts → font người dùng → font hệ thống (Mac lẫn Windows).

Cách dùng (trong work/build.py của dự án):
    import sys; sys.path.insert(0, "<thư mục làm việc>/scripts"); import e365 as E
    rd = E.VReader(src, ss=1.8, w=1080, h=1920, fps=30, grade=E.GRADE_WARM)
    img = rd.next()                      # PIL RGB
Mẫu build hoàn chỉnh: scripts/build_template.py. Thử thư viện: <python> scripts/e365.py --selftest
(<python> = .venv/bin/python trên Mac, .venv\\Scripts\\python trên Windows)
"""
import os, sys, json, shutil, subprocess, hashlib, numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]               # thư mục làm việc
IS_WIN, IS_MAC = sys.platform.startswith("win"), sys.platform == "darwin"
FONT_DIRS = [ROOT / "assets/fonts", Path.home() / "Library/Fonts", Path("/Library/Fonts"),
             Path(os.environ.get("LOCALAPPDATA", "~")) / "Microsoft/Windows/Fonts", Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"]

def find_font(name):
    """Tìm file font theo tên (vd. "InterDisplay-ExtraBold.otf"). Không thấy → báo rõ cần cài/chép font nào."""
    for d in FONT_DIRS:
        if (d / name).exists(): return str(d / name)
    raise FileNotFoundError(f"Thiếu font {name}: chép vào assets/fonts/ (xem check_env)")

class _F:                                                  # tìm font lúc dùng, không lỗi khi import
    def __init__(self, n): self.n = n
    def __fspath__(self): return find_font(self.n)
    def __str__(self): return find_font(self.n)
F_CAPTION = _F("InterDisplay-ExtraBold.otf")               # phụ đề chuẩn: Inter Display ExtraBold 66
F_BVP_BLACK = _F("BeVietnamPro-Black.ttf")
F_BVP_BOLD = _F("BeVietnamPro-Bold.ttf")
F_INTER_BOLD = _F("Inter-Bold.otf")
F_ANTON = _F("Anton-Regular.ttf")
F_PLAYFAIR_IT = _F("PlayfairDisplay-Italic.ttf")

def _detect_hw():
    if os.environ.get("E365_HW"): return os.environ["E365_HW"]
    if IS_MAC: return "vt"
    acc = subprocess.run(["ffmpeg", "-hide_banner", "-hwaccels"], capture_output=True, text=True).stdout
    return "cuda" if "cuda" in acc and shutil.which("nvidia-smi") else "none"
HW = _detect_hw()
X264_THREADS = os.environ.get("E365_X264_THREADS", "2" if IS_MAC else "4")   # Mac 10 nhân: 2 (đo 446%); i7-14700K 28 luồng: 4

WHITE, AMBER, RED, GOLD = (250, 250, 248), (255, 200, 61), (226, 32, 40), (255, 199, 44)   # AMBER = &H3DC8FF& (BGR) → #FFC83D
INK_DARK, INK_BROWN = (12, 12, 14), (48, 30, 16)
GRADE_NEUTRAL = "eq=brightness=0.0:contrast=1.03:saturation=1.04"
GRADE_WARM = "eq=brightness=0.035:contrast=1.05:saturation=1.10,colorbalance=rs=0.03:bs=-0.04:rm=0.025:bm=-0.03"
TH = "4"                                                  # ffmpeg phụ (mix, concat, đo) — luật máy

ease = lambda x: 1 - (1 - min(max(x, 0), 1)) ** 3
smooth = lambda u: (lambda v: v * v * (3 - 2 * v))(min(max(u, 0), 1))


# ---------------- Tiện ích ----------------
def run(cmd):
    """Chạy lệnh (list tham số — chạy giống nhau trên Mac/Windows, không lo dấu cách/ngoặc trong đường dẫn).
    ffmpeg phụ tự thêm `-threads 4`. Lỗi → dừng kèm 2000 ký tự stderr cuối. Chuỗi → chạy qua shell (chỉ khi thật cần)."""
    if isinstance(cmd, str):
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    else:
        cmd = [str(c) for c in cmd]
        if cmd[0] == "ffmpeg" and "-threads" not in cmd[:3]: cmd = ["ffmpeg", "-threads", TH] + cmd[1:]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode: raise SystemExit(str(cmd) + "\n" + r.stderr[-2000:])
    return r

def concat(paths, out, audio_wav=False):
    """Nối file cùng định dạng không encode lại (video: -c copy; wav: pcm_s16le). Đường dẫn ghi dạng posix cho cả Windows."""
    lst = Path(str(out) + ".txt")
    lst.write_text("".join("file '" + Path(p).resolve().as_posix().replace("'", "'\\''") + "'\n" for p in paths), encoding="utf-8")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst] + (["-c", "pcm_s16le"] if audio_wav else ["-c", "copy"]) + [out])

def probe(path):
    """→ dict(w, h, fps, dur, bits, rot). w/h đã xoay theo metadata (clip điện thoại quay dọc)."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate,pix_fmt:stream_side_data=rotation:format=duration:format_tags=major_brand", "-of", "json", path],
                       capture_output=True, text=True, encoding="utf-8")
    j = json.loads(r.stdout); st = j["streams"][0]; n, d = st["r_frame_rate"].split("/")
    rsg = next((int(sd.get("rotation", 0)) for sd in st.get("side_data_list", []) if "rotation" in sd), 0); rot = abs(rsg)
    w, h = (st["height"], st["width"]) if rot == 90 else (st["width"], st["height"])
    pf = st.get("pix_fmt", "")
    return dict(w=w, h=h, fps=float(n) / float(d), dur=float(j["format"]["duration"]), rot=rot, rot_signed=rsg,
                bits=10 if "10" in pf else 8, chroma="422" if "422" in pf else ("444" if "444" in pf else "420"),
                brand=j["format"].get("tags", {}).get("major_brand", ""))

CPU_PCT = float(os.environ.get("E365_CPU", "80"))          # trần CPU = % TỔNG máy (anh chốt 20/11/2026: 80%), máy nào cũng tự cân theo %

def auto_par(per_job=4.0, cap=8):
    """Số việc chạy song song tự tính theo máy: (số luồng × CPU_PCT%) / số luồng mỗi việc ăn, kẹp 1..cap.
    i7-14700K 28 luồng → 28×0,8/4 ≈ 6 · Mac M 10 nhân → 2. Ghi đè bằng biến PAR."""
    if os.environ.get("PAR"): return max(1, int(os.environ["PAR"]))
    return max(1, min(cap, round((os.cpu_count() or 4) * CPU_PCT / 100 / per_job)))

def start_cpu_watch(log, pct=None):
    """Bật canh CPU cho tiến trình hiện tại (đo mỗi 60 s, vượt trần → tạm dừng ffmpeg 15 s). Tự dừng khi job xong."""
    pct = pct or CPU_PCT
    kw = dict(creationflags=0x00000200 | 0x08000000) if IS_WIN else dict(start_new_session=True)   # nhóm riêng, không cửa sổ
    subprocess.Popen([sys.executable, str(ROOT / "scripts/cpu_watch.py"), str(os.getpid()), str(log), str(pct)],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)


# ---------------- Hình ----------------
S = 1.0                                                    # hệ số vẽ: toạ độ thiết kế (1920x1080 / 1080x1920) × S = cỡ render
                                                           # nháp 360p: S = 1/3 · bản giao 4K: S = 2 (build_template đặt E.S)
_HW_MODE = {}                                              # (HW, bits) → chế độ đã thử chạy được

class VReader:
    """Đọc frame tuần tự (chỉ tiến). Giải mã + scale ngay trên GPU về (w,h), rồi mới tải về RAM, fps/grade trên frame đã nhỏ
    → nhanh ~8 lần so với giải mã CPU ở 4K. 1 ffmpeg đọc, -threads 2.
      Mac (HW=vt):     -hwaccel videotoolbox -hwaccel_output_format videotoolbox_vld · scale_vt=w:h,hwdownload,format=nv12|p010le
      Windows (cuda):  -hwaccel cuda -hwaccel_output_format cuda · scale_cuda=w:h,hwdownload,format=nv12|p010le
        nếu bản ffmpeg không có scale_cuda → "cuda_cpu": giải mã NVDEC, scale CPU; vẫn lỗi → "sw": giải mã CPU.
    Nguồn 10-bit (DJI, iPhone HDR) → p010le; 8-bit → nv12 (tự dò bằng probe)."""
    def __init__(self, path, ss, w, h, fps=30, grade=GRADE_NEUTRAL, extra="", hw=True):
        w, h = int(w) // 2 * 2, int(h) // 2 * 2
        self.w, self.h, self.last = w, h, None
        tail = f"fps={fps}" + (f",{grade}" if grade else "") + (f",{extra}" if extra else "") + ",format=rgb24"
        info = probe(path); bits = info["bits"]; fmt = "p010le" if bits == 10 else "nv12"
        if info["chroma"] != "420" or info["brand"] == "XAVC": hw = False   # Sony XAVC: 4:2:2 không giải GPU được, 4:2:0 rơi ~3,5% frame (17/10/2026)
        r = info["rot_signed"] % 360                       # đường GPU không tự xoay theo metadata → scale theo khung gốc rồi transpose
        sw_, sh_ = (h, w) if r in (90, 270) else (w, h)
        rotf = {90: ",transpose=2", 270: ",transpose=1", 180: ",hflip,vflip"}.get(r, "")
        modes = {"vt": ["vt", "sw"], "cuda": ["cuda", "cuda_cpu", "sw"]}.get(HW, ["sw"]) if hw else ["sw"]
        key = (HW, bits)
        if hw and key in _HW_MODE: modes = [_HW_MODE[key]]   # chỉ dùng chế độ đã thử khi được phép GPU (XAVC ép CPU)
        for m in modes:
            if m == "vt":
                pre, vf = ["-hwaccel", "videotoolbox", "-hwaccel_output_format", "videotoolbox_vld"], f"scale_vt=w={sw_}:h={sh_},hwdownload,format={fmt}{rotf},{tail}"
            elif m == "cuda":
                pre, vf = ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"], f"scale_cuda=w={sw_}:h={sh_},hwdownload,format={fmt}{rotf},{tail}"
            elif m == "cuda_cpu":
                pre, vf = ["-hwaccel", "cuda"], f"scale={w}:{h}:flags=bicubic,{tail}"
            else:
                pre, vf = [], f"scale={w}:{h}:flags=bicubic,{tail}"
            cmd = ["ffmpeg", "-v", "error", "-threads", "2" if m != "sw" else "1", *pre, "-ss", f"{ss:.3f}", "-i", str(path), "-vf", vf, "-an"]
            if key not in _HW_MODE and len(modes) > 1:                 # thử 1 frame trước khi tin chế độ này
                t = subprocess.run(cmd + ["-frames:v", "1", "-f", "null", "-"], capture_output=True)
                if t.returncode: continue
                _HW_MODE[key] = m
            break
        self.mode = m
        self.p = subprocess.Popen(cmd + ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    def next(self):
        n = self.w * self.h * 3; b = self.p.stdout.read(n)
        if len(b) == n: self.last = Image.frombuffer("RGB", (self.w, self.h), b)
        if self.last is None: raise RuntimeError("VReader: không đọc được frame nào (sai ss/đường dẫn?)")
        return self.last                                   # hết nguồn → giữ frame cuối
    def close(self): self.p.kill(); self.p.wait()

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")

class ImgReader:
    """Ảnh tĩnh (ảnh sản phẩm, ảnh Codex minh hoạ) dùng như 1 shot: cùng giao diện VReader; zoom chậm do frame_from (z0→z1)."""
    def __init__(self, path, w, h):
        im = Image.open(path).convert("RGB"); k = max(w / im.width, h / im.height)
        self.w, self.h = round(im.width * k), round(im.height * k); self.im = im.resize((self.w, self.h), Image.LANCZOS)
    def next(self): return self.im
    def close(self): pass

def reader_for(path, ss, W, H, z=(1, 1), fps=30, **kw):
    """Ảnh tĩnh → ImgReader. Video: mở VReader ở cỡ đủ cho zoom lớn nhất S=max(z): đọc (W*S, H*S) giữ tỉ lệ khung RA. Nguồn khác tỉ lệ → crop ở frame_from."""
    if Path(path).suffix.lower() in IMG_EXT: return ImgReader(path, W * max(z), H * max(z))
    S = max(z); info = probe(path)
    k = max(W * S / info["w"], H * S / info["h"])           # phủ kín khung ra
    return VReader(path, ss, round(info["w"] * k / 2) * 2, round(info["h"] * k / 2) * 2, fps=fps, **kw)

def frame_from(rd, W, H, z, c=(.5, .5)):
    """Cắt khung W×H tại zoom z (1 = vừa khít), tâm c=(cx,cy) theo tỉ lệ. Kẹp trong ảnh, không lộ viền đen."""
    im = rd.next(); base = min(rd.w / W, rd.h / H); cw, ch = W * base / z, H * base / z
    x0 = max(min(c[0] * rd.w - cw / 2, rd.w - cw), 0); y0 = max(min(c[1] * rd.h - ch / 2, rd.h - ch), 0)
    if abs(cw - W) < 1 and abs(ch - H) < 1: return im.crop((round(x0), round(y0), round(x0) + W, round(y0) + H))
    return im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))

class Encoder:
    """ffmpeg encode nhận rawvideo rgb24 qua stdin. Nháp (final=False): encode GPU, gần như 0 CPU —
    Mac h264_videotoolbox 12M · Windows h264_nvenc preset p4 12M · không GPU: libx264 veryfast.
    Bản giao (final=True): libx264 crf18 medium, X264_THREADS luồng, lookahead-threads=1
    (Mac đo 12/10: 4 luồng → đỉnh 648%, 2 luồng → 446% = dưới trần 500%)."""
    def __init__(self, path, W, H, fps, final=False):
        big = min(W, H) >= 2000                            # bản giao 4K: x264 2 luồng quá chậm → HEVC phần cứng 45 Mbit (gần 0 CPU)
        if final and big and HW == "vt":
            codec = ["-c:v", "hevc_videotoolbox", "-b:v", "45M", "-tag:v", "hvc1"]
        elif final and big and HW == "cuda":
            codec = ["-c:v", "hevc_nvenc", "-preset", "p6", "-b:v", "45M", "-tag:v", "hvc1"]
        elif final:
            codec = ["-threads", X264_THREADS, "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-x264-params", "lookahead-threads=1"]
        elif HW == "vt":
            codec = ["-c:v", "h264_videotoolbox", "-b:v", "1500k" if min(W, H) <= 400 else "5M" if min(W, H) <= 800 else "12M"]
        elif HW == "cuda":
            codec = ["-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "1500k" if min(W, H) <= 400 else "5M" if min(W, H) <= 800 else "12M"]
        else:
            codec = ["-threads", "4", "-c:v", "libx264", "-crf", "20", "-preset", "veryfast"]
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                   "-r", str(fps), "-i", "-", *codec, "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    def write(self, img): self.p.stdin.write(img.convert("RGB").tobytes())
    def close(self):
        self.p.stdin.close()
        if self.p.wait(): raise SystemExit("Encoder lỗi")


# ---------------- Chữ động ----------------
# kiểu chữ: (font, màu chữ, màu viền, độ dày viền). "w" trắng đậm, "k" keyword nhấn, "it" từ nối nghiêng serif.
STYLES = {
    "dark":  {"w": (F_ANTON, WHITE, None, 0), "k": (F_ANTON, RED, None, 0), "it": (F_PLAYFAIR_IT, WHITE, None, 0)},   # Auto365 nền tối
    "light": {"w": (F_BVP_BLACK, WHITE, INK_BROWN, 3), "k": (F_BVP_BLACK, GOLD, INK_BROWN, 3), "it": (F_PLAYFAIR_IT, WHITE, INK_BROWN, 2)},
    # "paper": chữ trên cảnh minh hoạ NỀN SÁNG (style brand 3M đỏ–trắng–đen, 19/11/2026): đen đậm, keyword = hộp đỏ chữ trắng, nghiêng đen
    "paper": {"w": (F_ANTON, INK_DARK, None, 0), "k": (F_ANTON, WHITE, None, 0, RED), "it": (F_PLAYFAIR_IT, INK_DARK, None, 0)},
}

class Word:
    """Chữ động 1 từ/cụm. Đậm ("w","k"): trồi lên qua mask từ đáy chữ. Nghiêng ("it"): trượt ngang ~70 px + fade + blur.
    Thời lượng người dùng chốt 11/10: mask 0,55 s · trượt 0,8 s · ra 0,35 s (bản 10 s cũ: 0,30/0,45/0,20).
    Chốt 18/11/2026: chữ pop up lên rồi ĐỨNG YÊN ≥ HOLD_MIN (1,2 s) mới được xuống; vào/ra đều ease mượt + mờ dần,
    không lên/xuống đột ngột. t_out ngắn hơn mức tối thiểu sẽ tự kéo dài (build báo nếu tràn hết đoạn)."""
    IN_MASK, IN_SLIDE, OUT, HOLD_MIN = 0.55, 0.80, 0.35, 1.2
    def __init__(self, text, sty, size, t_in, t_out=99, slide=-1, theme="dark", pad=None):
        pad = round(40 * S) if pad is None else pad
        path, col, ink, sw, *box = STYLES[theme][sty]; f = ImageFont.truetype(str(path), size); sw = round(sw * S)
        l, t, r, b = f.getbbox(text, anchor="ls", stroke_width=sw)
        w, h = r - l + 2 * pad, b - t + 2 * pad
        txt = Image.new("RGBA", (w, h)); dt = ImageDraw.Draw(txt)
        shd = Image.new("RGBA", (w, h)); ds = ImageDraw.Draw(shd)
        if box:                                            # keyword trong hộp màu (theme "paper"): hộp nằm trong pad → không đổi bố cục
            bx, by = min(pad - 4, round(size * 0.13)), min(pad - 4, round(size * 0.07))
            rect = (pad - bx, pad - by, w - pad + bx, h - pad + by)
            dt.rounded_rectangle(rect, round(size * 0.08), fill=box[0] + (255,))
            ds.rounded_rectangle((rect[0], rect[1] + 6 * S, rect[2], rect[3] + 6 * S), round(size * 0.08), fill=(0, 0, 0, 70))
        dt.text((pad - l, pad - t), text, font=f, fill=col + (255,), anchor="ls", stroke_width=sw, stroke_fill=(ink or col) + (255,))
        sa = 60 if theme == "paper" else 190                # chữ tối trên nền sáng: bóng nhẹ, chỉ tách nền
        if not box: ds.text((pad - l, pad - t + 5 * S), text, font=f, fill=(0, 0, 0, sa), anchor="ls",
                            stroke_width=sw + round(2 * S), stroke_fill=(0, 0, 0, sa))
        self.img = Image.alpha_composite(shd.filter(ImageFilter.GaussianBlur(8 * S)), txt)
        self.off = (l - pad, t - pad); self.adv = f.getlength(text); self.space = f.getlength(" ")
        self.top, self.bot = t, b                          # so với baseline (t âm)
        t_out = max(t_out, t_in + (self.IN_MASK if sty != "it" else self.IN_SLIDE) + self.HOLD_MIN)   # đứng đủ lâu mới xuống
        self.t_in, self.t_out, self.slide, self.text = t_in, t_out, slide, text
        self.mask = sty != "it"; self.gh = b - t; self.clip = pad + (b - t) + round(12 * S)
    def draw(self, canvas, t, x, y):
        if t < self.t_in or t > self.t_out + self.OUT: return
        im = self.img; X = x + self.off[0]; Y = y + self.off[1]
        if self.mask:
            p = ease((t - self.t_in) / self.IN_MASK)
            q = ease((t - self.t_out) / self.OUT) if t > self.t_out else 0     # ra mượt (ease), không giật
            dy = int(self.gh * 1.05 * ((1 - p) + q))
            if dy:
                vis = self.clip - dy
                if vis <= 0: return
                im = im.crop((0, 0, im.width, vis)); Y += dy
            a = min(1, (t - self.t_in) / 0.18) * (1 - 0.6 * q)
        else:
            p = ease((t - self.t_in) / self.IN_SLIDE)
            q = ease((t - self.t_out) / self.OUT) if t > self.t_out else 0
            X += int(self.slide * S * (70 * (1 - p) - 50 * q))
            a = min(1, (t - self.t_in) / 0.25) * (1 - q)
            if p < 0.6: im = im.filter(ImageFilter.GaussianBlur(3 * S * (1 - p / 0.6)))
        if a < 1:
            im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
        canvas.alpha_composite(im, (X, Y))                # X,Y đã được layout_line kẹp trong vùng an toàn

def layout_line(words, y, W, H, x=None, align="center", gap=0.55, safe=None):
    """Xếp 1 dòng chữ động; trả [(word, x, y_baseline)]. Chống TRÀN KHUNG (lỗi đã gặp 11/10: "LOẠI NÀO CŨNG ĐƯỢC",
    "ĐANG CÓ VOUCHER" lòi mép): dòng rộng hơn W-2*safe → báo lỗi để giảm cỡ/bẻ dòng; lệch mép → dời vào trong."""
    safe = round(60 * S) if safe is None else safe
    sp = [w.space * gap * 2 for w in words]; total = sum(w.adv for w in words) + sum(sp[:-1])
    if total > W - 2 * safe:
        raise ValueError(f"Dòng chữ động quá rộng ({total:.0f}px > {W - 2 * safe}px): "
                         f"{' '.join(w.text for w in words)!r} → giảm cỡ hoặc tách 2 dòng")
    x0 = {"center": (x if x is not None else W / 2) - total / 2, "left": x, "right": (x if x is not None else W) - total}[align]
    x0 = min(max(x0, safe), W - safe - total)
    top = min(w.top for w in words); bot = max(w.bot for w in words)
    y = int(min(max(y, safe - top), H - safe - bot))
    out = []
    for w, s in zip(words, sp): out.append((w, int(x0), y)); x0 += w.adv + s
    return out

def line_box(placed, slide=None):
    """Hộp bao (x0,y0,x1,y1) của 1 dòng đã xếp, nới theo quãng trượt của chữ nghiêng."""
    slide = 70 * S if slide is None else slide
    xs0 = [x - (slide if not w.mask else 0) for w, x, _ in placed]; xs1 = [x + w.adv + (slide if not w.mask else 0) for w, x, _ in placed]
    return (min(xs0), min(y + w.top for w, _, y in placed), max(xs1), max(y + w.bot for w, _, y in placed))


# ---------------- Phụ đề ----------------
def cap_img(txt, size=66, font=F_CAPTION, maxw=None, W=1920, color=WHITE, ink=INK_DARK, keyword=None, kcolor=AMBER):
    """Phụ đề PNG nền trong: trắng viền tối + bóng mềm. Quá rộng → bẻ 2 dòng gần đều; vẫn quá → thu cỡ (chống tràn).
    keyword: tô 1 từ/cụm màu hổ phách (≤1 keyword mỗi dòng)."""
    maxw = maxw or int(W * 0.84)
    while True:
        f = ImageFont.truetype(str(font), size); lines = [txt]
        if f.getlength(txt) > maxw and len(txt.split()) > 1:
            ws = txt.split(); k = min(range(1, len(ws)), key=lambda i: abs(f.getlength(" ".join(ws[:i])) - f.getlength(" ".join(ws[i:]))))
            lines = [" ".join(ws[:k]), " ".join(ws[k:])]
        if max(f.getlength(l) for l in lines) <= maxw or size <= 30 * S: break
        size -= max(1, round(4 * S))
    lh = int(size * 1.32); sw = max(max(1, round(3 * S)), size // 18); P = round(20 * S)
    wd = int(max(f.getlength(l) for l in lines)) + 3 * P; hh = lh * len(lines) + 2 * P
    shd = Image.new("RGBA", (wd, hh)); im = Image.new("RGBA", (wd, hh))
    for i, l in enumerate(lines):
        cy = P + lh * i + lh // 2
        ImageDraw.Draw(shd).text((wd / 2, cy + 4 * S), l, font=f, anchor="mm", fill=(0, 0, 0, 200), stroke_width=sw + round(3 * S), stroke_fill=(0, 0, 0, 200))
        x = wd / 2 - f.getlength(l) / 2
        parts = l.split(keyword, 1) if keyword and keyword in l else [l]
        for j, part in enumerate(parts):
            for seg, col in ([(part, color)] if j == 0 else [(keyword, kcolor), (part, color)]):
                if not seg: continue
                ImageDraw.Draw(im).text((x, cy), seg, font=f, anchor="lm", fill=col, stroke_width=sw, stroke_fill=ink)
                x += f.getlength(seg)
    return Image.alpha_composite(shd.filter(ImageFilter.GaussianBlur(6 * S)), im)

def pop_scale(t, d=0.14):
    """Pop nhẹ 140 ms cho phụ đề: 0.92 → 1.03 → 1.0."""
    if t >= d: return 1.0
    u = t / d; return 0.92 + 0.11 * ease(u / 0.7) - 0.03 * max(0, (u - 0.7) / 0.3)


# ---------------- Soát bố cục (chạy TRƯỚC khi render) ----------------
def boxes_overlap(a, b, gap=0):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])

def check_layout(items, W, H, safe=None, gap=None):
    """items: [(tên, (x0,y0,x1,y1), t0, t1)]. Báo: lòi khỏi vùng an toàn; hai thứ hiện cùng lúc mà đè nhau hoặc
    cách nhau < gap px (lỗi đã gặp: phụ đề đè chữ động, nút CTA sát phụ đề). Trả list lỗi (rỗng = sạch)."""
    safe = round(40 * S) if safe is None else safe; gap = round(24 * S) if gap is None else gap
    errs = []
    for n, bx, a, b in items:
        if bx[0] < safe or bx[1] < safe or bx[2] > W - safe or bx[3] > H - safe: errs.append(f"{n}: lòi vùng an toàn {bx}")
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (n1, b1, a1, e1), (n2, b2, a2, e2) = items[i], items[j]
            if a1 < e2 and a2 < e1 and boxes_overlap(b1, b2, gap): errs.append(f"{n1} ↔ {n2}: đè/sát (<{gap}px) lúc {max(a1, a2):.2f}s")
    return errs


_FACE = None
def face_zones(img):
    """Vùng CẤM chữ quanh người trong 1 khung (PIL RGB/RGBA cỡ W×H): [(tên, (x0,y0,x1,y1))].
    YuNet (scripts/data/face_yunet...onnx, OpenCV). "đầu" = mặt nới rộng (tóc, cằm); "vai" = vùng vai–ngực trên.
    Lỗi Corolla Cross v2 (18/11/2026): chữ "3M CR BLK" đè mặt MC, "20 TRIỆU"/"XỨNG ĐÁNG?" sát đầu–vai."""
    global _FACE
    import cv2
    W, H = img.size; k = 640 / W; small = np.asarray(img.convert("RGB").resize((640, round(H * k))))[:, :, ::-1].copy()
    if _FACE is None:
        _FACE = cv2.FaceDetectorYN.create(str(ROOT / "scripts/data/face_detection_yunet_2023mar.onnx"), "", (640, small.shape[0]), 0.7, 0.3, 50)
    _FACE.setInputSize((640, small.shape[0])); _, faces = _FACE.detect(small); res = []
    for f in (faces if faces is not None else []):
        x, y, w, h = (float(v) / k for v in f[:4])
        if h < H * 0.04: continue                         # mặt quá nhỏ (người ở xa) — bỏ
        res.append(("đầu", (x - 0.55 * w, y - 0.75 * h, x + 1.55 * w, y + 1.35 * h)))
        res.append(("vai", (x - 1.3 * w, y + 1.2 * h, x + 2.3 * w, y + 2.6 * h)))
    return res

# ---------------- Khung kính, CTA, nền ----------------
def rounded(im, r, border=2, balpha=110):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, fill=255)
    o = im.convert("RGBA"); o.putalpha(m)
    if border: ImageDraw.Draw(o).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, outline=(255, 255, 255, balpha), width=border)
    return o

def with_shadow(card, blur=28, alpha=170, pad=60, r=36):
    c = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad)); m = Image.new("L", c.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((pad, pad + 14, pad + card.width, pad + card.height + 14), r, fill=alpha)
    sh = Image.new("RGBA", c.size); sh.putalpha(m.filter(ImageFilter.GaussianBlur(blur)))
    c.alpha_composite(sh); c.alpha_composite(card, (pad, pad)); return c

def cta(txt, size=40, color=RED):
    f = ImageFont.truetype(str(F_INTER_BOLD), size); w = int(f.getlength(txt)) + 80; h = int(size * 2.1)
    im = Image.new("RGBA", (w, h)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=color + (255,)); d.text((w / 2, h / 2), txt, font=f, fill=WHITE, anchor="mm")
    return im

def soft_bg(im, tint=(30, 22, 16), k=0.30):
    """Nền mờ sâu, hơi tối, cho khung kính/chữ nổi lên."""
    W, H = im.size
    s = im.resize((W // 6, H // 6), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR)
    return Image.blend(s.convert("RGB"), Image.new("RGB", (W, H), tint), k)

def paste_scaled(canvas, im, cx, cy, s=1.0, a=1.0):
    if s != 1: im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
    if a < 1: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


# ---------------- Âm thanh ----------------
def keep_len(keep, fps):
    """Thời lượng đoạn (khoá theo lưới frame). keep: [(a,b)] giây nguồn, hoặc (None, d) = khoảng lặng d giây."""
    return round(sum((b - a) if a is not None else b for a, b in keep) * fps) / fps

def out2src(keep, o):
    """Giây trong đoạn đã cắt → giây nguồn (khoảng lặng (None,d) trả None)."""
    for a, b in keep:
        d = b if a is None else b - a
        if o <= d: return None if a is None else a + o
        o -= d
    a, b = keep[-1]; return b

def keep_minus(keep, cuts, min_piece=0.12):
    """Bỏ các khúc nói lặp/vấp (cuts: [(a,b)] hoặc [{a,b}] giây nguồn, từ scripts/stutter.py) khỏi keep → keep mới.
    Mảnh còn lại ngắn hơn min_piece bị bỏ (tránh tiếng cụt)."""
    cs = sorted((c["a"], c["b"]) if isinstance(c, dict) else tuple(c) for c in cuts); out = []
    for a, b in keep:
        if a is None: out.append((a, b)); continue
        pieces = [(a, b)]
        for ca, cb in cs:
            nxt = []
            for x, y in pieces:
                if cb <= x or ca >= y: nxt.append((x, y)); continue
                if ca > x: nxt.append((x, ca))
                if cb < y: nxt.append((cb, y))
            pieces = nxt
        out += [(round(x, 3), round(y, 3)) for x, y in pieces if y - x >= min_piece]
    return out

def joins(keep, gap=0.05):
    """Mốc (giây trong đoạn) các MỐI CẮT thật giữa 2 khúc nguồn không liền nhau → hình người nói sẽ nhảy, phải trám."""
    res, o = [], 0
    for i, (a, b) in enumerate(keep):
        d = b if a is None else b - a
        if i and a is not None and keep[i - 1][0] is not None and a - keep[i - 1][1] > gap: res.append(round(o, 3))
        o += d
    return res

def src2out(keep, t):
    """Giây nguồn → giây trong đoạn đã cắt."""
    o = 0
    for a, b in keep:
        if a is None: o += b; continue
        if t < a: return o
        if t <= b: return o + t - a
        o += b - a
    return o

def loudness(path):
    """→ (LUFS tích phân, true peak dBTP)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-threads", TH, "-i", str(path), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    js = r.stderr[r.stderr.rfind("{"):]; d = json.loads(js[:js.index("}") + 1])
    return float(d["input_i"]), float(d["input_tp"])

def cut_voice(src, keep, D, out, target=-17):
    """Ghép các khúc giữ lại của lời đọc: fade in 12 ms / out 15 ms ở mỗi mối cắt, highpass 90 Hz, chuẩn về target LUFS,
    nén nhẹ (2.5:1), đệm/cắt đúng D giây (= thời lượng hình). (None, d) = chèn lặng d giây."""
    tr, lab = [], []
    for i, (a, b) in enumerate(keep):
        if a is None:
            tr.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{b:.3f}[a{i}]")
        else:
            tr.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
                      f"afade=t=in:d=0.012,afade=t=out:st={b - a - 0.015:.3f}:d=0.015[a{i}]")
        lab.append(f"[a{i}]")
    tmp = str(out) + ".raw.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex",
         f"{';'.join(tr)};{''.join(lab)}concat=n={len(lab)}:v=0:a=1,highpass=f=90[o]", "-map", "[o]", tmp])
    li, _ = loudness(tmp)
    run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", f"volume={target - li:.2f}dB,acompressor=threshold=-20dB:ratio=2.5:"
         f"attack=8:release=120,apad=pad_dur=2,atrim=0:{D:.4f}", "-ar", "48000", "-ac", "2", out])
    os.remove(tmp)

def voice_source(src, cache_dir, mode="strong"):
    """Tiếng giọng đã lọc tạp âm của 1 file nguồn (DeepFilterNet, scripts/denoise.py), cache theo tên+cỡ+mtime file.
    mode: "auto" (tự chọn mức theo nền ồn từng file — khuyên dùng) · "strong" (siêu mạnh) · "soft" (giọng nhỏ/xa) · None (giữ nguyên). Thiếu deep-filter → báo và dùng tiếng gốc."""
    if not mode: return src
    src = Path(src); st = src.stat(); cache_dir = Path(cache_dir); cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{src.stem}_{hashlib.md5(f'{src}{st.st_size}{st.st_mtime}{mode}'.encode()).hexdigest()[:8]}_denoise.wav"
    if out.exists(): return out
    sys.path.insert(0, str(ROOT / "scripts")); import denoise as DN
    if not (DN.binary() or _try(DN.install)):
        print("CẢNH BÁO: chưa có deep-filter → dùng tiếng gốc, chưa lọc tạp âm"); return src
    DN.denoise(src, out, soft=(mode == "soft"), auto=(mode == "auto"), quiet=True); print(f"lọc tạp âm ({mode}): {src.name} → {out.name}"); return out

def _try(f):
    try: return f()
    except BaseException as e: print("deep-filter:", e); return None

def load_mono(path, ss=None, dur=None, sr=48000):
    a = ["ffmpeg", "-threads", TH, "-v", "error"] + (["-ss", f"{ss:.3f}", "-t", f"{dur:.3f}"] if ss is not None else []) + \
        ["-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(a, capture_output=True).stdout, np.float32).astype(np.float64)

def music_bed(path, NS, sr=48000, xf=1.5):
    """Nhạc nền dài đúng NS mẫu (mono, chuẩn đỉnh 1): bài ngắn hơn clip thì nối vòng, hoà âm xf giây ở mỗi chỗ nối (không giật)."""
    trk = load_mono(path, sr=sr); trk /= (np.abs(trk).max() + 1e-9); X = int(xf * sr)
    out = trk.copy()
    while len(out) < NS:
        r = np.linspace(0, 1, X); out = np.concatenate([out[:-X], out[-X:] * (1 - r) + trk[:X] * r, trk[X:]])
    return out[:NS]

def resolve_music(music, key=""):
    """MUSIC trong build: None | đường dẫn | "auto" | "auto:<mood>" (tech/drive/groove/warm) → (path|None, mô tả)."""
    if not music: return None, "không nhạc"
    if isinstance(music, str) and music.startswith("auto"):
        sys.path.insert(0, str(ROOT / "scripts")); import music as M
        return M.pick(music.split(":", 1)[1] if ":" in music else "auto", key)
    return Path(music), Path(music).name

def write_wav(path, x, sr=48000):
    from scipy.io import wavfile
    wavfile.write(str(path), sr, np.repeat((np.clip(x, -1, 1) * 32767).astype(np.int16)[:, None], 2, 1))

_SFX = {}
def sfx_place(bus, rel, at, gain, align="peak", maxlen=None, sr=48000):
    """Đặt 1 SFX vào bus (mảng numpy mono, dài = tổng thời lượng × sr). rel tính từ assets/sfx (vd. "whoosh/Swoosh_20.wav").
    SFX được chuẩn đỉnh = 1 rồi nhân gain (bảng gain chuẩn: assets/sfx/QUY_TAC_SU_DUNG.md).
    align="peak": đỉnh SFX rơi đúng mốc `at` (whoosh vào điểm cắt); "start": SFX bắt đầu tại `at` (hit, tick, click).
    maxlen: cắt SFX còn maxlen giây, fade-out 50 ms ở đuôi (impact dài)."""
    if rel not in _SFX:
        p = ROOT / "assets/sfx" / rel
        if not p.exists(): raise FileNotFoundError(f"Không thấy SFX {p} (tên phải đúng từng ký tự, kể cả dấu cách)")
        x = load_mono(p, sr=sr); x /= np.abs(x).max() + 1e-9
        _SFX[rel] = (x, int(np.convolve(np.abs(x), np.ones(480) / 480, "same").argmax()))
    x, pk = _SFX[rel]
    if maxlen:
        n = min(int(maxlen * sr), len(x)); f = min(2400, n); x = x[:n].copy(); x[n - f:] *= np.linspace(1, 0, f)
    i = int(at * sr) - (pk if align == "peak" else 0)
    if i < 0: x = x[-i:]; i = 0
    seg = x[:max(0, len(bus) - i)]; bus[i:i + len(seg)] += seg * gain
    return bus

def final_mix(voice, sfx, music, out, extra=None):
    """voice (+extra, vd. tiếng hiện trường) làm sidechain duck nhạc; cộng SFX; loudnorm -14 LUFS / TP -1.5."""
    ins = ["-i", voice, "-i", sfx, "-i", music] + (["-i", extra] if extra else [])
    v = "[0:a][3:a]amix=inputs=2:normalize=0[vn];[vn]" if extra else "[0:a]"
    run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", f"{v}asplit=2[vo][vk];[2:a][vk]sidechaincompress=threshold=0.03:"
         f"ratio=6:attack=15:release=300[md];[vo][1:a][md]amix=inputs=3:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=9[m]",
         "-map", "[m]", "-ar", "48000", out])

def mux(video, audio, out):
    # Không dùng -shortest: tiếng ngắn hơn hình vài ms làm rơi khung cuối (31/10/2026: 169/173 khung). Đệm lặng + cắt theo độ dài hình.
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True).stdout.strip()
    run(["ffmpeg", "-y", "-v", "error", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "apad",
         "-c:a", "aac", "-b:a", "256k", "-t", dur, "-movflags", "+faststart", out])


# ---------------- Tự kiểm ----------------
if __name__ == "__main__" and "--selftest" in sys.argv:
    W, H = 1080, 1920
    ws = [Word("ÁNH SÁNG", "k", 100, 0), Word("rõ hơn", "it", 76, 0.3)]
    pl = layout_line(ws, 1235, W, H); bx = line_box(pl)
    cap = cap_img("đây là một câu phụ đề khá dài để thử tự bẻ hai dòng cho khung dọc", size=48, font=F_BVP_BOLD, W=W, keyword="phụ đề")
    cb = (W // 2 - cap.width // 2, 1270 - cap.height // 2, W // 2 + cap.width // 2, 1270 + cap.height // 2)
    print("kin box", bx, "| cap", cap.size, "| layout errs:", check_layout([("kin", bx, 0, 2), ("cap", cb, 1, 3)], W, H))
    try: layout_line([Word("LOẠI NÀO CŨNG ĐƯỢC LUÔN NHA", "k", 130, 0)], 1300, W, H); print("FAIL: không bắt tràn")
    except ValueError as e: print("bắt tràn OK:", str(e)[:60])
    fr = Image.new("RGBA", (W, H), (60, 60, 60, 255))
    for w, x, y in pl: w.draw(fr, 1.0, x, y)
    fr.alpha_composite(cap, (cb[0], cb[1])); out = ROOT / "work/_e365_selftest.png"; out.parent.mkdir(exist_ok=True)
    fr.convert("RGB").save(out); print("OK →", out)
