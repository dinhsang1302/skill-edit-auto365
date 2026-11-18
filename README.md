# Skill Edit Auto365

Gói style dựng clip mặc định của xưởng **Edit365** cho clip sản phẩm ô tô (Auto365): chữ động theo từng từ
(Anton trắng + keyword đỏ viết hoa + từ nối Playfair nghiêng), grade tối, thẻ ảnh bay, khung kính chứa thông số có chip nguồn,
phụ đề PNG, âm thanh chuẩn -14 LUFS.

## Cài nhanh
**Mac (Apple Silicon):**
```bash
git clone https://github.com/dinhsang1302/skill-edit-auto365 ~/.claude/skills/edit-auto365
bash ~/.claude/skills/edit-auto365/setup.sh
cd ~/Movies/Auto365Edit && claude
```
**Windows 10/11 (GPU NVIDIA khuyên dùng), PowerShell:**
```powershell
git clone https://github.com/dinhsang1302/skill-edit-auto365 "$env:USERPROFILE\.claude\skills\edit-auto365"
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\skills\edit-auto365\setup.ps1"
cd "$env:USERPROFILE\Videos\Auto365Edit"; claude
```
Thật ra chỉ cần cài Claude Code + `git clone` skill: gõ *"Dùng Skill Edit Auto365 dựng clip từ file …"*, Claude tự kiểm tra máy, tự cài phần thiếu, chạy thử rồi dựng tới khi ra clip. **Hướng dẫn đầy đủ: [`HUONG-DAN.md`](HUONG-DAN.md).**

## Nội dung
- `HUONG-DAN.md` — hướng dẫn cài và dựng clip bằng Claude Code
- `setup.sh` (Mac), `setup.ps1` (Windows) — cài đặt + tạo thư mục làm việc
- `SKILL.md` — điểm vào của skill
- `references/` — `style.md` (nhận diện), `quy-trinh.md` (quy trình, CPU, luật nội dung), `loi-da-gap.md`
- `scripts/` — `e365.py` (thư viện, tự chọn GPU Mac/Windows), `build_template.py`, `transcribe.py` (Mac mlx-whisper / Windows faster-whisper CUDA), `words_to_caps.py`, `qc.py`, `contact_sheet.py`, `new_project.py`, `check_env.py`, `cpu_watch.py`
- `examples/` — code job thật (16:9 nền tối, 16:9 đầy đủ 20 đoạn)
- `assets/fonts/` — Anton, Playfair Display, Inter, Be Vietnam Pro (SIL Open Font License 1.1, xem `OFL_*.txt`)
