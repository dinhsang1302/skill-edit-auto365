# Hướng dẫn dùng Skill Edit Auto365 trên Claude Code (Mac + Windows)

Mục tiêu: bỏ clip gốc + ảnh vào thư mục, gõ yêu cầu cho Claude Code, nhận về file `.mp4` dựng xong theo style Auto365.

## Cách nhanh nhất: để Claude tự làm
Chỉ cần cài **Claude Code** (bước 1) và tải skill về đúng chỗ (lệnh `git clone` ở bước 2), rồi mở Claude Code ở bất kỳ đâu và gõ:
> Dùng Skill Edit Auto365 dựng clip từ file `<đường dẫn clip>` cho anh, khung 16:9.

Claude tự nhận skill → kiểm tra máy → tự chạy setup cài ffmpeg, Python, thư viện, model nhận giọng → chạy thử ra 1 clip mẫu →
tạo dự án, chép clip vào → dựng tới khi ra file MP4 và mở thư mục chỉ sẵn file. Chỉ dừng hỏi khi cần quyết định (tỉ lệ, kịch bản)
hoặc khi máy Mac chưa có Homebrew (cần mật khẩu máy — Claude đưa lệnh để anh tự chạy).
Các bước dưới đây là để tự làm tay hoặc khi cần xử lý lỗi.

## 0. Cần có
| Thứ | Mac | Windows |
|---|---|---|
| Máy | Apple Silicon (M1 trở lên), macOS 13+ | Windows 10/11 64-bit. **Khuyên có GPU NVIDIA** (RTX, driver ≥ 551) để giải mã/encode + nhận giọng nhanh; không có vẫn chạy bằng CPU (chậm hơn nhiều) |
| Dung lượng trống | ≥ 10 GB | ≥ 15 GB (thêm thư viện CUDA ~3 GB) |
| Claude Code | tài khoản Claude trả phí (Pro/Max) hoặc API key | như Mac; cần thêm **Git for Windows** (setup tự cài) |
| Trình cài gói | Homebrew (https://brew.sh) | winget (có sẵn trên Win 10/11; thiếu thì cài "App Installer" từ Microsoft Store) |
| ffmpeg | Homebrew | bản **Gyan full** (có NVDEC/NVENC, `scale_cuda`) — setup tự cài |
| Python 3.12 + thư viện | numpy, scipy, pillow, psutil, **mlx-whisper** | numpy, scipy, pillow, psutil, **faster-whisper** + cuBLAS/cuDNN |
| Font | Anton, Playfair Display, Inter, Be Vietnam Pro — có sẵn trong `assets/fonts/` (SIL OFL), không phải cài | như Mac |
| Lọc tạp âm giọng | DeepFilterNet 0.5.6 (MIT/Apache) — setup tự tải `bin/deep-filter`, kiểm SHA-256 | như Mac (`bin\deep-filter.exe`) |
| Nhạc nền | Setup tự tải 4 bài Mixkit (Mixkit Free License: online/quảng cáo online được, không TV/radio); muốn nhạc riêng thì bỏ vào `assets/music` | như Mac |
| SFX (tuỳ chọn) | Tự bỏ file có giấy phép vào `assets/sfx` | như Mac |
| Codex CLI (tuỳ chọn, **không bắt buộc**) | Có thì skill gọi vẽ thêm hình minh hoạ; không có thì skill tự dùng ảnh/clip có sẵn trong `insert/`, setup không cài | như Mac |

Tất cả ở cột trên `setup` tự cài, trừ Homebrew/winget và tài khoản Claude.

## 1. Cài Claude Code
**Mac** (Terminal):
```bash
curl -fsSL https://claude.ai/install.sh | bash      # hoặc: brew install node && npm install -g @anthropic-ai/claude-code
claude                                              # lần đầu: đăng nhập
```
**Windows** (PowerShell):
```powershell
winget install Git.Git                               # Claude Code trên Windows cần Git for Windows
irm https://claude.ai/install.ps1 | iex              # hoặc: winget install OpenJS.NodeJS.LTS; npm install -g @anthropic-ai/claude-code
claude                                               # lần đầu: đăng nhập
```
Lệnh cài có thể đổi theo thời gian — xem bản mới nhất ở docs.claude.com (mục Claude Code → Setup).

## 2. Cài skill + thư mục làm việc
**Mac:**
```bash
git clone https://github.com/dinhsang1302/skill-edit-auto365 ~/.claude/skills/edit-auto365
bash ~/.claude/skills/edit-auto365/setup.sh                     # tạo ~/Movies/Auto365Edit
```
**Windows** (PowerShell):
```powershell
git clone https://github.com/dinhsang1302/skill-edit-auto365 "$env:USERPROFILE\.claude\skills\edit-auto365"
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\skills\edit-auto365\setup.ps1"
# đổi chỗ đặt thư mục làm việc (vd. ổ D):  ... setup.ps1 -WS "D:\Auto365Edit"
```
Setup làm: cài ffmpeg + Python 3.12 (Windows thêm Git) → tạo thư mục làm việc (`scripts/`, `assets/`, `projects/`, `CLAUDE.md`)
→ tạo `.venv` và cài thư viện → chạy `scripts/check_env.py`. Cuối phải in **"KẾT QUẢ: đủ để dựng."**
Windows: sau khi setup cài mới ffmpeg/Python/Git, **mở cửa sổ PowerShell mới** rồi chạy lại setup một lần nữa nếu có dòng THIẾU.

Thư mục làm việc:
```
Auto365Edit/
  CLAUDE.md          # dặn Claude Code luôn dùng Skill Edit Auto365
  scripts/           # e365.py, build_template.py, transcribe.py, qc.py, contact_sheet.py, new_project.py, check_env.py, cpu_watch.py
  assets/fonts|music|sfx
  projects/<YYYY-MM-DD>_<Ten>/input  insert  work  output  brief.md
  .venv/
```
Dưới đây `<python>` = `.venv/bin/python` (Mac) hoặc `.venv\Scripts\python` (Windows).

## 3. Dựng một clip
1. Mở Claude Code tại thư mục làm việc:
   - Mac: `cd ~/Movies/Auto365Edit && claude`
   - Windows: `cd "$env:USERPROFILE\Videos\Auto365Edit"; claude`
2. Tạo dự án — gõ cho Claude *"tạo dự án mới tên F10_CX5"*, hoặc tự chạy `<python> scripts/new_project.py F10_CX5` (mở sẵn Finder/Explorer).
3. Kéo file vào thư mục dự án:
   - `input/` — clip gốc có người dẫn nói (16:9 hoặc dọc).
   - `insert/` — ảnh hộp có in thông số, ảnh sản phẩm, ảnh/clip vệt sáng (beam) thật, b-roll.
   - Điền `brief.md` (sản phẩm, kênh đăng, tỉ lệ khung, thông số có nguồn, có CTA hay không).
4. Gõ yêu cầu, ví dụ:
   > Dùng Skill Edit Auto365 dựng clip trong `projects/2026-11-18_F10_CX5`, khung 16:9, ~60 s, đăng Facebook.
   > Kịch bản: (dán kịch bản nếu có — chữ trên màn hình sẽ bám nguyên văn).

   Claude Code sẽ: soát nguồn (`qc.py`, contact sheet, lỗi video AI) → nhận giọng (`transcribe.py`), hỏi lại từ không chắc
   → lọc tạp âm giọng → dò và bỏ chỗ nói lặp/vấp (`stutter.py`), trám mối cắt bằng ảnh/b-roll có sẵn trong `insert/` (máy có Codex thì vẽ thêm minh hoạ được) → tự chọn nhạc
   → viết `work/build.py` từ mẫu → render **nháp** → tự soát bố cục + contact sheet → báo để xem.
5. Góp ý bằng lời ("chữ hiện chậm hơn", "cảnh 3 đổi ảnh beam khác", "bỏ end card") → Claude sửa script, render lại đúng đoạn đó.
6. Gõ "xuất bản giao" → file ở `projects/X/output/`, kèm báo cáo mạch dựng, thông số đã dùng + nguồn.

Tự chạy tay (không cần Claude):
```bash
# Mac
.venv/bin/python projects/X/work/build.py               # nháp
.venv/bin/python projects/X/work/build.py 03            # chỉ đoạn 03
FINAL=1 VER=2 .venv/bin/python projects/X/work/build.py # bản giao 4K v2 (nháp ở trên ra 360p để rà)
.venv/bin/python scripts/stutter.py --check projects/X/output/<file>.mp4   # soát còn lặp/nói lại không
.venv/bin/python scripts/qc.py projects/X/output/<file>.mp4
```
```powershell
# Windows
.venv\Scripts\python projects\X\work\build.py
$env:FINAL=1; $env:VER=2; .venv\Scripts\python projects\X\work\build.py; Remove-Item Env:FINAL, Env:VER
.venv\Scripts\python scripts\qc.py projects\X\output\<file>.mp4
```

## 4. Phần cứng & tốc độ
- `e365` tự chọn: Mac = videotoolbox + `scale_vt`; Windows NVIDIA = NVDEC + `scale_cuda`, nháp `h264_nvenc`; không GPU = CPU. Ép bằng `E365_HW=vt|cuda|none`.
- Trần CPU = 50% số luồng máy (`cpu_watch.py` tự tạm dừng ffmpeg khi vượt) để máy vẫn làm việc khác được.
- Nháp rà xuất **360p** (rất nhanh, file nhẹ); bản giao (clip chính) xuất **4K** HEVC phần cứng — clip ~75 s mất vài phút. Ép cỡ khác: `RES=1080`.
- Nhận giọng lần đầu tải model ~1,6 GB. Windows có GPU: faster-whisper CUDA; lỗi CUDA thì tự chạy CPU (chậm, có báo).
- Clip Sony XAVC (4K 4:2:2 hoặc rơi frame khi giải GPU) được tự chuyển giải mã CPU 1 luồng — chậm hơn, bình thường.

## 5. Lỗi hay gặp
| Hiện tượng | Cách xử lý |
|---|---|
| Windows: `ffmpeg`/`py`/`git` "not recognized" ngay sau setup | Mở cửa sổ PowerShell mới (PATH mới), chạy lại setup |
| Windows: script bị chặn "running scripts is disabled" | Chạy đúng lệnh có `-ExecutionPolicy Bypass` như trên |
| `check_env` báo THIẾU `h264_nvenc`/`hwaccel cuda` | Cập nhật driver NVIDIA; máy không có NVIDIA thì vẫn dựng được bằng CPU (`E365_HW=none`) |
| `faster-whisper: GPU lỗi … → chạy CPU` | Thiếu cuBLAS/cuDNN: `.venv\Scripts\python -m pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"` |
| Chữ tiếng Việt trong console bị lỗi | Setup đã đặt `PYTHONUTF8=1`; mở PowerShell mới. Dùng Windows Terminal |
| Mac: `mlx_whisper` không cài được | Máy Mac Intel không chạy mlx → cần Apple Silicon |
| Không có lệnh `claude` | Cài lại bước 1, mở cửa sổ terminal mới |
| Không có nhạc nền | Bỏ file nhạc có giấy phép vào `assets/music` rồi nói Claude dùng file đó |

## 6. Luật cần nhớ khi giao việc
- Không đưa thông số không có nguồn; ảnh AI chỉ minh hoạ, không làm bằng chứng (hộp, beam, trước/sau phải là ảnh thật).
- Nhiệt độ màu (3000K/4300K…) chỉ ghi khi đã xác nhận ảnh nào là màu nào.
- Clip TikTok mặc định không end card/CTA.
