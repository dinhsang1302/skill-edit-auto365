#!/usr/bin/env python3
"""Mẫu build chuẩn cho 1 dự án (dùng thư viện scripts/e365.py).

Làm gì: dựng clip theo danh sách đoạn SEGS — mỗi đoạn = 1 câu lời đọc (keep = khúc giữ lại trong nguồn tiếng),
hình = các shot (clip + giây nguồn + zoom/tâm), phụ đề PNG, chữ động theo từng từ. Render tuần tự từng đoạn
(1 ffmpeg đọc + 1 python vẽ + 1 ffmpeg encode), cache theo hash nội dung đoạn → sửa đoạn nào chỉ render lại đoạn đó.
Âm thanh: cắt lời theo keep (fade 12/15 ms), nhạc duck theo giọng, SFX, -14 LUFS / TP -1.5. Soát bố cục chữ trước khi render.

Cách dùng:
  1. Chép vào dự án:  cp scripts/build_template.py projects/<X>/work/build.py
  2. Sửa phần CẤU HÌNH + SEGS (đường dẫn file tính từ thư mục dự án).
  3. Chạy (từ thư mục làm việc; <python> = .venv/bin/python trên Mac, .venv\\Scripts\\python trên Windows):
       <python> projects/<X>/work/build.py            # nháp toàn bộ (encode GPU: videotoolbox / nvenc)
       <python> projects/<X>/work/build.py 01 03      # chỉ render nháp đoạn 01, 03 (xem nhanh)
       bản giao libx264 → output/<NAME>_<ratio>_v2.mp4:
         Mac:        FINAL=1 VER=2 .venv/bin/python projects/<X>/work/build.py
         PowerShell: $env:FINAL=1; $env:VER=2; .venv\\Scripts\\python projects\\<X>\\work\\build.py; Remove-Item Env:FINAL,Env:VER
Tham số môi trường: FINAL=1 (bản giao), VER=<n> (số phiên bản, mỗi lần sửa tăng 1, không ghi đè bản cũ),
  SKIP_CHECK=1 (bỏ qua soát bố cục — chỉ khi đã soát mắt).
"""
import os, sys, json, hashlib, numpy as np
from pathlib import Path
from PIL import Image

PRJ = Path(__file__).resolve().parents[1]                  # projects/<X>
ROOT = next(p for p in [PRJ, *PRJ.parents] if (p / "scripts/e365.py").exists())
sys.path.insert(0, str(ROOT / "scripts"))
import e365 as E

# ---------------- CẤU HÌNH ----------------
NAME = "Demo"                                               # tên sản phẩm trong tên file giao
W, H, FPS = 1920, 1080, 30                                  # 16:9; bản 9:16 → 1080, 1920. FPS = đúng fps nguồn
RATIO = "9x16" if H > W else "16x9"
THEME = "dark"                                              # Skill Edit Auto365: Anton trắng + keyword đỏ + Playfair nghiêng
GRADE = E.GRADE_NEUTRAL
CAP = dict(size=56 if H > W else 66, font=E.F_CAPTION, y=int(H * 0.66) if H > W else int(H * 0.86))
MUSIC = None                                                # vd. ROOT / "assets/music/_downloaded/mixkit_better_times_are_coming_440.mp3"
MUSIC_GAIN = 0.22
SFX_WHOOSH = None                                           # vd. "whoosh/Transitions SFX_13.wav" (tính từ assets/sfx) — chỉ ở chuyển cảnh lớn; bảng chuẩn: assets/sfx/QUY_TAC_SU_DUNG.md
VER = int(os.environ.get("VER", "1")); FINAL = os.environ.get("FINAL") == "1"
OUT = PRJ / "work/seg"; OUT.mkdir(parents=True, exist_ok=True)
DELIVER = PRJ / "output" / (f"{NAME}_{RATIO}_v{VER}" + ("" if FINAL else "_nhap") + ".mp4")

def sh(o, src, ss, **p): return (o, src, ss, p)             # shot: (giây trong đoạn, file trong dự án, giây nguồn, z=(z0,z1), c=(cx,cy))
def K(y, *words, x=None, align="center", end=None):        # 1 dòng chữ động; words = (giây nguồn, chữ, kiểu w|k|it, cỡ)
    return dict(y=y, x=x, align=align, words=list(words), end=end)

# keep: [(a,b)] giây nguồn tiếng; (None, d) = khoảng lặng d giây (vd. để nghe tiếng hiện trường)
# caps: [(giây nguồn, "câu phụ đề", "keyword hoặc None")] — lấy từ transcript ĐÃ HIỆU ĐÍNH (scripts/words_to_caps.py)
SEGS = [
    dict(id="01", a="input/demo.mp4", keep=[(0.0, 2.2)], shots=[sh(0, "input/demo.mp4", 0.0, z=(1.0, 1.06), c=(.5, .45))],
         caps=[], kin=[K(int(H * 0.40), (0.2, "DEMO", "w", 120), (0.7, "dựng", "it", 80)),
                       K(int(H * 0.40) + 200, (1.0, "AUTO365", "k", 130))]),
    dict(id="02", a="input/demo.mp4", keep=[(2.6, 5.4)], shots=[sh(0, "input/demo.mp4", 2.6, z=(1.1, 1.2), c=(.5, .5))],
         caps=[(2.7, "đây là phụ đề chạy thử", "phụ đề")], kin=[]),
]
# ------------------------------------------

def seg_len(s): return E.keep_len(s["keep"], FPS)
def s2o(s, t): return E.src2out(s["keep"], t)

def kin_placed(s):
    L = seg_len(s); res = []
    for ln in s.get("kin", []):
        t_out = s2o(s, ln["end"]) if ln["end"] else L - 0.24
        ws = [E.Word(txt, sty, size, s2o(s, t), t_out, slide=-1 if i % 2 == 0 else 1, theme=THEME)
              for i, (t, txt, sty, size) in enumerate(ln["words"])]
        pl = E.layout_line(ws, ln["y"], W, H, ln["x"], ln["align"])
        res.append((pl, min(w.t_in for w in ws), t_out + E.Word.OUT))
    return res

def caps_of(s):
    L = seg_len(s); c = [(s2o(s, t), txt, kw) for t, txt, kw in s["caps"]]
    return [(o, c[i + 1][0] if i + 1 < len(c) else L, E.cap_img(txt, CAP["size"], CAP["font"], W=W, keyword=kw))
            for i, (o, txt, kw) in enumerate(c)]

def check(s):
    """Soát trước: chữ động lòi khung / đè phụ đề / sát nhau. Phụ đề tự ẩn khi chữ động đang hiện,
    nên chỉ báo khi hai thứ thật sự cùng hiện."""
    items = [(f"kin{j}", E.line_box(pl), a, b) for j, (pl, a, b) in enumerate(kin_placed(s))]
    kin_t = [(a, b) for _, _, a, b in items]
    for i, (a, b, im) in enumerate(caps_of(s)):
        vis = [(a, b)] if not any(x < b and a < y for x, y in kin_t) else []
        for va, vb in vis:
            items.append((f"cap{i}", (W // 2 - im.width // 2, CAP["y"] - im.height // 2, W // 2 + im.width // 2, CAP["y"] + im.height // 2), va, vb))
    return [f"đoạn {s['id']}: {e}" for e in E.check_layout(items, W, H)]

def render_seg(s, path):
    L = seg_len(s); N = round(L * FPS); caps = caps_of(s); kins = kin_placed(s)
    enc = E.Encoder(path, W, H, FPS, final=FINAL); shots = s["shots"]; rd = None; cur = -1
    for i in range(N):
        t = i / FPS
        k = max(j for j, x in enumerate(shots) if x[0] <= t + 1e-6)
        o0, src, ss, p = shots[k]; o1 = shots[k + 1][0] if k + 1 < len(shots) else L
        z0, z1 = p.get("z", (1, 1))
        if k != cur:
            if rd: rd.close()
            rd = E.reader_for(PRJ / src, ss, W, H, z=(z0, z1), fps=FPS, grade=GRADE); cur = k
        z = z0 + (z1 - z0) * E.smooth((t - o0) / max(o1 - o0, 1e-3))
        fr = E.frame_from(rd, W, H, z, p.get("c", (.5, .5))).convert("RGBA")
        kin_on = any(a <= t <= b for _, a, b in kins)
        for a, b, im in caps:                               # phụ đề nhường chỗ khi chữ động hiện (tránh đè)
            if a <= t < b and not kin_on: E.paste_scaled(fr, im, W / 2, CAP["y"], E.pop_scale(t - a))
        for pl, _, _ in kins:
            for w, x, y in pl: w.draw(fr, t, x, y)
        enc.write(fr)
    rd.close(); enc.close()

def seg_hash(s):
    src = Path(__file__).read_text() + Path(E.__file__).read_text()
    return hashlib.md5((json.dumps(s, sort_keys=True, ensure_ascii=False, default=str) + src + str(FINAL)).encode()).hexdigest()[:10]

def job(s):
    p = OUT / f"seg_{s['id']}_{seg_hash(s)}.mp4"
    if not p.exists(): render_seg(s, p)
    return p

def audio(total, starts):
    parts = []
    for s in SEGS:
        f = OUT / f"v_{s['id']}.wav"; E.cut_voice(PRJ / s["a"], s["keep"], seg_len(s), f); parts.append(f)
    E.concat(parts, OUT / "voice.wav", audio_wav=True)
    SR = 48000; NS = int(total * SR); t = np.arange(NS) / SR
    mus = np.zeros(NS); sfx = np.zeros(NS)
    if MUSIC:
        trk = E.load_mono(MUSIC); mus = np.tile(trk, int(np.ceil(NS / len(trk))))[:NS] / (np.abs(trk).max() + 1e-9)
        mus *= np.clip(t / .3, 0, 1) * np.clip((total - t) / 1.5, 0, 1) * MUSIC_GAIN
    if SFX_WHOOSH:                                          # whoosh ở mỗi chuyển đoạn (đỉnh rơi đúng điểm cắt)
        for st in starts[1:]: E.sfx_place(sfx, SFX_WHOOSH, st, 0.22)
    # thêm SFX theo bảng chuẩn, vd.: E.sfx_place(sfx, "tick_click/Click_16.wav", t_so + 0.10, 0.22, "start")
    E.write_wav(OUT / "music.wav", mus); E.write_wav(OUT / "sfx.wav", sfx)
    E.final_mix(OUT / "voice.wav", OUT / "sfx.wav", OUT / "music.wav", OUT / "mix.wav")

if __name__ == "__main__":
    E.start_cpu_watch(PRJ / "work/cpu_watch.log", 50)      # luật máy: trần 500% CPU suốt job
    only = sys.argv[1:]; todo = [s for s in SEGS if not only or s["id"] in only]
    errs = sum((check(s) for s in todo), [])
    if errs and os.environ.get("SKIP_CHECK") != "1": raise SystemExit("Soát bố cục lỗi:\n  " + "\n  ".join(errs))
    paths = [job(s) for s in todo]                          # tuần tự, từng đoạn một
    if only: print("\n".join(map(str, paths))); sys.exit()
    E.concat(paths, OUT / "video.mp4")
    lens = [seg_len(s) for s in SEGS]; starts = list(np.cumsum([0] + lens)[:-1]); total = sum(lens)
    audio(total, starts)
    DELIVER.parent.mkdir(exist_ok=True); E.mux(OUT / "video.mp4", OUT / "mix.wav", DELIVER)
    li, tp = E.loudness(DELIVER); print(f"OK {DELIVER}  {total:.2f}s  {li:.1f} LUFS / TP {tp:.1f}")
