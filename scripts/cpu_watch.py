#!/usr/bin/env python3
"""Canh trần CPU suốt job render (luật "Giới hạn tài nguyên máy" trong references/quy-trinh.md) — chạy trên Mac và Windows.
Mỗi 60 s cộng %CPU của MỌI ffmpeg + python (> 5%) trên máy, kể cả job dự án khác (thang kiểu `ps`: 100% = 1 luồng).
Trần = pct% × số luồng × 100 (Mac 10 nhân, 50% → 500; i7-14700K 28 luồng, 50% → 1400).
Vượt trần → tạm dừng mọi ffmpeg 15 s rồi cho chạy tiếp, ghi log. Tự thoát khi tiến trình job kết thúc.
Dùng: <python> scripts/cpu_watch.py <pid_job> <log> [pct=50]       (build tự bật qua e365.start_cpu_watch)
Cần psutil (Windows: có trong setup.ps1). Mac không có psutil → dùng `ps` + SIGSTOP/SIGCONT."""
import os, sys, time, signal, subprocess, datetime
JOB, LOG = int(sys.argv[1]), sys.argv[2]; PCT = float(sys.argv[3]) if len(sys.argv) > 3 else 50
NC = os.cpu_count() or 1; CAP = NC * PCT
try:
    import psutil
except ImportError:
    psutil = None

def alive(pid):
    if psutil: return psutil.pid_exists(pid)
    try: os.kill(pid, 0); return True
    except OSError: return False

def sample():
    """→ (tổng %CPU, list tiến trình ffmpeg)."""
    if psutil:
        ps = [p for p in psutil.process_iter(["name"]) if p.info["name"] and ("ffmpeg" in p.info["name"].lower() or "python" in p.info["name"].lower())]
        for p in ps:
            try: p.cpu_percent(None)
            except psutil.Error: pass
        time.sleep(2); tot = 0; ff = []
        for p in ps:
            try: c = p.cpu_percent(None)
            except psutil.Error: continue
            n = p.info["name"].lower()
            if "ffmpeg" in n: tot += c; ff.append(p)
            elif c > 5: tot += c
        return tot, ff
    out = subprocess.run(["ps", "-Ao", "pid=,pcpu=,comm="], capture_output=True, text=True).stdout
    tot = 0; ff = []
    for l in out.splitlines():
        pid, c, comm = l.split(None, 2); c = float(c)
        if "ffmpeg" in comm: tot += c; ff.append(int(pid))
        elif "python" in comm.lower() and c > 5: tot += c
    return tot, ff

def pause(ff, stop):
    for p in ff:
        try:
            if psutil: p.suspend() if stop else p.resume()
            else: os.kill(p, signal.SIGSTOP if stop else signal.SIGCONT)
        except Exception: pass

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f: f.write(f"{datetime.datetime.now():%H:%M:%S} {msg}\n")

while alive(JOB):
    tot, ff = sample()
    log(f"CPU={tot:.0f}% trần={CAP:.0f}% ffmpeg={len(ff)}")
    if tot > CAP:
        pause(ff, True); log("  vượt trần → tạm dừng ffmpeg 15 s"); time.sleep(15); pause(ff, False)
    time.sleep(58)
log("job xong, dừng canh")
