#!/usr/bin/env python3
"""Soát nhanh 1 file video: thông số (độ phân giải, fps, thời lượng hình/tiếng), khoảng lặng > 0,4 s, độ lớn LUFS + true peak.
Dùng: <python> scripts/qc.py <video> [ngưỡng_lặng_dB=-35]
Bước 1 (soát nguồn) và bước 8 (tự kiểm bản giao: ~-14 LUFS, TP ≤ -1,5, |hình − tiếng| < 0,05 s)."""
import sys, json, re, subprocess
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
f = sys.argv[1]; noise = sys.argv[2] if len(sys.argv) > 2 else "-35"
R = lambda c: subprocess.run(c, capture_output=True, text=True, encoding="utf-8", errors="replace")
j = json.loads(R(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,pix_fmt,duration,sample_rate,channels",
                  "-of", "json", f]).stdout)
print(f"== {f}"); dur = {}
for s in j["streams"]:
    t = s["codec_type"]; dur[t] = float(s.get("duration", 0))
    print(f"  {t}: " + ", ".join(f"{k}={v}" for k, v in s.items() if k != "codec_type"))
if "video" in dur and "audio" in dur:
    d = abs(dur["video"] - dur["audio"]); print(f"  lệch hình−tiếng: {d:.3f}s" + ("  ⚠ > 0,05 s" if d > 0.05 else ""))
err = R(["ffmpeg", "-hide_banner", "-threads", "4", "-i", f, "-af", f"silencedetect=noise={noise}dB:d=0.4", "-f", "null", "-"]).stderr
print(f"  -- khoảng lặng (> 0,4 s, {noise} dB):")
for m in re.finditer(r"silence_(start|end): ([\d.]+)(?: \| silence_duration: ([\d.]+))?", err):
    print(f"    {m.group(1)} {float(m.group(2)):.2f}" + (f"  (dài {float(m.group(3)):.2f}s)" if m.group(3) else ""))
err = R(["ffmpeg", "-hide_banner", "-threads", "4", "-i", f, "-af", "loudnorm=print_format=json", "-f", "null", "-"]).stderr
js = err[err.rfind("{"):]; L = json.loads(js[:js.index("}") + 1])
print(f"  -- độ lớn: {L['input_i']} LUFS, true peak {L['input_tp']} dBTP")
