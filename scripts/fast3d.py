#!/usr/bin/env python3
"""Tăng tốc dựng minh hoạ 3D (anh chốt 20/11/2026: dùng RTX).
1) GPU (CuPy, nếu có card NVIDIA + `pip install cupy-cuda12x[ctk]`): over() trộn lớp, blur() làm mờ — 2 bước chiếm ~75 % thời gian khung 4K.
   Không có CuPy/GPU → tự rơi về CPU (float32), kết quả như nhau.
2) encode_parallel(): chia khung cho nhiều tiến trình (số tiến trình = e365.auto_par, theo trần % CPU máy), mỗi tiến trình ghi 1 khúc,
   rồi nối khúc bằng ffmpeg concat (không nén lại) → nhanh gấp ~số tiến trình.
Dùng trong thư viện cảnh: `import fast3d as FX; over = FX.over; FX.patch_cv2_blur()`; render: `FX.encode_parallel(out, n, "scenes3d_c", "f_side13")`."""
import os, sys, subprocess, tempfile
from pathlib import Path
import numpy as np, cv2

try:
    import cupy as cp
    from cupyx.scipy import ndimage as cnd
    cp.zeros(1).sum(); GPU = os.environ.get("E365_GPU", "1") != "0"
except Exception:
    cp = None; GPU = False

def over(bg, col, a):
    """Phủ màu col (tuple hoặc ảnh HxWx3) với alpha a (HxW) — GPU nếu có. Trả float32 numpy."""
    if GPU:
        g = cp.asarray(bg, cp.float32); A = cp.clip(cp.asarray(a, cp.float32), 0, 1)[..., None]
        c = cp.asarray(np.asarray(col, np.float32))
        g *= (1 - A); g += c * A; return cp.asnumpy(g)
    bg = np.asarray(bg, np.float32); a = np.clip(np.asarray(a, np.float32), 0, 1)[..., None]
    return bg * (1 - a) + np.asarray(col, np.float32) * a

_cv_blur = cv2.GaussianBlur
def blur(img, ksize, sigma, *args, **kw):
    """Thay cv2.GaussianBlur((0,0), sigma) bằng bản GPU khi ảnh lớn và sigma ≥ 3; còn lại dùng OpenCV."""
    if GPU and ksize == (0, 0) and sigma >= 3 and img.size >= 1_000_000 and img.dtype in (np.float32, np.float64):
        x = cp.asarray(img, cp.float32); s = (sigma, sigma) + ((0,) if x.ndim == 3 else ())
        return cp.asnumpy(cnd.gaussian_filter(x, s, mode="nearest", truncate=3.0))
    return _cv_blur(img, ksize, sigma, *args, **kw)

def patch_cv2_blur():
    """Cho mọi cv2.GaussianBlur trong tiến trình đi qua blur() (GPU khi đáng)."""
    cv2.GaussianBlur = blur

def _worker(args):
    mod, fn, a, b, fps, W, H, out, crf, root = args
    sys.path.insert(0, root); M = __import__(mod); f = getattr(M, fn)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                          "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p", "-threads", "2", out], stdin=subprocess.PIPE)
    for i in range(a, b):
        fr = f(i / fps)
        if fr.dtype != np.uint8: fr = np.clip(fr, 0, 255).astype(np.uint8)
        p.stdin.write(np.ascontiguousarray(fr).tobytes())
    p.stdin.close(); p.wait(); return p.returncode

def encode_parallel(out, n, module, func, fps=25, W=1920, H=1080, crf=12, procs=None, root=None):
    """Render n khung của module.func(t)->RGB uint8 HxWx3 bằng nhiều tiến trình rồi nối (copy, không nén lại)."""
    import concurrent.futures as CF
    if procs is None:
        try:
            sys.path.insert(0, str(Path(__file__).parent)); import e365; procs = e365.auto_par(per_job=4)
        except Exception: procs = max(1, (os.cpu_count() or 4) // 5)
    procs = max(1, min(procs, n // 12 or 1)); root = root or os.getcwd()
    td = Path(tempfile.mkdtemp(prefix="fx3d_")); step = -(-n // procs)
    jobs = [(module, func, a, min(n, a + step), fps, W, H, str(td / f"p{k:02d}.mp4"), crf, root) for k, a in enumerate(range(0, n, step))]
    with CF.ProcessPoolExecutor(len(jobs)) as ex:
        if any(ex.map(_worker, jobs)): raise SystemExit(f"render lỗi {out}")
    lst = td / "list.txt"; lst.write_text("".join(f"file '{j[7]}'\n" for j in jobs), encoding="utf-8")
    tmp = Path(str(out) + ".part.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(tmp)], check=True)
    os.replace(tmp, out); print("OK", out, n, "khung,", len(jobs), "tiến trình,", "GPU" if GPU else "CPU", flush=True)

def encode_auto(out, n, frame, fps=25, W=1920, H=1080, crf=12):
    """Thay encode() tuần tự: hàm khung cấp module → tự render song song nhiều tiến trình (encode_parallel);
    lambda/hàm lồng → tuần tự như cũ. Module "__main__" → dùng tên file script để tiến trình con import lại."""
    mod, name = getattr(frame, "__module__", None), getattr(frame, "__qualname__", "")
    if mod == "__main__": mod = Path(sys.modules["__main__"].__file__).stem; root = str(Path(sys.modules["__main__"].__file__).resolve().parent)
    else: root = str(Path(sys.modules[mod].__file__).resolve().parent) if mod in sys.modules and getattr(sys.modules[mod], "__file__", None) else os.getcwd()
    if mod and name and "<" not in name and "." not in name and n >= 24 and os.environ.get("FX_SERIAL") != "1":
        return encode_parallel(out, n, mod, name, fps, W, H, crf, root=root)
    tmp = Path(str(out) + ".part.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                          "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p", "-threads", "3", str(tmp)], stdin=subprocess.PIPE)
    for i in range(n):
        fr = frame(i / fps); p.stdin.write(np.ascontiguousarray(np.clip(fr, 0, 255).astype(np.uint8) if fr.dtype != np.uint8 else fr).tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise SystemExit(f"ffmpeg lỗi {out}")
    os.replace(tmp, out); print("OK", out, n, "khung (tuần tự)", flush=True)
