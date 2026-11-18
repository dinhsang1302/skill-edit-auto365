#!/usr/bin/env python3
"""Lọc tạp âm giọng nói bằng DeepFilterNet 0.5.6 (AI, offline, MIT/Apache — github.com/Rikorose/DeepFilterNet).
Lọc được cả tiếng người nói lẫn phía sau; ffmpeg afftdn chỉ trừ ồn đều (quạt, ù, xì).

Dùng (từ thư mục làm việc):
  <python> scripts/denoise.py --install                 tải đúng bản cho máy vào bin/ (kiểm SHA-256) — setup tự gọi
  <python> scripts/denoise.py <file> [out.wav]          lọc SIÊU MẠNH (mặc định) → <tên file>_denoise.wav cạnh file gốc
  <python> scripts/denoise.py <file> [out.wav] --soft   lọc VỪA cho giọng thu nhỏ/xa (nâng -20 LUFS trước, không gate)
Trong build: e365.voice_source(...) tự gọi và cache (DENOISE trong build_template.py).

Quy trình đã kiểm trên máy xưởng (chốt 01/11/2026):
  1. đổi 48 kHz → 2. deep-filter 1 lượt (-D, --pf --pf-beta 0.15) → 3. VÁ LỖ: DeepFilterNet đôi khi ra frame 10 ms bằng 0 tuyệt đối
  giữa chữ (nghe như tiếng tách) → lấp bằng tiếng gốc × gain nội suy → 4. gate nhẹ (agate) dập ồn trong khoảng nghỉ.
  KHÔNG chạy 2 lượt (cắt cụt đuôi chữ). Giọng nhỏ (-39 LUFS) lọc mạnh sẽ mất giọng → dùng --soft.
"""
import hashlib, os, platform, shutil, stat, subprocess, sys, tempfile, urllib.request
from pathlib import Path
import numpy as np

if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
VER = "0.5.6"
URL = f"https://github.com/Rikorose/DeepFilterNet/releases/download/v{VER}/"
ASSETS = {  # (hệ, kiến trúc) → (file phát hành, sha256 đã đo 18/11/2026)
    ("darwin", "arm64"): ("deep-filter-0.5.6-aarch64-apple-darwin", "4601e7f4e4c03e59a4c5b5000216ef3add3e808799cfccd95e14e83ea4611081"),
    ("darwin", "x86_64"): ("deep-filter-0.5.6-x86_64-apple-darwin", "d3be84003acb7c23e738ad7f70a158ec779a8d233a82e7fa3e717d112eb5b50f"),
    ("win32", "amd64"): ("deep-filter-0.5.6-x86_64-pc-windows-msvc.exe", "75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915"),
}
SR, F = 48000, 480                                         # khung 10 ms


def _key():
    m = platform.machine().lower()
    if sys.platform == "darwin" and m == "x86_64":         # Python chạy qua Rosetta trên máy M → vẫn dùng bản arm64
        try:
            if subprocess.run(["sysctl", "-n", "sysctl.proc_translated"], capture_output=True, text=True).stdout.strip() == "1": m = "arm64"
        except Exception: pass
    return ("win32" if sys.platform.startswith("win") else sys.platform, {"aarch64": "arm64", "x86_64": "x86_64" if sys.platform == "darwin" else "amd64"}.get(m, m))


def binary():
    """Đường dẫn deep-filter: biến môi trường DEEP_FILTER, bin/ của thư mục làm việc, hoặc PATH. Không có → None."""
    cands = [os.environ.get("DEEP_FILTER"), ROOT / "bin" / ("deep-filter.exe" if sys.platform.startswith("win") else "deep-filter"),
             shutil.which("deep-filter")]
    return next((str(c) for c in cands if c and Path(c).is_file()), None)


def install():
    if binary(): print("deep-filter đã có:", binary()); return binary()
    k = _key()
    if k not in ASSETS: raise SystemExit(f"Chưa có bản DeepFilterNet cho {k} — lọc tạp âm sẽ bỏ qua (dùng afftdn).")
    name, sha = ASSETS[k]; out = ROOT / "bin" / ("deep-filter.exe" if k[0] == "win32" else "deep-filter")
    out.parent.mkdir(exist_ok=True); tmp = out.with_suffix(".part")
    print(f"Tải DeepFilterNet {VER} ({name}, ~27 MB)…", flush=True)
    with urllib.request.urlopen(URL + name, timeout=120) as r, open(tmp, "wb") as f: shutil.copyfileobj(r, f)
    got = hashlib.sha256(tmp.read_bytes()).hexdigest()
    if got != sha: tmp.unlink(); raise SystemExit(f"SHA-256 sai ({got}) — không cài. Thử lại hoặc tải tay từ {URL}{name}")
    tmp.replace(out); out.chmod(out.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("OK:", out); return str(out)


def _load(f, ch):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-ar", str(SR), "-ac", str(ch), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(r, np.float32).reshape(-1, ch).copy()


def patch_holes(orig, dfn, out):
    """Lấp frame 10 ms = 0 tuyệt đối giữa chữ bằng tín hiệu gốc × gain (dB) nội suy từ 2 frame lành hai bên. Trả số frame đã vá."""
    d = _load(dfn, 2); o = _load(orig, 2)[:len(d)]
    if len(o) < len(d): o = np.vstack([o, np.zeros((len(d) - len(o), 2), np.float32)])
    mo, md = o.mean(1), d.mean(1); L = min(len(mo), SR * 4)
    if L > 9600:                                           # căn lệch ±50 ms bằng tương quan
        best = max(range(-2400, 2401, 8), key=lambda k: np.dot(md[2400:L - 2400], mo[2400 + k:L - 2400 + k])); o = np.roll(o, -best, 0)
    nF = len(d) // F
    if nF < 3: shutil.copy(dfn, out); return 0
    rms = lambda a: np.sqrt((a[:nF * F].reshape(nF, F, -1) ** 2).mean((1, 2))) + 1e-12
    rd, ro = rms(d), rms(o)
    z = np.array([np.all(d[i * F:(i + 1) * F] == 0) for i in range(nF)])
    if z.all(): shutil.copy(dfn, out); return 0
    first, last = int(np.argmax(~z)), nF - 1 - int(np.argmax(~z[::-1]))
    g = np.full(nF, np.nan); g[~z] = 20 * np.log10(rd[~z] / ro[~z]); fix = 0
    for i in range(first, last + 1):
        if z[i]:
            a = i - 1
            while z[a]: a -= 1
            b = i + 1
            while z[b]: b += 1
            g[i] = g[a] + (g[b] - g[a]) * (i - a) / (b - a); fix += 1
    gl = 10 ** (np.interp(np.arange(nF * F), (np.arange(nF) + .5) * F, np.where(np.isnan(g), -120, g)) / 20)
    y = d.copy()
    for i in range(first, last + 1):
        if z[i]:
            s = slice(max(0, (i - 1) * F), min((i + 2) * F, nF * F)); n = s.stop - s.start
            w = np.ones(n); h = min(F // 2, n // 2); w[:h] = np.linspace(0, 1, h); w[n - h:] = np.linspace(1, 0, h)
            y[s] = y[s] * (1 - w[:, None]) + o[s] * gl[s][:, None] * w[:, None]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", "pcm_s16le", str(out)],
                   input=y.astype(np.float32).tobytes(), check=True)
    return fix


def _lufs(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    v = [l for l in r.stderr.splitlines() if l.strip().startswith("I:")]
    return float(v[-1].split()[1]) if v else -23.0


def denoise(src, out=None, soft=False, quiet=False):
    """Lọc giọng của file (video hoặc audio). Mặc định siêu mạnh; soft=True lọc vừa. Trả đường dẫn wav 48 kHz stereo."""
    src = Path(src); out = Path(out) if out else src.with_name(src.stem + "_denoise.wav")
    exe = binary() or install()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td); x = td / "x_48k.wav"
        pre = []
        if soft:                                           # giọng nhỏ: nâng về ~-20 LUFS trước để mạng không coi giọng là ồn
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ar", str(SR), "-ac", "2", str(td / "raw.wav")], check=True)
            pre = ["-af", f"volume={-20 - _lufs(td / 'raw.wav'):.2f}dB"]; srcx = td / "raw.wav"
        else: srcx = src
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(srcx), "-vn", *pre, "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s16le", str(x)], check=True)
        args = ["-a", "24", "--pf", "--pf-beta", "0.03"] if soft else ["--pf", "--pf-beta", "0.15"]
        (td / "o").mkdir()
        subprocess.run([exe, "-D", *args, "-o", str(td / "o"), str(x)], check=True, capture_output=quiet)
        dfn = td / "o" / x.name; fixed = td / "fixed.wav"
        n = patch_holes(x, dfn, fixed)
        af = "anull" if soft else "agate=threshold=0.012:ratio=3:range=0.2:attack=20:release=200"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(fixed), "-af", af, "-ar", str(SR), "-c:a", "pcm_s16le", str(out)], check=True)
    if not quiet: print(f"OK {out}  ({'vừa' if soft else 'siêu mạnh'}, vá {n} lỗ 10 ms)")
    return out


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if "--install" in sys.argv: install(); sys.exit()
    if not a: raise SystemExit(__doc__)
    denoise(a[0], a[1] if len(a) > 1 else None, soft="--soft" in sys.argv)
