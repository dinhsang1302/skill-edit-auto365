---
name: edit-auto365
description: Skill Edit Auto365 — dựng clip video sản phẩm (ô tô, đèn, phim cách nhiệt, phụ kiện…) có người dẫn nói, ra file MP4 hoàn chỉnh theo style Auto365 — chữ động theo từng từ quanh người dẫn (Anton trắng + keyword đỏ viết hoa + từ nối Playfair nghiêng), grade tối, thẻ ảnh bay, khung kính chứa ảnh/thông số có chip nguồn, phụ đề tiếng Việt, nhạc duck, -14 LUFS. Tự kiểm tra máy, tự cài thứ còn thiếu (ffmpeg, Python, thư viện, model nhận giọng) rồi dựng tới khi ra clip. Dùng khi người dùng nói "Skill Edit Auto365", "edit auto365", "style Auto365", "dựng clip", "edit clip", "edit video", "làm clip review đèn/xe", đưa đường dẫn video (.mp4/.mov) và nhờ dựng/edit, hoặc gửi kịch bản kèm clip quay người dẫn. Chạy trên macOS (Apple Silicon) và Windows (khuyên GPU NVIDIA); khung 16:9 hoặc 9:16.
---

# Skill Edit Auto365

Style dựng mặc định của xưởng Edit365 cho clip sản phẩm ô tô (đèn, phim, phụ kiện). Chốt 17/10/2026.
**Nhiệm vụ của skill: từ yêu cầu của người dùng → máy sẵn sàng → clip MP4 xong, không bắt người dùng tự cài hay tự gõ lệnh.**
Trả lời người dùng bằng tiếng Việt, ngắn, kết luận trước.

`$SK` = thư mục skill này (thường `~/.claude/skills/edit-auto365`). `$WS` = thư mục làm việc (mặc định: Mac `~/Movies/Auto365Edit`,
Windows `%USERPROFILE%\Videos\Auto365Edit`; nếu người dùng đang mở Claude Code trong một thư mục có `scripts/e365.py` + `.venv` thì `$WS` là thư mục đó).
`<python>` = `$WS/.venv/bin/python` (Mac) hoặc `$WS/.venv/Scripts/python.exe` (Windows).

## Bước 0 — Tự kiểm tra máy và cài (làm TRƯỚC mọi việc dựng, mỗi phiên một lần)
Chạy lần lượt, chỉ báo người dùng 1 dòng ở mỗi mốc ("Đang kiểm tra máy…", "Đang cài ffmpeg + Python…", "Máy sẵn sàng"):

1. **Nhận nền tảng**: `uname -s` (Darwin = Mac; MINGW/MSYS/CYGWIN hoặc lệnh lỗi = Windows — Claude Code trên Windows chạy Bash qua Git Bash).
   Mac Intel (`uname -m` = x86_64) → báo không hỗ trợ nhận giọng mlx; vẫn dựng được nếu người dùng tự gửi lời thoại.
2. **Đã sẵn sàng chưa?** Đủ cả 3 thì sang Bước 1:
   - `$WS/.venv` có python, `$WS/scripts/e365.py` tồn tại;
   - `$WS/.skill_version` trùng `$SK/VERSION` (khác → skill vừa cập nhật → chạy lại setup để chép script mới, không mất dự án);
   - `<python> $WS/scripts/check_env.py` thoát mã 0 (in "KẾT QUẢ: đủ để dựng.").
3. **Chưa → chạy setup** (tự cài, idempotent, chạy lại an toàn; báo trước "sẽ cài ffmpeg, Python 3.12 và thư viện, ~5–10 phút" rồi làm luôn,
   không hỏi từng món — người dùng đã yêu cầu skill tự cài):
   - Mac: `bash "$SK/setup.sh" "$WS"` (timeout dài, 10 phút). Thiếu Homebrew → **không tự cài được** (cần mật khẩu máy): đưa người dùng lệnh
     `! /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` để họ tự chạy, xong chạy lại setup.
   - Windows: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$SK/setup.ps1" -WS "$WS"`. Sau khi winget cài mới ffmpeg/Python/Git,
     PATH của phiên hiện tại chưa có → chạy setup **lần 2** (setup tự nạp lại PATH); vẫn thiếu thì dùng đường dẫn đầy đủ
     (`%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe`, `py -3.12`) hoặc báo người dùng mở lại Claude Code.
4. **Sửa từng dòng THIẾU** trong `check_env.py` theo bảng "Lỗi hay gặp" ở `HUONG-DAN.md` (vd. thiếu cuBLAS/cuDNN → pip install; không có GPU NVIDIA →
   chấp nhận chạy CPU, đặt `E365_HW=none`, báo người dùng sẽ chậm hơn). Chạy lại `check_env.py` tới khi đạt. Lỗi lặp lại 2 lần cùng chỗ → dừng, báo
   người dùng nguyên văn dòng lỗi + việc họ cần làm, không lặp vô hạn.
5. **Chạy thử ra clip** nếu `$WS/.e365_ready` chưa có hoặc khác phiên bản: `cd "$WS" && <python> scripts/demo_project.py`
   (1–3 phút; lần đầu tải model nhận giọng ~1,6 GB — báo trước). Ra file MP4 + "máy SẴN SÀNG" là xong Bước 0.

## Bước 1 — Nhận việc
- Người dùng đưa file/thư mục video ở ngoài `$WS` → tạo dự án `<python> scripts/new_project.py <Ten> --no-open`, **chép** (không di chuyển) clip vào
  `input/`, ảnh/b-roll vào `insert/`. Tên dự án ngắn, không dấu.
- Thiếu thông tin quyết định (tỉ lệ 16:9 hay 9:16, kênh đăng, có kịch bản không) → hỏi gộp 1 lần; cái gì có mặc định thì tự chọn và nói ra
  (mặc định: tỉ lệ theo nguồn, fps theo nguồn, không end card cho TikTok).
- Điền `brief.md` theo những gì biết.

## Bước 2 — Dựng (đọc `references/` trước khi viết build)
Đọc: `references/style.md` (nhận diện style) → `references/quy-trinh.md` (quy trình bắt buộc, CPU, luật nội dung) → `references/loi-da-gap.md`.
1. **Soát nguồn**: `<python> scripts/qc.py <file>`, contact sheet 1 fps `<python> scripts/contact_sheet.py <out.jpg> <file> 1 6` rồi **xem ảnh**;
   tìm lỗi video AI (tay, chữ, logo méo) → cắt hình giữ tiếng, phủ insert. Ghi danh mục tư liệu vào `brief.md`.
2. **Transcript**: `<python> scripts/transcribe.py <file> <dự án>/work/words.json`, hiệu đính tay tên sản phẩm, W/K/lm, cos/pha
   (bảng lỗi nhận giọng trong `quy-trinh.md`); từ không chắc → hỏi người dùng. Gợi ý phụ đề: `scripts/words_to_caps.py`.
3. **Viết `work/build.py`** từ `scripts/build_template.py` (new_project đã chép sẵn): `SEGS` (keep / shots / caps / kin), `NAME`, `W,H,FPS`,
   `THEME="dark"`, `MUSIC` (chỉ file có giấy phép trong `assets/music`; không có thì không nhạc và nói rõ). Học cách dựng từ `examples/`.
   Mọi mốc cắt, chữ, vị trí, âm lượng nằm trong script; sửa = sửa script rồi chạy lại.
4. **Nháp**: `cd "$WS" && <python> projects/X/work/build.py` (encode GPU, nhanh). Soát bố cục tự động phải qua; contact sheet bản nháp → **xem ảnh**,
   sửa chữ đè mặt/sản phẩm/thông số. Bước dự kiến > 5 phút → báo trước.
5. **Bản giao**: `FINAL=1 VER=n` (Mac/Git Bash: `FINAL=1 VER=1 <python> …`), mỗi lần sửa tăng `VER`, không ghi đè bản cũ.
6. **Tự kiểm**: `<python> scripts/qc.py <bản giao>` (~-14 LUFS, TP ≤ -1,5, hình = tiếng), contact sheet bản cuối, đếm khung đủ.

## Bước 3 — Giao
- Mở thư mục chọn sẵn file: Mac `open -R <file>`, Windows `explorer.exe /select,"<file theo dạng C:\...>"`.
- Báo 3–5 dòng: mạch dựng, chỗ cắt vì lỗi, thông số đã dùng + nguồn, phần tạm (nhạc/CTA), từ cần soát.
- Người dùng góp ý → sửa `build.py`, render lại đúng đoạn (`build.py 03`), xuất `VER` mới.

## Luật không thương lượng
Không bịa thông số (chỉ lời đọc đã xác nhận / in trên hộp / fact sheet, kèm chip nguồn). Ảnh AI chỉ minh hoạ, không làm bằng chứng
(hộp, beam, trước/sau, xe khách phải là ảnh thật — thiếu thì xin). Không gắn nhiệt độ màu khi chưa xác nhận. Không nhạc/SFX không rõ giấy phép.
Trần CPU 50% máy, render từng đoạn tuần tự (`e365.start_cpu_watch`).

## Code
| File | Vai trò |
|---|---|
| `setup.sh` / `setup.ps1` | Cài + tạo `$WS` (Mac / Windows), idempotent |
| `scripts/check_env.py` | Kiểm tra máy, thoát mã 1 nếu còn THIẾU |
| `scripts/demo_project.py` | Chạy thử trọn quy trình ra 1 clip, ghi `.e365_ready` |
| `scripts/e365.py` | Thư viện: `VReader` (tự chọn videotoolbox / NVDEC / CPU), `Encoder`, `Word`/`layout_line` (chữ động, chống tràn), `cap_img` (phụ đề), `check_layout`, `rounded`/`with_shadow`/`cta`/`soft_bg`, `cut_voice`/`loudness`/`final_mix`/`mux`, `STYLES["dark"]` |
| `scripts/build_template.py` | Mẫu build 1 dự án: SEGS → render tuần tự có cache → âm thanh → bản giao |
| `scripts/transcribe.py`, `words_to_caps.py` | Nhận giọng tiếng Việt từng từ (Mac mlx-whisper / Windows faster-whisper CUDA), gợi ý phụ đề |
| `scripts/qc.py`, `contact_sheet.py` | Soát thông số/LUFS/khoảng lặng, contact sheet |
| `scripts/new_project.py`, `cpu_watch.py` | Tạo khung dự án, canh trần CPU |
| `examples/f10_10s_16x9_nen_toi.py` | Bản 10 s 16:9 nền tối — mẫu chữ động gọn nhất |
| `examples/mazda_full_16x9.py` + `textfx.py` | Clip 16:9 đầy đủ 20 đoạn: ảnh bảng căn đèn, split so sánh, chip nguồn, end card |

`examples/` là code job thật để học cách dựng (không chạy nguyên xi; đường dẫn từ biến `E365_ROOT` / `PRJ`).
