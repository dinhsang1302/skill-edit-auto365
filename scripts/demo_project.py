#!/usr/bin/env python3
"""Chạy thử trọn quy trình ra 1 clip trên dự án mẫu tự sinh (không cần file thật): nguồn → soát → nhận giọng → build → tự kiểm.
Dùng (từ thư mục làm việc): <python> scripts/demo_project.py      (~1–3 phút; lần đầu thêm thời gian tải model nhận giọng ~1,6 GB)
Xong ghi file .e365_ready (kèm phiên bản skill) để lần sau khỏi chạy lại. Xoá được: projects/_demo.
Giọng mẫu tạo tại chỗ: Mac `say` (giọng Linh nếu có), Windows System.Speech; không có thì dùng tiếng sine (bỏ bước nhận giọng)."""
import sys, os, shutil, subprocess, time, json
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]; os.chdir(ROOT); PY = sys.executable
P = ROOT / "projects/_demo"; shutil.rmtree(P, ignore_errors=True)
for s in ["input", "insert", "output", "work"]: (P / s).mkdir(parents=True, exist_ok=True)
def step(t): print(f"\n== {t}", flush=True)
def run(*c): subprocess.run([str(x) for x in c], check=True)
t0 = time.time()

step("1. Tạo nguồn mẫu (hình testsrc2 1920x1080 30 fps 6 s + giọng đọc)")
vo = P / "work/vo.wav"; text = "Đây là clip chạy thử của Skill Edit Auto365. Phụ đề và chữ động đang hoạt động."
try:
    if sys.platform == "darwin":
        voices = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
        aiff = P / "work/vo.aiff"
        run("say", *(["-v", "Linh"] if "Linh" in voices else []), "-o", aiff, text); run("ffmpeg", "-v", "error", "-y", "-i", aiff, vo)
    elif sys.platform.startswith("win"):
        ps = (f"Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.SetOutputToWaveFile('{vo}'); $s.Speak('{text}'); $s.Dispose()")
        run("powershell", "-NoProfile", "-Command", ps)
    if not vo.exists(): raise RuntimeError("không tạo được giọng")
    has_voice = True
except Exception as e:
    print("  (không tạo được giọng đọc:", e, "→ dùng tiếng sine, bỏ bước nhận giọng)")
    run("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=6", vo); has_voice = False
run("ffmpeg", "-v", "error", "-y", "-threads", "4", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=30:d=6", "-i", vo,
    "-filter_complex", "[1:a]aresample=48000,apad[a]", "-map", "0:v", "-map", "[a]", "-t", "6", "-c:v", "libx264", "-preset", "veryfast",
    "-threads", "2", "-pix_fmt", "yuv420p", "-c:a", "aac", P / "input/demo.mp4")

step("2. Soát nguồn (thông số, khoảng lặng, LUFS, contact sheet)")
run(PY, "scripts/qc.py", P / "input/demo.mp4"); run(PY, "scripts/contact_sheet.py", P / "work/sheet_src.jpg", P / "input/demo.mp4", 1, 6)

if has_voice:
    step("3. Nhận giọng + gợi ý phụ đề (lần đầu tải model)")
    run(PY, "scripts/transcribe.py", P / "input/demo.mp4", P / "work/words.json"); run(PY, "scripts/words_to_caps.py", P / "work/words.json")

step("4. Build nháp theo mẫu scripts/build_template.py (encode GPU nếu có)")
shutil.copy("scripts/build_template.py", P / "work/build.py")
os.environ["SHAKE_CHECK"] = "0"                            # hình testsrc2 tổng hợp chuyển động liên tục → không soát rung
run(PY, P / "work/build.py")

step("5. Tự kiểm bản ra")
out = next((P / "output").glob("*.mp4")); run(PY, "scripts/qc.py", out); run(PY, "scripts/contact_sheet.py", P / "output/contact.jpg", out, 2, 6)
n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                    "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
if not n.isdigit() or int(n) < 100: raise SystemExit(f"LỖI: bản ra chỉ có {n} khung")
ver = (Path(__file__).resolve().parents[1] / ".skill_version")
(ROOT / ".e365_ready").write_text(json.dumps({"version": ver.read_text().strip() if ver.exists() else "?", "time": time.ctime(),
                                               "out": str(out)}, ensure_ascii=False), encoding="utf-8")
print(f"\nXONG trong {time.time() - t0:.0f}s: {out} ({n} khung)\n  contact sheet: {P / 'output/contact.jpg'}\n  → máy SẴN SÀNG dựng clip thật.")
