#!/usr/bin/env python3
"""Đo RUNG tay máy, chọn khúc ổn định, chống rung cảnh người nói.

Cách đo: giải mã 1 luồng CPU ở 320x180 xám, dịch chuyển toàn khung giữa 2 khung liền (phase correlation);
rung = phần dao động nhanh (dịch chuyển trừ trung bình trượt 0,5 s), đơn vị px/khung quy về khung 1920 rộng.
Lia máy / dolly / gimbal đi đều KHÔNG bị tính là rung. Kết quả cache ở <thư mục file>/../work/shake/ (hoặc cạnh file).

Ngưỡng (đo 18/11/2026 trên clip xưởng: chân máy/gimbal 0,04–0,2 · cầm tay vững 0,2–0,5 · rung > 1 · đầu clip lúc bấm máy 5–15):
  ỔN ≤ 0,35 TB và đỉnh ≤ 1,2 · RUNG NHẸ ≤ 1,0 (cảnh người nói → chống rung) · RUNG NẶNG > 1,0 (bỏ / phủ insert)

Dùng:
  <python> scripts/shake.py <giây> <clip>…          in rung TB cả clip + khúc <giây> ổn nhất (bỏ 0,5 s đầu)
  <python> scripts/shake.py --stab <clip> <out.mp4>  chống rung (ffmpeg deshake + phóng 6 % che viền)
Trong build: E/shake.window(path, a, b) → (TB, đỉnh); best(path, dur) → giây bắt đầu; stabilized(path) → file đã chống rung (cache).
"""
import hashlib, os, subprocess, sys
from pathlib import Path
import numpy as np

if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
W, H = 320, 180
OK_MEAN, OK_PEAK, LIGHT = 0.35, 1.2, 1.0


def _frames(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-threads", "1", "-i", str(path), "-vf", f"scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    n = W * H
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(H, W).astype(np.float32)
    p.wait()


def _shift(a, b, win):
    A = np.fft.fft2((a - a.mean()) * win); B = np.fft.fft2((b - b.mean()) * win)
    R = A * np.conj(B); R /= np.abs(R) + 1e-9
    r = np.fft.ifft2(R).real; y, x = np.unravel_index(np.argmax(r), r.shape)
    def sub(m, p, c):
        d = m - 2 * c + p
        return 0.0 if abs(d) < 1e-9 else 0.5 * (m - p) / d
    fx = x + sub(r[y, (x - 1) % W], r[y, (x + 1) % W], r[y, x]); fy = y + sub(r[(y - 1) % H, x], r[(y + 1) % H, x], r[y, x])
    return (fx - W if fx > W / 2 else fx), (fy - H if fy > H / 2 else fy)


def fps_of(path):
    s = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True).stdout.strip().split("\n")[0]
    n, _, d = s.partition("/"); return float(n) / float(d or 1)


def _cache(path):
    p = Path(path); st = p.stat()
    root = next((q / "work" for q in p.parents if (q / "work").is_dir()), p.parent)
    return root / "shake" / f"{p.stem}_{hashlib.md5(f'{p}{st.st_size}{st.st_mtime}'.encode()).hexdigest()[:8]}.npy"


def scan(path):
    """Rung từng khung (px/khung ở cỡ 1920). Ảnh tĩnh → mảng 0. Cache theo file."""
    if Path(path).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"): return 30.0, np.zeros(1)
    c = _cache(path); fps = fps_of(path)
    if c.exists(): return fps, np.load(c)
    win = np.outer(np.hanning(H), np.hanning(W)).astype(np.float32); prev, mv = None, []
    for f in _frames(path):
        if prev is not None: mv.append(_shift(f, prev, win))
        prev = f
    mv = np.array(mv or [(0, 0)], float) * (1920 / W)
    k = max(3, int(fps * 0.5) | 1); ker = np.ones(k) / k
    sm = np.stack([np.convolve(mv[:, i], ker, "same") for i in (0, 1)], 1)
    jit = np.hypot(*(mv - sm).T)
    c.parent.mkdir(parents=True, exist_ok=True); np.save(c, jit); return fps, jit


def window(path, a, b):
    """(rung TB, đỉnh) trong [a,b] giây nguồn."""
    fps, j = scan(path)
    if len(j) <= 1: return 0.0, 0.0
    s = j[int(a * fps):max(int(b * fps), int(a * fps) + 1)]
    return (float(s.mean()), float(s.max())) if len(s) else (float(j.mean()), float(j.max()))


def best(path, dur, skip=0.5):
    """Giây bắt đầu khúc dài dur ổn định nhất (bỏ skip giây đầu: lúc bấm máy hay rung)."""
    fps, j = scan(path)
    n = max(1, int(dur * fps)); s0 = int(skip * fps)
    if len(j) <= s0 + n: return 0.0
    c = np.convolve(j[s0:], np.ones(n) / n, "valid"); return (s0 + int(np.argmin(c))) / fps


def level(mean, peak):
    return "ỔN" if mean <= OK_MEAN and peak <= OK_PEAK else "RUNG NHẸ" if mean <= LIGHT else "RUNG NẶNG"


def stabilized(path, cache_dir=None):
    """File đã chống rung (deshake + phóng 6 % che viền đen), cache. Dùng cho cảnh người nói rung nhẹ (không bỏ được vì đang nói)."""
    p = Path(path); st = p.stat()
    out = Path(cache_dir or _cache(path).parent.parent / "stab") / f"{p.stem}_{hashlib.md5(f'{p}{st.st_size}{st.st_mtime}'.encode()).hexdigest()[:8]}_stab.mp4"
    if out.exists(): return out
    out.parent.mkdir(parents=True, exist_ok=True); tmp = out.with_suffix(".part.mp4")
    sys.path.insert(0, str(Path(__file__).resolve().parent)); import e365 as E
    enc = (["-c:v", "h264_videotoolbox", "-b:v", "40M"] if E.HW == "vt" else ["-c:v", "h264_nvenc", "-preset", "p5", "-b:v", "40M"] if E.HW == "cuda"
           else ["-threads", E.X264_THREADS, "-c:v", "libx264", "-crf", "16", "-preset", "fast"])
    print(f"chống rung {p.name} …", flush=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-threads", "2", "-i", str(p), "-vf",
                    "deshake=rx=48:ry=48:edge=mirror,scale=iw*1.06:-2,crop=iw/1.06:ih/1.06", *enc, "-pix_fmt", "yuv420p",
                    "-c:a", "copy", str(tmp)], check=True)
    tmp.replace(out); return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: raise SystemExit(__doc__)
    if a[0] == "--stab": print(stabilized(a[1], Path(a[2]).parent if len(a) > 2 else None)); sys.exit()
    L = float(a[0])
    for p in a[1:]:
        fps, j = scan(p); s = best(p, L); m, x = window(p, s, s + L)
        print(f"{Path(p).name:28s} cả clip TB {j.mean():5.2f} [{level(j.mean(), j.max())}] | khúc {L:.1f}s ổn nhất từ {s:6.2f}s: TB {m:4.2f}, đỉnh {x:4.2f} [{level(m, x)}]")
