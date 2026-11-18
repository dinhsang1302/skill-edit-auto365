#!/usr/bin/env python3
"""Mẫu build chuẩn cho 1 dự án (dùng thư viện scripts/e365.py).

Làm gì: dựng clip theo danh sách đoạn SEGS — mỗi đoạn = 1 câu lời đọc (keep = khúc giữ lại trong nguồn tiếng),
hình = các shot (clip + giây nguồn + zoom/tâm), phụ đề PNG, chữ động theo từng từ. Render tuần tự từng đoạn
(1 ffmpeg đọc + 1 python vẽ + 1 ffmpeg encode), cache theo hash nội dung đoạn → sửa đoạn nào chỉ render lại đoạn đó.
Giọng: lọc tạp âm DeepFilterNet trước (DENOISE), bỏ khúc nói LẶP/VẤP theo "cuts" (scripts/stutter.py) — mỗi mối cắt trong cảnh
người nói tự được TRÁM bằng insert/animation ("covers"), build từ chối render nếu còn mối cắt chưa trám.
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
Độ phân giải (anh chốt 18/11/2026): NHÁP để rà = 360p (vẽ thẳng ở 640x360 / 360x640 → rất nhanh, file nhẹ);
  BẢN GIAO (clip chính) = 4K (3840x2160 / 2160x3840, vẽ chữ thẳng ở 4K cho nét, encode HEVC phần cứng 45 Mbit; máy không GPU → libx264).
  Toạ độ/cỡ chữ trong SEGS, CAP luôn viết theo khung THIẾT KẾ W×H (1920x1080 hoặc 1080x1920); build tự nhân hệ số E.S.
  Ép cỡ khác: RES=<cạnh ngắn> (vd. RES=1080).
Tham số môi trường: FINAL=1 (bản giao), VER=<n> (số phiên bản, mỗi lần sửa tăng 1, không ghi đè bản cũ),
  SKIP_CHECK=1 (bỏ qua soát bố cục — chỉ khi đã soát mắt).
"""
import os, sys, json, hashlib, zlib, numpy as np
from pathlib import Path
from PIL import Image

PRJ = Path(__file__).resolve().parents[1]                  # projects/<X>
ROOT = next(p for p in [PRJ, *PRJ.parents] if (p / "scripts/e365.py").exists())
sys.path.insert(0, str(ROOT / "scripts"))
import e365 as E

# ---------------- CẤU HÌNH ----------------
NAME = "Demo"                                               # tên sản phẩm trong tên file giao
W, H, FPS = 1920, 1080, 30                                  # khung THIẾT KẾ 16:9; bản 9:16 → 1080, 1920. FPS = đúng fps nguồn
RATIO = "9x16" if H > W else "16x9"
THEME = "dark"                                              # Skill Edit Auto365: Anton trắng + keyword đỏ + Playfair nghiêng
GRADE = E.GRADE_NEUTRAL
CAP = dict(size=56 if H > W else 66, font=E.F_CAPTION, y=int(H * 0.66) if H > W else int(H * 0.86))
MUSIC = "auto"                                              # "auto" tự chọn nhạc có giấy phép (scripts/music.py) · "auto:drive" theo mood tech/drive/groove/warm · đường dẫn file · None
MUSIC_GAIN = 0.22
SFX_WHOOSH = None                                           # vd. "whoosh/Transitions SFX_13.wav" (tính từ assets/sfx) — chỉ ở chuyển cảnh lớn; bảng chuẩn: assets/sfx/QUY_TAC_SU_DUNG.md
DENOISE = "strong"                                          # lọc tạp âm giọng: "strong" siêu mạnh · "soft" giọng nhỏ/xa · None tắt
FACE_CHECK = True                                           # chặn render nếu chữ động đè đầu/vai người (YuNet) — không tắt khi giao bản
AUTO_COVER = True                                           # thiếu covers → tự lấy ảnh/clip có sẵn trong insert/; không có gì → punch-in (đổi cỡ khung)
COVER = 2.0                                                 # giây trám quanh mỗi mối cắt lặp/vấp (≥ 1,5 s, ≤ 3 s)
VER = int(os.environ.get("VER", "1")); FINAL = os.environ.get("FINAL") == "1"
OUT = PRJ / "work/seg"; OUT.mkdir(parents=True, exist_ok=True)
RES = int(os.environ.get("RES") or (2160 if FINAL else 360))  # cạnh ngắn: nháp 360p, bản giao 4K
DELIVER = PRJ / "output" / (f"{NAME}_{RATIO}_v{VER}" + ("" if FINAL else f"_nhap{RES}p") + ".mp4")

def sh(o, src, ss, **p): return (o, src, ss, p)             # shot: (giây trong đoạn, file trong dự án, giây nguồn, z=(z0,z1), c=(cx,cy))
def K(y, *words, x=None, align="center", end=None):        # 1 dòng chữ động; words = (giây nguồn, chữ, kiểu w|k|it, cỡ)
    return dict(y=y, x=x, align=align, words=list(words), end=end)

# keep: [(a,b)] giây nguồn tiếng; (None, d) = khoảng lặng d giây (vd. để nghe tiếng hiện trường)
# cuts: [(a,b)] giây nguồn bỏ đi vì nói LẶP (giữ lần cuối) / VẤP — lấy từ scripts/stutter.py SAU KHI nghe lại từng chỗ
# shots: sh(..., sync=True) = cảnh người nói khớp tiếng: tự nhảy theo từng khúc keep (không lệch môi sau khi cắt)
# covers: [(file ảnh/clip, giây nguồn, z)] — mỗi mối cắt trong đoạn lấy 1 cái theo thứ tự, phủ COVER giây quanh mối cắt.
#   Nên dùng insert khớp lời (ảnh sản phẩm, b-roll, thẻ thông số). Không khai báo đủ → AUTO_COVER tự lấy tư liệu có sẵn trong insert/.
#   Codex vẽ minh hoạ là TUỲ CHỌN (chỉ khi máy có Codex CLI); không có Codex vẫn dựng bình thường bằng tư liệu có sẵn.
# caps: [(giây nguồn, "câu phụ đề", "keyword hoặc None")] — lấy từ transcript ĐÃ HIỆU ĐÍNH (scripts/words_to_caps.py)
SEGS = [
    dict(id="01", a="input/demo.mp4", keep=[(0.0, 3.4)], shots=[sh(0, "input/demo.mp4", 0.0, z=(1.0, 1.06), c=(.5, .45))],
         caps=[], kin=[K(int(H * 0.40), (0.2, "DEMO", "w", 120), (0.5, "dựng", "it", 80)),
                       K(int(H * 0.40) + 200, (0.6, "AUTO365", "k", 130))]),
    dict(id="02", a="input/demo.mp4", keep=[(3.6, 5.8)], shots=[sh(0, "input/demo.mp4", 3.6, z=(1.1, 1.2), c=(.5, .5))],
         caps=[(3.7, "đây là phụ đề chạy thử", "phụ đề")], kin=[]),
    # Ví dụ đoạn có chỗ lặp được cắt + trám:
    # dict(id="03", a="input/A001.mp4", keep=[(12.0, 18.5)], cuts=[(13.10, 13.62)],
    #      shots=[sh(0, "input/A001.mp4", 12.0, z=(1.0, 1.04), sync=True)],
    #      covers=[("insert/hop_san_pham.jpg", 0, (1.0, 1.08))], caps=[...], kin=[]),
]
for _s in SEGS:                                             # bỏ khúc lặp/vấp khỏi keep (giữ bản gốc ở keep0 để tra)
    if _s.get("cuts"): _s["keep0"] = _s["keep"]; _s["keep"] = E.keep_minus(_s["keep"], _s["cuts"])

# ---- đổi khung thiết kế → khung render (nháp 360p / giao 4K): mọi toạ độ, cỡ chữ nhân E.S ----
E.S = RES / min(W, H)
W, H = round(W * E.S / 2) * 2, round(H * E.S / 2) * 2
CAP = dict(CAP, size=round(CAP["size"] * E.S), y=round(CAP["y"] * E.S))
for _s in SEGS:
    for ln in _s.get("kin", []):
        ln["y"] = round(ln["y"] * E.S); ln["x"] = None if ln["x"] is None else round(ln["x"] * E.S)
        ln["words"] = [(t, txt, sty, round(size * E.S)) for t, txt, sty, size in ln["words"]]
# ------------------------------------------

def seg_len(s): return E.keep_len(s["keep"], FPS)
def s2o(s, t): return E.src2out(s["keep"], t)

def kin_placed(s):
    L = seg_len(s); res = []
    for ln in s.get("kin", []):
        t_out = s2o(s, ln["end"]) if ln["end"] else L - E.Word.OUT - 0.05   # xuống hết trước khi cắt cảnh
        ws = [E.Word(txt, sty, size, s2o(s, t), t_out, slide=-1 if i % 2 == 0 else 1, theme=THEME)
              for i, (t, txt, sty, size) in enumerate(ln["words"])]
        pl = E.layout_line(ws, ln["y"], W, H, ln["x"], ln["align"])
        res.append((pl, min(w.t_in for w in ws), max(w.t_out for w in ws) + E.Word.OUT))
    return res

def caps_of(s):
    L = seg_len(s); c = [(s2o(s, t), txt, kw) for t, txt, kw in s["caps"]]
    return [(o, c[i + 1][0] if i + 1 < len(c) else L, E.cap_img(txt, CAP["size"], CAP["font"], W=W, keyword=kw))
            for i, (o, txt, kw) in enumerate(c)]

def auto_covers():
    """Tư liệu có sẵn để tự trám: ảnh/clip trong insert/ của dự án (kể cả insert/ai nếu đã có). Không cần Codex."""
    exts = E.IMG_EXT + (".mp4", ".mov", ".m4v")
    return sorted(p for p in (PRJ / "insert").rglob("*") if p.suffix.lower() in exts and not p.name.startswith("."))

def shots_of(s):
    """Danh sách shot thật để render: tách shot sync theo từng khúc keep, rồi chèn insert trám quanh mỗi mối cắt."""
    L = seg_len(s); keep = s["keep"]; res = []; sh0 = s["shots"]
    for k, (o0, src, ss, p) in enumerate(sh0):
        o1 = sh0[k + 1][0] if k + 1 < len(sh0) else L
        if not p.get("sync"): res.append((o0, src, ss, p)); continue
        o = 0
        for a, b in keep:
            d = b if a is None else b - a
            if a is not None and o + d > o0 and o < o1: res.append((max(o, o0), src, a + max(0, o0 - o), p))
            o += d
    cov = list(s.get("covers", [])); pool = auto_covers(); n = 0
    for j in E.joins(keep):
        if not cov and AUTO_COVER and pool:                 # hết covers khai báo → tự lấy tư liệu có sẵn trong insert/ (xoay vòng)
            f = pool[(zlib.crc32(s["id"].encode()) + n) % len(pool)]; n += 1; cov.append((str(f.relative_to(PRJ)), 0, (1.0, 1.08)))
        if not cov:
            if AUTO_COVER:                                  # không có tư liệu nào → punch-in: đổi cỡ khung ngay mối cắt để che cú nhảy hình
                k = [i for i, x in enumerate(res) if x[0] <= j + 1e-6][-1]; o0, src, ss, p = res[k]
                if p.get("sync") and abs(o0 - j) < 1e-3:
                    z0 = p.get("z", (1, 1))[0]; zz = 1.18 if z0 < 1.1 else 1.0
                    res[k] = (o0, src, ss, dict(p, z=(zz, zz), punch=True))
            continue
        f, css, z = cov.pop(0); a, b = max(0, j - COVER / 2), min(L, j + COVER / 2)
        back = [x for x in res if x[0] <= b + 1e-6][-1]   # shot đang chạy lúc hết trám → tiếp tục đúng nguồn
        res = [x for x in res if not (a <= x[0] < b)] + [(a, f, css, dict(z=z, cover=True))]
        if b < L - 1e-3:
            o0, src, ss, p = back
            res.append((b, src, (E.out2src(keep, b) if p.get("sync") else ss + b - o0), p))
    return sorted(res, key=lambda x: x[0])

def frame_at(s, t):
    """Khung hình (W×H) của đoạn tại giây t — để soát chữ đè mặt trước khi render."""
    sh = shots_of(s); L = seg_len(s); k = max(j for j, x in enumerate(sh) if x[0] <= t + 1e-6)
    o0, src, ss, p = sh[k]; o1 = sh[k + 1][0] if k + 1 < len(sh) else L
    z0, z1 = p.get("z", (1, 1)); z = z0 + (z1 - z0) * E.smooth((t - o0) / max(o1 - o0, 1e-3))
    rd = E.reader_for(PRJ / src, ss + (t - o0), W, H, z=(z, z), fps=FPS, grade=GRADE)
    try: return E.frame_from(rd, W, H, z, p.get("c", (.5, .5)))
    finally: rd.close()

def check_faces(s):
    """Chữ động không được đè đầu/vai người (soát 3 khung mỗi dòng chữ: lúc hiện, giữa, lúc xuống)."""
    errs = []
    for pl, a, b in kin_placed(s):
        bx = E.line_box(pl); txt = " ".join(w.text for w, _, _ in pl)
        for t in sorted({round(a + 0.3, 2), round((a + b) / 2, 2), round(max(a, b - 0.5), 2)}):
            for zone, z in E.face_zones(frame_at(s, min(t, seg_len(s) - 0.05))):
                if E.boxes_overlap(bx, tuple(map(int, z)), 16):
                    side = "bên trái" if (z[0] + z[2]) / 2 > W / 2 else "bên phải"
                    errs.append(f"đoạn {s['id']}: chữ '{txt}' đè {zone} người lúc {t:.2f}s → dời sang {side} khung (đối diện người) hoặc hạ xuống vùng trống")
                    break
            else: continue
            break
    return errs

def check(s):
    """Soát trước: chữ động lòi khung / đè phụ đề / sát nhau. Phụ đề tự ẩn khi chữ động đang hiện,
    nên chỉ báo khi hai thứ thật sự cùng hiện."""
    items = [(f"kin{j}", E.line_box(pl), a, b) for j, (pl, a, b) in enumerate(kin_placed(s))]
    kin_t = [(a, b) for _, _, a, b in items]
    for i, (a, b, im) in enumerate(caps_of(s)):
        vis = [(a, b)] if not any(x < b and a < y for x, y in kin_t) else []
        for va, vb in vis:
            items.append((f"cap{i}", (W // 2 - im.width // 2, CAP["y"] - im.height // 2, W // 2 + im.width // 2, CAP["y"] + im.height // 2), va, vb))
    errs = [f"đoạn {s['id']}: {e}" for e in E.check_layout(items, W, H)]
    L = seg_len(s); sh = shots_of(s)                        # mối cắt lặp/vấp trong cảnh người nói phải được trám
    for j in E.joins(s["keep"]):
        cur = [x for x in sh if x[0] <= j + 1e-6][-1]
        if cur[3].get("sync") and not cur[3].get("punch"): errs.append(f"đoạn {s['id']}: mối cắt {j:.2f}s chưa trám → thêm 1 mục vào covers")
    for pl, a, b in kin_placed(s):                          # chữ phải đứng đủ HOLD_MIN và xuống hết trước khi hết đoạn
        if b > L + 0.01: errs.append(f"đoạn {s['id']}: chữ '{pl[0][0].text}…' cần tới {b:.2f}s (đứng ≥ {E.Word.HOLD_MIN}s) > đoạn {L:.2f}s → hiện sớm hơn hoặc gộp")
    return errs

def render_seg(s, path):
    L = seg_len(s); N = round(L * FPS); caps = caps_of(s); kins = kin_placed(s)
    enc = E.Encoder(path, W, H, FPS, final=FINAL); shots = shots_of(s); rd = None; cur = -1
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
    return hashlib.md5((json.dumps(s, sort_keys=True, ensure_ascii=False, default=str) + src + str(FINAL) + str(RES) + str(auto_covers())).encode()).hexdigest()[:10]

def job(s):
    p = OUT / f"seg_{s['id']}_{seg_hash(s)}.mp4"
    if not p.exists(): render_seg(s, p)
    return p

def audio(total, starts):
    parts = []
    for s in SEGS:
        f = OUT / f"v_{s['id']}.wav"
        E.cut_voice(E.voice_source(PRJ / s["a"], OUT / "denoise", DENOISE), s["keep"], seg_len(s), f); parts.append(f)
    E.concat(parts, OUT / "voice.wav", audio_wav=True)
    SR = 48000; NS = int(total * SR); t = np.arange(NS) / SR
    mus = np.zeros(NS); sfx = np.zeros(NS)
    mpath, mdesc = E.resolve_music(MUSIC, str(PRJ.name)); print("nhạc nền:", mdesc)
    if mpath:
        mus = E.music_bed(mpath, NS) * np.clip(t / .3, 0, 1) * np.clip((total - t) / 1.5, 0, 1) * MUSIC_GAIN
    if SFX_WHOOSH:                                          # whoosh ở mỗi chuyển đoạn (đỉnh rơi đúng điểm cắt)
        for st in starts[1:]: E.sfx_place(sfx, SFX_WHOOSH, st, 0.22)
    # thêm SFX theo bảng chuẩn, vd.: E.sfx_place(sfx, "tick_click/Click_16.wav", t_so + 0.10, 0.22, "start")
    E.write_wav(OUT / "music.wav", mus); E.write_wav(OUT / "sfx.wav", sfx)
    E.final_mix(OUT / "voice.wav", OUT / "sfx.wav", OUT / "music.wav", OUT / "mix.wav")

if __name__ == "__main__":
    E.start_cpu_watch(PRJ / "work/cpu_watch.log", 50)      # luật máy: trần 500% CPU suốt job
    print(f"render {W}x{H} ({'BẢN GIAO' if FINAL else 'NHÁP rà'}{' 4K' if min(W, H) >= 2160 else f' {RES}p'})")
    if FINAL and min(W, H) >= 2160:
        lo = [s["a"] for s in SEGS if min(E.probe(PRJ / s["a"])["w"], E.probe(PRJ / s["a"])["h"]) < 2160]
        if lo: print("  lưu ý: nguồn dưới 4K sẽ được phóng lên 4K:", ", ".join(sorted(set(map(str, lo)))))
    only = sys.argv[1:]; todo = [s for s in SEGS if not only or s["id"] in only]
    errs = sum((check(s) + (check_faces(s) if FACE_CHECK else []) for s in todo), [])
    if errs and os.environ.get("SKIP_CHECK") != "1": raise SystemExit("Soát bố cục lỗi:\n  " + "\n  ".join(errs))
    paths = [job(s) for s in todo]                          # tuần tự, từng đoạn một
    if only: print("\n".join(map(str, paths))); sys.exit()
    E.concat(paths, OUT / "video.mp4")
    lens = [seg_len(s) for s in SEGS]; starts = list(np.cumsum([0] + lens)[:-1]); total = sum(lens)
    audio(total, starts)
    DELIVER.parent.mkdir(exist_ok=True); E.mux(OUT / "video.mp4", OUT / "mix.wav", DELIVER)
    li, tp = E.loudness(DELIVER); print(f"OK {DELIVER}  {total:.2f}s  {li:.1f} LUFS / TP {tp:.1f}")
