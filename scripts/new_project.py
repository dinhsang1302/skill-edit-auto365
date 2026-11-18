#!/usr/bin/env python3
"""Tạo khung dự án mới: projects/<YYYY-MM-DD>_<Ten>/{input,insert,output,work} + brief.md mẫu + work/build.py (chép từ mẫu),
rồi mở thư mục (Finder / Explorer) để người dùng kéo file vào.
Dùng (từ thư mục làm việc): <python> scripts/new_project.py <Ten_Du_An> [YYYY-MM-DD] [--no-open]"""
import sys, os, shutil, subprocess, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
a = [x for x in sys.argv[1:] if not x.startswith("--")]
if not a: sys.exit("Dùng: scripts/new_project.py <Ten>")
d = a[1] if len(a) > 1 else datetime.date.today().isoformat()
P = ROOT / "projects" / f"{d}_{a[0]}"
for s in ["input", "insert", "output", "work"]: (P / s).mkdir(parents=True, exist_ok=True)
if not (P / "work/build.py").exists(): shutil.copy(ROOT / "scripts/build_template.py", P / "work/build.py")
if not (P / "brief.md").exists():
    (P / "brief.md").write_text(f"""# Brief — {a[0]}

- **Ngày tạo:** {datetime.date.today():%d/%m/%Y}
- **Sản phẩm / thương hiệu:**
- **Kênh đăng:** (Facebook / TikTok / YouTube / Reels…)
- **Tỉ lệ khung:** (16x9 / 9x16 / cả hai)
- **Độ dài mong muốn:**
- **Thông số có nguồn** (ghi kèm nguồn: lời đọc / in trên hộp / fact sheet):
  -
- **Nhạc / SFX chỉ định:** (file trong assets/ hoặc để người dựng chọn)
- **CTA / end card:** (có / không — clip TikTok thường không)
- **Ghi chú:** (điểm cần nhấn, cảnh bắt buộc có/không dùng)

## File đã bỏ vào
- `input/`  clip gốc (người dẫn, quay xe, quay beam…)
- `insert/` ảnh hộp, ảnh sản phẩm, ảnh/clip beam, b-roll
""", encoding="utf-8")
if "--no-open" not in sys.argv:
    if sys.platform.startswith("win"): os.startfile(P)
    elif sys.platform == "darwin": subprocess.run(["open", str(P)])
print(P)
