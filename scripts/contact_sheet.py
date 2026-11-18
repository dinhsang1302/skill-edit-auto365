#!/usr/bin/env python3
"""Contact sheet để soát nguồn / soát bản cuối (mỗi cảnh ≥ 1 frame).
Dùng:
  <python> scripts/contact_sheet.py <out.jpg> <video> [fps=1] [cột=6]        → lưới frame đều theo fps
  <python> scripts/contact_sheet.py <out.jpg> <file@giây> [<file@giây> ...]   → lấy đúng các mốc (so cảnh, so màu)
  (dùng @ thay : vì đường dẫn Windows có "C:"). Biến môi trường TW = bề ngang mỗi ô (mặc định 360)."""
import sys, os, subprocess, tempfile, glob, math
out, args = sys.argv[1], sys.argv[2:]; TW = os.environ.get("TW", "360")
if len(args) >= 1 and os.path.isfile(args[0]) and "@" not in args[0]:
    src = args[0]; fps = args[1] if len(args) > 1 else "1"; cols = int(args[2]) if len(args) > 2 else 6
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
    n = int(dur * float(fps)) + 1; rows = math.ceil(n / cols)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-threads", "4", "-i", src, "-vf", f"fps={fps},scale={TW}:-2,tile={cols}x{rows}",
                    "-frames:v", "1", "-update", "1", out], check=True)
else:
    d = tempfile.mkdtemp(); cols = int(os.environ.get("COLS", "6"))
    for i, a in enumerate(args):
        f, t = a.rsplit("@", 1)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-threads", "4", "-ss", t, "-i", f, "-frames:v", "1", "-vf", f"scale={TW}:-2",
                        os.path.join(d, f"{i:03d}.jpg")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(d, "%03d.jpg"), "-vf", f"tile={cols}x{math.ceil(len(args) / cols)}",
                    "-frames:v", "1", out], check=True)
    for x in glob.glob(os.path.join(d, "*")): os.remove(x)
    os.rmdir(d)
print(out)
