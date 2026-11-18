#!/usr/bin/env python3
"""Kiểm tra môi trường dựng Skill Edit Auto365 (Mac hoặc Windows). Chạy từ thư mục làm việc:  <python> scripts/check_env.py
In OK/THIẾU cho: ffmpeg + filter + GPU, thư viện Python, nhận giọng, font, assets, script. Thoát mã 1 nếu còn THIẾU."""
import os, sys, shutil, subprocess, importlib
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]; os.chdir(ROOT); sys.path.insert(0, str(ROOT / "scripts"))
FAIL = []
def ok(m): print("  OK    " + m)
def bad(m): print("  THIẾU " + m); FAIL.append(m)
def opt(m): print("  (tuỳ) " + m)
R = lambda c: subprocess.run(c, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
WIN, MAC = sys.platform.startswith("win"), sys.platform == "darwin"
print(f"== Nền tảng: {'Windows' if WIN else 'macOS' if MAC else sys.platform}, {os.cpu_count()} luồng CPU → trần job 50% = {os.cpu_count() * 50}% (thang ps)")
print("== ffmpeg")
if not shutil.which("ffmpeg"): bad("ffmpeg (Mac: brew install ffmpeg · Windows: winget install Gyan.FFmpeg)"); ff = ""
else:
    ok(R(["ffmpeg", "-version"]).splitlines()[0][:60]); ff = R(["ffmpeg", "-hide_banner", "-filters"])
    for x in ["overlay", "eq", "loudnorm", "sidechaincompress", "silencedetect", "xfade", "tile", "colorbalance"]:
        (ok if f" {x} " in ff else bad)(f"filter {x}")
    enc = R(["ffmpeg", "-hide_banner", "-encoders"]); acc = R(["ffmpeg", "-hide_banner", "-hwaccels"])
    (ok if "libx264" in enc else bad)("encoder libx264 (bản giao)")
    if MAC:
        (ok if "videotoolbox" in acc else bad)("hwaccel videotoolbox"); (ok if " scale_vt " in ff else bad)("filter scale_vt")
        (ok if "h264_videotoolbox" in enc else bad)("encoder h264_videotoolbox")
    else:
        (ok if shutil.which("nvidia-smi") else bad)("driver NVIDIA (nvidia-smi)")
        if shutil.which("nvidia-smi"): ok("GPU: " + R(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"]).strip())
        (ok if "cuda" in acc else bad)("hwaccel cuda (NVDEC)")
        (ok if " scale_cuda " in ff else opt)("filter scale_cuda" + ("" if " scale_cuda " in ff else " không có → scale CPU, chậm hơn; dùng bản Gyan full"))
        (ok if "h264_nvenc" in enc else bad)("encoder h264_nvenc (nháp)")
    print("  (libass/subtitles không cần: phụ đề vẽ bằng Pillow)")
print("== Python", sys.version.split()[0], sys.executable)
for m, pipn in [("numpy", "numpy"), ("scipy", "scipy"), ("PIL", "pillow"), ("cv2", "opencv-python-headless")] + ([] if MAC else [("psutil", "psutil")]):
    try: importlib.import_module(m); ok(m)
    except ImportError: bad(f"{m} (pip install {pipn})")
if MAC:
    try: importlib.import_module("mlx_whisper"); ok("mlx_whisper (nhận giọng)")
    except ImportError: bad("mlx_whisper (pip install mlx-whisper)")
else:
    try: importlib.import_module("faster_whisper"); ok("faster_whisper (nhận giọng)")
    except ImportError: bad("faster_whisper (pip install faster-whisper)")
    try:
        import ctranslate2; n = ctranslate2.get_cuda_device_count(); (ok if n else opt)(f"ctranslate2 thấy {n} GPU CUDA" + ("" if n else " → nhận giọng chạy CPU (chậm)"))
    except Exception as e: opt(f"ctranslate2: {e}")
try: importlib.import_module("av"); opt("PyAV có (không dùng để render)")
except ImportError: opt("PyAV không có (không cần cho render)")
print("== Font")
import e365
for n in ["InterDisplay-ExtraBold.otf", "Inter-Bold.otf", "BeVietnamPro-Black.ttf", "BeVietnamPro-Bold.ttf",
          "Anton-Regular.ttf", "PlayfairDisplay-Italic.ttf"]:
    try: ok(f"{n} ({Path(e365.find_font(n)).parent})")
    except FileNotFoundError: bad(f"font {n} → chép vào assets/fonts/")
print("== GPU dựng: e365.HW =", e365.HW, "(vt = Mac, cuda = NVIDIA, none = CPU)")
print("== Lọc tạp âm giọng (DeepFilterNet)")
import denoise
(ok if denoise.binary() else bad)("deep-filter " + (denoise.binary() or "→ <python> scripts/denoise.py --install"))
(ok if shutil.which("codex") else opt)("codex CLI " + ("có — vẽ được hình minh hoạ" if shutil.which("codex") else "không có → bỏ qua, dùng tư liệu có sẵn (không bắt buộc)"))
print("== Assets / script")
mus = [p for p in (ROOT / "assets/music").rglob("*") if p.suffix.lower() in (".mp3", ".wav")]
(ok if mus else bad)(f"assets/music ({len(mus)} file)" + ("" if mus else " → <python> scripts/music.py --install"))
sfx = [p for p in (ROOT / "assets/sfx").rglob("*") if p.suffix.lower() in (".mp3", ".wav")] if (ROOT / "assets/sfx").exists() else []
(ok if sfx else opt)(f"assets/sfx ({len(sfx)} file)" + ("" if sfx else " — trống: SFX phải báo là tự tổng hợp"))
for s in ["scripts/e365.py", "scripts/build_template.py", "scripts/cpu_watch.py", "scripts/transcribe.py", "scripts/words_to_caps.py",
          "scripts/contact_sheet.py", "scripts/qc.py", "scripts/new_project.py", "scripts/denoise.py", "scripts/stutter.py", "scripts/music.py"]:
    (ok if (ROOT / s).exists() else bad)(s)
r = subprocess.run([sys.executable, "scripts/e365.py", "--selftest"], capture_output=True, text=True, encoding="utf-8", errors="replace")
(ok if r.returncode == 0 and "OK" in r.stdout else bad)("e365 selftest" + ("" if r.returncode == 0 else " → " + r.stderr[-300:]))
print("KẾT QUẢ: đủ để dựng." if not FAIL else f"KẾT QUẢ: còn thiếu {len(FAIL)} mục (xem dòng THIẾU).")
sys.exit(1 if FAIL else 0)
