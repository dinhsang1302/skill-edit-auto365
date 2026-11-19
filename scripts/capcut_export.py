#!/usr/bin/env python3
"""Đưa bản dựng (đã duyệt ở nháp 720p) vào project CapCut thay vì xuất file ghép (anh chốt 18/11/2026).

Track (mỗi thứ một track để người dùng tự sửa trong CapCut):
  V1 "MC"        clip người dẫn (nguồn gốc / bản đã chống rung) theo từng khúc giữ lại, TẮT TIẾNG
  V2 "CHÈN"      nguồn chèn: b-roll, ảnh, clip trám mối cắt (nguồn gốc, zoom = keyframe); cảnh "card" (khung bo góc + chip) = clip đã vẽ sẵn
  V3+ "CHỮ"      chữ animation Claude tự vẽ, xuất MOV ProRes 4444 nền trong suốt (không dùng text CapCut, không phụ đề)
  A1 "VOICE"     giọng đã lọc tạp âm, TÁCH THEO TỪNG KHÚC GIỮ LẠI (anh chốt 19/11/2026): mỗi khúc là 1 clip trỏ vào file giọng
                 ĐẦY ĐỦ của nguồn (đã lọc + nâng mức) với điểm vào/ra = mốc keep → kéo dài được cùng clip MC trong CapCut
  A2 "NHẠC"      nhạc nền đã duck theo giọng · A3 "SFX" (nếu có)
Không tự thêm chuyển cảnh / hiệu ứng / filter CapCut (luật xưởng: người dựng tự thêm). Màu grade của nháp không mang sang.

Gọi từ build: CAPCUT="<tên project>" <python> projects/X/work/build.py
  Project phải có sẵn (tạo project trống trong CapCut, đặt tên, rồi TẮT CapCut). Project đã có nội dung → từ chối,
  trừ khi CAPCUT_CLEAR=1 (xoá timeline cũ; bản cũ được sao lưu trong .mcp_backups).
Thư viện CapCut MCP: biến CAPCUT_MCP=<…/src> hoặc tự tìm ~/capcut-mcp-macos/src, ~/capcut-mcp-windows/src.
"""
import os, subprocess, sys
from pathlib import Path
from PIL import Image

if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")


def _mcp():
    for c in [os.environ.get("CAPCUT_MCP"), Path.home() / "capcut-mcp-macos/src", Path.home() / "capcut-mcp-windows/src"]:
        if c and (Path(c) / "capcut_mcp").is_dir():
            sys.path.insert(0, str(c))
            from capcut_mcp import edits, ir
            from capcut_mcp.draft import Draft
            return edits, ir, Draft
    raise SystemExit("Chưa có CapCut MCP (~/capcut-mcp-macos hoặc ~/capcut-mcp-windows) — cài theo README rồi chạy lại, "
                     "hoặc đặt CAPCUT_MCP=<thư mục src>.")


def alpha_mov(path, W, H, fps, dur, draw):
    """Ghi MOV ProRes 4444 có alpha; draw(canvas RGBA, t) vẽ lên khung trong suốt."""
    path = Path(path); tmp = path.with_suffix(".part.mov"); path.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                          "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-threads", "2", str(tmp)], stdin=subprocess.PIPE)
    for i in range(max(1, round(dur * fps))):
        c = Image.new("RGBA", (W, H)); draw(c, i / fps); p.stdin.write(c.tobytes())
    p.stdin.close()
    if p.wait(): raise SystemExit(f"Lỗi ghi {path}")
    tmp.replace(path); return path


def _fill_scale(src_wh, W, H):
    """CapCut scale 1 = vừa khít canvas (có thể hở 2 bên). Nhân hệ số này để phủ kín như frame_from."""
    w, h = src_wh; fit = min(W / w, H / h); fill = max(W / w, H / h); return fill / fit


def _pos(z, c, k):
    """Tâm khung c=(cx,cy) ở zoom z (đã nhân hệ số phủ k) → position CapCut (−1..1 theo nửa canvas), kẹp không lộ viền."""
    zz = z * k; lim = max(zz - 1, 0)
    x = max(-lim, min(lim, (0.5 - c[0]) * 2 * zz)); y = max(-lim, min(lim, (c[1] - 0.5) * 2 * zz))
    return x, y


def export(project, W, H, fps, clips, texts, voice, music=None, sfx=None, clear=False):
    """clips: [dict(layer="MC"|"CHÈN", path, start, dur, ss, z=(z0,z1), c=(cx,cy), wh=(w,h), mute=True)] theo giây timeline.
    texts: [dict(path=mov, start, dur)]. voice: [dict(path, start, dur, ss)] theo từng khúc (hoặc 1 wav dài bằng timeline — kiểu cũ).
    music/sfx: wav dài bằng timeline."""
    edits, ir, Draft = _mcp()
    d = Draft.open(project); data = d.data
    if any(t.get("segments") for t in data["tracks"]):
        if not clear: raise SystemExit(f"Project CapCut '{project}' đã có nội dung — tạo project trống mới, hoặc chạy lại với CAPCUT_CLEAR=1 (bản cũ được sao lưu).")
        data["tracks"] = []
    data["canvas_config"] = dict(data.get("canvas_config") or {}, width=W, height=H, ratio="original")
    data["fps"] = float(fps)
    def track(kind, name):                                   # track mới, có tên để người dùng nhận ra
        data["tracks"].append({"attribute": 0, "flag": 0, "id": edits.guid(), "is_default_name": False, "name": name,
                               "segments": [], "type": kind})
        return len(data["tracks"]) - 1
    TR = {"MC": track("video", "MC"), "CHÈN": track("video", "CHÈN")}   # MC dưới, CHÈN đè lên
    for c in clips:
        r = edits.add_clip(data, str(c["path"]), start=c["start"], duration=c["dur"], source_start=c.get("ss", 0.0),
                           track_index=TR[c["layer"]], volume=0.0 if c.get("mute", True) else 1.0)
        z0, z1 = c.get("z", (1, 1)); k = _fill_scale(c["wh"], W, H); cc = c.get("c", (.5, .5))
        x, y = _pos(z0, cc, k)
        edits.update_clip(data, r["clip_id"], scale=z0 * k, position={"x": x, "y": y})
        if abs(z1 - z0) > 1e-3:                              # zoom chậm = keyframe tuyến tính (sửa được trong CapCut)
            x1, y1 = _pos(z1, cc, k); T = c["dur"]
            for prop, a, b in (("KFTypeScaleX", z0 * k, z1 * k), ("KFTypeScaleY", z0 * k, z1 * k),
                               ("KFTypePositionX", x, x1), ("KFTypePositionY", y, y1)):
                if abs(b - a) > 1e-4: edits.set_keyframes(data, r["clip_id"], prop, [{"time": 0, "value": a}, {"time": T, "value": b}])
    lanes = []                                               # chữ: mỗi track không có 2 đoạn chồng thời gian
    for t in sorted(texts, key=lambda x: x["start"]):
        k = next((i for i, (end, _) in enumerate(lanes) if end <= t["start"] + 1e-3), None)
        if k is None: lanes.append((0, track("video", f"CHỮ {len(lanes) + 1}"))); k = len(lanes) - 1
        lanes[k] = (t["start"] + t["dur"], lanes[k][1])
        r = edits.add_clip(data, str(t["path"]), start=t["start"], duration=t["dur"], track_index=lanes[k][1], volume=0.0)
        x0, y0, x1, y1 = t["box"]; bw, bh = x1 - x0, y1 - y0     # CapCut scale 1 = vừa khít canvas → quy về đúng cỡ pixel
        edits.update_clip(data, r["clip_id"], scale=1 / min(W / bw, H / bh),
                          position={"x": ((x0 + x1) / 2 - W / 2) / (W / 2), "y": (H / 2 - (y0 + y1) / 2) / (H / 2)})
    na = 0
    if isinstance(voice, (list, tuple)):                     # giọng theo từng khúc, nguồn đầy đủ → kéo dài được
        tv = track("audio", "VOICE"); na += 1
        for v in voice:
            edits.add_clip(data, str(v["path"]), start=v["start"], duration=v["dur"], source_start=v.get("ss", 0.0), track_index=tv)
        voice = None
    for f, name in ((voice, "VOICE"), (music, "NHẠC"), (sfx, "SFX")):
        if f:
            edits.add_clip(data, str(f), start=0, track_index=track("audio", name)); na += 1
    if clear:                                                # xoá vật liệu mồ côi của timeline cũ (không để phình project)
        used = {x for t in data["tracks"] for g in t["segments"] for x in [g.get("material_id")] + list(g.get("extra_material_refs") or [])}
        for k, v in data["materials"].items():
            if isinstance(v, list) and v and all(isinstance(m, dict) and "id" in m for m in v):
                data["materials"][k] = [m for m in v if m["id"] in used]
    res = d.save()
    print(f"CapCut '{project}': {len(clips)} clip hình · {len(texts)} chữ trên {len(lanes)} track · {na} track tiếng → {res['saved']}")
    return res
