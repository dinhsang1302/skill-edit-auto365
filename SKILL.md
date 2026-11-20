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
1b. **Che biển số (bắt buộc khi thấy biển)** (anh chốt 19/11/2026): mọi cảnh thấy biển số — xe chính và xe khác nếu đọc được, kể cả số sơn trên
   thân xe van — đều che **trước khi dựng**, trong đúng khoảng nguồn được dùng. Chép `scripts/bienso/*` vào `projects/X/work/plates/`, chạy tại đó:
   `sheet.py <n>…` (tìm clip có biển, **xem ảnh**) → `grid.py`/`fine.py` (đọc toạ độ 4 góc ở 1 khung mồi) → điền `tracks.py`
   (id, clip, giây mồi, 4 góc, khoảng giây nguồn, `plate`|`patch`, độ mềm cho xe nền mất nét) → `track.py <id>…` (bám LK flow + homography)
   → `render.py <n>…` → `insert_bs/`, `input_bs/` (cùng độ phân giải/fps/số khung, giữ tiếng) → `qc.py <id>…` và **xem ảnh** tới khi không lộ chữ, tấm che
   không trôi. Kiểu che: biển trắng trơn bo góc, viền xám mảnh, rộng hơn biển ~8 %, màu trắng theo ánh sáng tại chỗ, có nhiễu hạt; số sơn trên thân xe →
   `patch` (tô màu thân xe lấy theo hàng). `build.py` (hàm `BS()`) tự dùng bản `_bs` cho hình — mốc, đo rung, tiếng giữ nguyên; CapCut cũng nhận bản đã che.
   Khoảng cần che lấy từ `shots_of()` (khúc người nói `sync` → che hết khúc keep). Dò tự động (gói ONNX) chưa cài được → chấm tay 4 góc.
2. **Transcript**: `<python> scripts/transcribe.py <file> <dự án>/work/words.json`, hiệu đính tay tên sản phẩm, W/K/lm, cos/pha
   (bảng lỗi nhận giọng trong `quy-trinh.md`); từ không chắc → hỏi người dùng. Gợi ý phụ đề: `scripts/words_to_caps.py`.
3. **Nghe lại, bỏ LẶP / VẤP (tự làm, không đợi người dùng nhắc)**:
   `<python> scripts/stutter.py <dự án>/work/words.json --audio <file nguồn> --out <dự án>/work/cuts.json` — **bắt buộc `--audio`** (nghe sâu).
   Lý do (lỗi Corolla Cross v2, 18/11/2026): whisper nhận cả clip **gộp các lần nói lại thành một** và kéo dài 1 từ ~2 s để che
   ("theo em thì mức độ ưu, theo em thì…" chỉ còn "theo em thì…") → đọc transcript thường KHÔNG thấy lặp. Nghe sâu = dò từ bị kéo dài / khoảng hở
   còn tiếng nói, nhận giọng riêng đoạn đó, lộ ra lời bị giấu.
   → tìm từ/cụm nói lặp liền nhau và **nói lại** (cụm lặp sau vài từ nói hỏng) (**giữ lần cuối**, cắt các lần trước), tiếng đệm "ờ/à/ừm" (whisper hay ghi "ờ…" thành "ở,"), nói cụt rồi nói lại,
   ngừng > 0,6 s. **Nghe lại từng chỗ** (cắt `-ss/-t` rồi nhận giọng lại) trước khi chốt; lặp có chủ ý ("rất rất sáng") thì giữ.
   Chỗ chốt cắt → đưa vào `cuts` của đoạn; cảnh người nói đặt `sync=True` để hình nhảy theo tiếng.
   **Mỗi mối cắt trong cảnh người nói phải TRÁM** bằng `covers` (insert/animation khớp lời: ảnh hộp, sản phẩm, b-roll, thẻ thông số; ảnh tĩnh tự zoom chậm),
   ~2 s quanh mối cắt (`COVER`, 1,5–3 s). Không khai báo đủ `covers` → build **tự lấy tư liệu có sẵn** (ảnh/clip trong `insert/`, xoay vòng); dự án không có insert nào → **punch-in**
   (đổi cỡ khung người nói ngay mối cắt, che cú nhảy hình). Ưu tiên chọn tay insert khớp lời; Codex chỉ là tuỳ chọn.
4. **Viết `work/build.py`** từ `scripts/build_template.py` (new_project đã chép sẵn): `SEGS` (keep / shots / caps / kin), `NAME`, `W,H,FPS`,
   `THEME="dark"`. Học cách dựng từ `examples/`.
   - **Giọng tự lọc tạp âm theo từng file** (`DENOISE="auto"` mặc định từ 1.6, anh chốt 19/11/2026: lọc siêu mạnh hết bị **méo tiếng**):
     đo nền ồn mỗi file → giới hạn suy giảm DeepFilterNet = nền ồn + 52 dB (kẹp 0–28 dB), post-filter/gate nhẹ chỉ khi ồn nhiều; còn ồn nhẹ cũng được.
     Build in mức đã chọn cho từng file. Anh chê còn ồn/méo → dịch mục tiêu -52 dBFS. `"strong"`/`"soft"` vẫn còn. Lọc 1 file lẻ:
     `<python> scripts/denoise.py <file> --auto`. Không chạy 2 lượt.
   - **Nhạc tự chọn** (`MUSIC="auto"`): nhạc người dùng bỏ vào `assets/music` thắng; không có thì bộ Mixkit có giấy phép (setup đã tải),
     chọn theo mood `"auto:tech|drive|groove|warm"` (công nghệ/thông số · chạy xe đêm · thi công cận · khách hàng/kết vui), nối vòng có hoà âm,
     duck theo giọng. Báo tên bài + giấy phép khi giao.
   - **Chữ pop up**: hiện mượt (mask 0,55 s), **đứng yên ≥ 1,2 s** (`Word.HOLD_MIN`), ra mượt 0,35 s; không lên/xuống đột ngột.
     Build báo lỗi nếu chữ không đủ thời gian đứng trong đoạn → cho hiện sớm hơn hoặc gộp dòng, không rút thời gian đứng.
   - **Rà minh hoạ mức HIGH** (anh chốt 19/11/2026): lập bảng câu thoại → cảnh; câu nào nói **tính năng / hiệu quả** (giảm nhiệt, chống UV, cản nhiệt,
     riêng tư, tầm nhìn đêm), **thông số** hay **vị trí dán** (kính lái / sườn / hậu / cửa sổ trời) đều có cảnh **ảnh render chân thực + animation**
     **Thà thừa còn hơn thiếu.**
   - **Style minh hoạ (từ 1.6, anh chốt 19/11/2026, áp cho mọi dịch vụ)**: ảnh render **realistic KÍN KHUNG, sáng sủa** (showroom/xưởng sáng có
     đèn đỏ, đường nắng, nội thất sáng — **không phông trắng trơn, không mảng trắng chừa chữ**), tone brand **đỏ–trắng–đen** kiểu 3M, xe trắng;
     hiệu ứng `scripts/fx_light.py`: **tia nhiệt/UV thẳng bay chậm** (không sóng uốn lượn) có mũi tên, khiên bạc chặn + tia dội ngược, phim quét
     kính mép đỏ, panel trắng header đỏ có thanh đo, 1 vệt đỏ mảnh chân khung. Mẫu đầy đủ 14 cảnh: `examples/anim_minh_hoa_sang/`.
     Clip đặt trong `work/anim_light/` → chữ kin tự đổi theme **"paper"** (chữ đen, keyword hộp đỏ chữ trắng); đoạn người dẫn giữ chữ trắng.
     Ảnh nền: Codex, prompt "photorealistic full-frame, bright, red/white/black accents, no text/logo/plate", đo kính bằng lưới 100 px, preview 6 khung/cảnh.
   - **Diễn hoạt 3D có tracking (từ 1.6.1, anh duyệt 19/11/2026 — mẫu `examples/anim_3d/uv3d.py`, cảnh chống UV)**: máy quay ảo lia/xoay nhẹ + tiến vào
     (homography K·R·K⁻¹ áp lên ảnh nền); **mọi hiệu ứng đi chung phép chiếu đó** (tracking). Mặt kính = mặt phẳng (4 góc → homography): lớp phim
     (lưới tổ ong), vòng sóng, vệt bóng lướt chiếu lên đúng mặt kính theo phối cảnh, cắt theo đa giác kính. Tia: chùm thuôn (nhỏ ở xa, to gần máy),
     lõi sáng + quầng, vệt sáng dài trôi chậm dọc tia (không chấm tròn), chạm kính → loé nhỏ + tia dội ngược. **Tốc độ tia: bay tới kính ~1,6 s**
     (anh chê nhanh → chậm thêm 1/3); tia đã bay sẵn trước khung đầu để chạm kính đúng mốc lời. Clip dài (`DUR=10`) → mỗi ~2,6 s một đợt tia.
     **Không răng cưa/vỡ nét**: dựng 2× (3840×2160), nét `cv2.LINE_AA` + toạ độ `shift=2`, thu về 1080p `INTER_AREA`, x264 crf 12. Soi khung 100 % trước khi giao.
   - **Tăng tốc RTX (từ 1.6.5, anh chốt 20/11/2026)**: `scripts/fast3d.py` — `over()` trộn lớp + `cv2.GaussianBlur` lớn chạy trên GPU (CuPy, setup tự cài
     `cupy-cuda12x[ctk]` khi có NVIDIA; không có GPU → CPU, kết quả như nhau) và `encode_parallel(out, n, "<module>", "<hàm khung>")` chia khung cho
     nhiều tiến trình (số = `e365.auto_par`, theo trần 80 % máy) rồi nối khúc không nén lại. Đo thật: cảnh ảnh thật 4K 144 khung **9 phút → 44 giây**.
     Thư viện cảnh dùng `over = FX.over; FX.patch_cv2_blur()` và `encode = FX.encode_auto` (xem `examples/anim_3d/lib3d.py`): **mọi cảnh tự render
     song song + RTX**, không cần sửa từng cảnh; hàm khung phải ở cấp module (lambda/hàm lồng → tự chạy tuần tự). `FX_SERIAL=1` ép tuần tự.
   - **Áp tăng tốc cho mọi bước render (1.6.7)**: minh hoạ nền sáng `fx_light.encode` → cũng qua `encode_auto` (song song); che biển
     `bienso/render.py <n1> <n2> …` → nhiều clip chạy song song (kẹp 3 vì GeForce giới hạn phiên NVENC); chữ MOV cho CapCut → gom lại render
     song song `PAR` luồng (thử 12 dòng: 1,8 s → 0,5 s, giống hệt bản tuần tự); dựng đoạn → song song `auto_par` + chỉ dựng lại đoạn đổi.
     Thoại không nói số → cảnh không có số/thanh đo.
   - **Hình minh hoạ: dùng tư liệu có sẵn trước** — ảnh/clip trong `insert/`, b-roll, frame đẹp trích từ chính clip (ảnh hộp, sản phẩm, cận chi tiết).
     **Codex là tuỳ chọn**: kiểm `codex --version` (hoặc `where codex` trên Windows); **máy không có Codex CLI hoặc chưa đăng nhập → bỏ qua, không cài, không hỏi,
     không coi là lỗi**, dựng tiếp bằng tư liệu có sẵn. Máy có Codex mà thật sự thiếu hình minh hoạ thì trong `<dự án>/insert/ai/` chạy
     `codex exec --skip-git-repo-check -s workspace-write [-i ref.png] -- "<prompt tiếng Anh>, 16:9 (hoặc 9:16), no text. Save as <ten>.png in the current directory." < /dev/null`
     (`-i` phải trước `--`; ~1–2 phút/ảnh). Chỉ cho minh hoạ/bối cảnh — **không** tạo hộp, thông số, vệt sáng, ảnh trước/sau, xe khách.
     Soát ảnh (chữ sai dấu, tay, logo méo), ghi prompt vào `brief.md`, báo ảnh nào là AI.
   Mọi mốc cắt, chữ, vị trí, âm lượng nằm trong script; sửa = sửa script rồi chạy lại.
   - **Rung (tự làm)**: shot chèn để giây nguồn `None` → build tự chọn khúc **ít rung nhất** của clip (bỏ 0,5 s đầu lúc bấm máy;
     lia/dolly đều không tính là rung — `scripts/shake.py`); chèn rung → build chặn, chỉ clip + giây.
     **Không tự chống rung** (người dùng chốt 18/11/2026: tự bấm chống rung trong CapCut); cảnh người nói rung → build chỉ in mốc để báo người dùng.
     Soát nhanh cả thư mục: `<python> scripts/shake.py 2.5 <dự án>/insert/*.mp4`.
   - **Tận dụng nguồn quay, không chèn sơ sài**: mỗi 2–4 s một shot chèn khớp lời (nhiều góc, nhiều khúc từ các clip đã quay — một clip dài
     dùng được nhiều khúc khác nhau); người nói liền mạch ≤ `MC_MAX` (8 s) — quá thì build chặn. Mở clip vẫn thấy người dẫn.
   - **Trình bày (học từ mẫu, KHÔNG lạm dụng — mỗi kiểu vài lần/clip, ưu tiên hình quay thật)**:
     · **card**: `sh(o, "insert/x.mp4", None, card=dict(chip="F10 Turbo V2 · 4300K · cos", side="left"))` — cảnh quay trong khung bo góc ~58 %
       trên nền mờ tối của chính nó, chip nhãn góc trên trái, chữ lớn phía đối diện bằng `kin`: từ nối nghiêng (`it`, vd. *phiên bản*) + số/keyword
       đỏ đậm (`k`, vd. **4300K**). Dùng cho câu nêu thông số / phiên bản / so sánh.
     · chữ lớn keyword đỏ + từ nối nghiêng quanh người dẫn; zoom vào thông số in trên hộp (bằng chứng) kèm chip nguồn.
     · Ý tưởng thêm từ các style trong máy (`styles/` của xưởng: Auto365, MagentX, Bàn ảnh; skill luancut/papercut/seecut) — chỉ mượn khi hợp lời.
5. **Nháp để rà = 720p** (anh chốt 18/11/2026): `cd "$WS" && <python> projects/X/work/build.py` → `output/<NAME>_<ratio>_v<n>_nhap720p.mp4`
   (vẽ thẳng 1280x720). Toạ độ/cỡ chữ trong SEGS luôn viết theo khung thiết kế 1920x1080 (9:16: 1080x1920), build tự quy đổi.
   Soát tự động phải qua: tràn khung, đè phụ đề, **chữ đè đầu/vai người** (YuNet, `FACE_CHECK`), mối cắt chưa trám, chữ không đủ thời gian đứng,
   **chèn rung**, **người nói liền mạch quá lâu**. Contact sheet bản nháp → **xem ảnh**; **`<python> scripts/stutter.py --check <bản nháp>`** phải ĐẠT
   (CHƯA ĐẠT → thêm vào `cuts`, xuất `VER` mới). Gửi bản nháp cho người dùng duyệt. Bước dự kiến > 5 phút → báo trước.
6. **Duyệt xong → ĐƯA VÀO CAPCUT (không xuất file ghép)** — **CHỈ khi người dùng nói đã duyệt bản nháp 720p và bảo đưa vào CapCut; KHÔNG tự đưa**
   (anh chốt 19/11/2026). Người dùng tạo 1 project trống trong CapCut, đặt tên, **tắt CapCut**, rồi
   `CAPCUT="<tên project>" <python> projects/X/work/build.py` (cần CapCut MCP `~/capcut-mcp-macos` hoặc `~/capcut-mcp-windows`; project đã có nội dung →
   từ chối, `CAPCUT_CLEAR=1` để ghi đè, bản cũ được sao lưu). Track:
   **MC** (clip người dẫn đã cắt lặp/vấp, **tắt tiếng**, chạy liền bên dưới) · **CHÈN** (nguồn chèn gốc, zoom = keyframe; cảnh card = clip dựng sẵn) ·
   **CHỮ 1..n** (chữ animation Claude vẽ, MOV ProRes 4444 trong suốt — **không dùng chữ CapCut, không phụ đề**) · **VOICE** (giọng MC + voice off đã lọc tạp âm,
   **tách theo từng khúc keep** — mỗi khúc 1 clip trỏ vào file giọng ĐẦY ĐỦ của nguồn (đã lọc, cùng mức như bản mix), điểm vào = mốc keep, khớp clip MC →
   người dùng kéo dài được cả MC lẫn giọng nếu lỡ cắt mất chữ; **không xuất 1 file voice liền** (anh chốt 19/11/2026; build `voice_pieces()`)) · **NHẠC** (đã duck theo giọng) · **SFX** (nếu có).
   Không tự thêm chuyển cảnh/hiệu ứng/filter CapCut (người dùng tự thêm). Soát bằng CapCut MCP `capcut_frame` vài mốc trước khi báo.
   Chỉ khi người dùng đòi file ghép: `FINAL=1 VER=n` → 4K HEVC (3840x2160 / 2160x3840).

## Rà bổ sung cảnh 3D sau mỗi bản nháp (từ 1.6.4, anh chốt 20/11/2026 — Everest v5→v6 thêm 8 cảnh)
Dựng xong nháp có minh hoạ → **tự rà lại toàn bộ lời thoại** tìm câu nói về tính năng / hiệu quả / tầm nhìn / riêng tư / cảm giác trong xe /
hiểu lầm ("càng tối càng mát?") / vị trí kính mà hình đang **chỉ là cảnh thi công chung chung** → lập bảng đề xuất gửi anh:
`# | mốc | lời thoại | cảnh 3D đề xuất`, chia **🔴 nên làm** (ý chính: hook, so sánh mã phim theo vị trí kính, riêng tư, đánh đổi tầm nhìn đêm)
và **🟡 làm thì tốt** (nắng chói, lái đêm, màu phim ≠ cách nhiệt, khoang dịu lại); **không** thay cảnh quay thật đang làm bằng chứng
(phân tầng màu kính thật, thông số in trên hộp). Kèm ước lượng thời gian (Codex ảnh ~2–3 phút/ảnh, ≤3 song song; viết + preview;
render 3D song song; dựng lại chỉ đoạn đổi) → anh chọn số cảnh → làm.
- Cảnh mới **thay shot chèn** ở đúng câu (đặt bằng `o_()`), **không** thay cảnh người dẫn nói (sync), không phá shot đã ghim vùng che biển.
- Độ dài cảnh = đúng khoảng shot bị thay; tia chạm kính đúng mốc chữ/số của lời.
- Ảnh nền mới tên riêng (`real/n_*`, `real/m_*`), tránh 2 cảnh cùng ý/cùng ảnh đứng gần nhau.
- ≥ 5 cảnh → chia agent theo mục dưới. Bản mới → **dòng thời gian CapCut mới** (không sửa dòng anh đang chỉnh).
- Danh mục cảnh đã có (dùng lại ý, đổi ảnh/xe): truyền sáng % · loại bỏ năng lượng % · riêng tư % · đa lớp + nano · UV 99,9 % · hồng ngoại % ·
  càng tối ≠ càng mát (2 kính split) · top view 2 mã phim theo vị trí · gia đình ghế sau nắng kính hông · gương đêm qua kính sườn ·
  nắng chói kính lái · đường đêm qua kính lái · phim tối/sáng cùng chặn nhiệt · khoang lái dịu lại · cửa sổ trời.

## Chia việc cho subagent (từ 1.6.3, anh chốt 20/11/2026)
Việc dài (> ~15 phút: nhiều cảnh minh hoạ 3D, che biển nhiều clip, dựng + CapCut) → **giao subagent chạy nền**, phiên chính chỉ điều phối và báo anh.
Nhiều cảnh minh hoạ (≥ 5) → **sinh thêm subagent chạy song song**, chia theo cảnh để không giẫm nhau:
- **Agent A (tích hợp)**: cảnh chính + mọi sửa `work/build.py`/thư viện chung + dựng nháp + CapCut. Chỉ A được sửa build và thư viện dùng chung (không phá API đang import).
- **Agent B, C… (cảnh phụ)**: mỗi agent một file cảnh riêng (`work/anim_3d/scenes3d_b.py`…), ảnh nền thư mục riêng (`real/m_*`), xuất mp4 tên riêng;
  **chỉ ĐỌC** `build.py` (đo độ dài shot theo câu thoại bằng `o_()`/`src2out`). Xong ghi file hẹn `work/anim_3d/B_DONE.txt`
  (`tên | đoạn | mốc nguồn | độ dài s | số khung | câu thoại`). A chờ file hẹn rồi mới ghép + dựng.
- Phân công đổi giữa chừng → nhắn agent đang chạy (SendMessage) phạm vi mới trước khi sinh agent mới.
- **Codex tối đa 3 lệnh song song tính chung mọi agent**; trần CPU 80% máy vẫn áp chung (cpu_watch canh cả máy).
- Mỗi agent tự QC ảnh/preview/crop 100 % phần của mình; A soát contact sheet bản dựng cuối. Phiên chính đọc báo cáo, xem sheet, báo anh ngắn.

## Bước 3 — Giao
- Mở thư mục chọn sẵn file: Mac `open -R <file>`, Windows `explorer.exe /select,"<file theo dạng C:\...>"`.
- Báo 3–5 dòng: mạch dựng, chỗ cắt vì lỗi, thông số đã dùng + nguồn, phần tạm (nhạc/CTA), từ cần soát.
- Người dùng góp ý → sửa `build.py`, render lại đúng đoạn (`build.py 03`), xuất `VER` mới.
- Đã đưa vào CapCut: báo tên project + các track; nhắc mở CapCut để thêm chuyển cảnh/hiệu ứng nếu muốn.

## Luật không thương lượng
Không bịa thông số (chỉ lời đọc đã xác nhận / in trên hộp / fact sheet, kèm chip nguồn). Ảnh AI chỉ minh hoạ, không làm bằng chứng
(hộp, beam, trước/sau, xe khách phải là ảnh thật — thiếu thì xin). Không gắn nhiệt độ màu khi chưa xác nhận. Không nhạc/SFX không rõ giấy phép.
Trần CPU **80% tổng máy** (E365_CPU, anh chốt 20/11/2026 — tính theo % máy, không theo số luồng); số đoạn render song song **tự tính** `e365.auto_par()` = luồng × 80% / 4 (i7-14700K → 6, Mac M 10 nhân → 2; ghi đè bằng PAR); `e365.start_cpu_watch` canh trần.

## Code
| File | Vai trò |
|---|---|
| `setup.sh` / `setup.ps1` | Cài + tạo `$WS` (Mac / Windows), idempotent |
| `scripts/check_env.py` | Kiểm tra máy, thoát mã 1 nếu còn THIẾU |
| `scripts/demo_project.py` | Chạy thử trọn quy trình ra 1 clip, ghi `.e365_ready` |
| `scripts/e365.py` | Thư viện: `VReader` (tự chọn videotoolbox / NVDEC / CPU), `Encoder`, `Word`/`layout_line` (chữ động, chống tràn), `cap_img` (phụ đề), `check_layout`, `rounded`/`with_shadow`/`cta`/`soft_bg`, `cut_voice`/`loudness`/`final_mix`/`mux`, `STYLES["dark"]` |
| `scripts/build_template.py` | Mẫu build 1 dự án: SEGS → render tuần tự có cache → âm thanh → bản giao |
| `scripts/transcribe.py`, `words_to_caps.py` | Nhận giọng tiếng Việt từng từ (Mac mlx-whisper / Windows faster-whisper CUDA), gợi ý phụ đề |
| `scripts/denoise.py` | Tự cài DeepFilterNet 0.5.6 (kiểm SHA-256) + lọc tạp âm giọng (`--auto` theo nền ồn từng file / siêu mạnh / `--soft`) |
| `scripts/fast3d.py` | Tăng tốc minh hoạ 3D: trộn lớp + làm mờ trên RTX (CuPy), render chia khung nhiều tiến trình |
| `scripts/fx_light.py` | Hiệu ứng minh hoạ nền sáng style 3M: tia nhiệt/UV, khiên, tia dội, phim quét, panel thanh đo, vệt đỏ, encode |
| `scripts/shake.py` | Đo rung, chọn khúc ít rung cho shot chèn (cache `work/shake`); `--stab` chống rung tay khi cần (build không tự dùng) |
| `scripts/bienso/` | Che biển số: `sheet`/`grid`/`fine` (tìm + đọc góc), `tracks.py` (khai báo), `track` (bám phối cảnh), `render` (→ `insert_bs/`, `input_bs/`), `qc` |
| `scripts/capcut_export.py` | Đưa bản dựng vào project CapCut theo track (MC / CHÈN / CHỮ MOV trong suốt / VOICE / NHẠC / SFX) |
| `scripts/stutter.py` | Nghe sâu (lộ lời whisper giấu) + dò lặp / nói lại / vấp / ngừng dài → `cuts.json`; `--check <bản giao>` soát cuối |
| `scripts/data/face_detection_yunet_2023mar.onnx` | Nhận diện mặt (OpenCV YuNet, MIT) cho soát chữ đè đầu/vai |
| `scripts/music.py` | Tự tải bộ nhạc Mixkit có giấy phép + chọn bài theo mood |
| `scripts/qc.py`, `contact_sheet.py` | Soát thông số/LUFS/khoảng lặng, contact sheet |
| `scripts/new_project.py`, `cpu_watch.py` | Tạo khung dự án, canh trần CPU |
| `examples/f10_10s_16x9_nen_toi.py` | Bản 10 s 16:9 nền tối — mẫu chữ động gọn nhất |
| `examples/mazda_full_16x9.py` + `textfx.py` | Clip 16:9 đầy đủ 20 đoạn: ảnh bảng căn đèn, split so sánh, chip nguồn, end card |

`examples/` là code job thật để học cách dựng (không chạy nguyên xi; đường dẫn từ biến `E365_ROOT` / `PRJ`).
