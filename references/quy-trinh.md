# Skill Edit Auto365 — quy trình & luật

Trích từ quy trình chuẩn của xưởng Edit365 (AGENTS.md). Đường dẫn `scripts/…` tính từ gốc skill; đường dẫn `projects/…` là dự án gốc ở xưởng (chỉ để tham khảo).

> **Mac và Windows.** `<python>` = `.venv/bin/python` (Mac) hoặc `.venv\Scripts\python` (Windows). Thư viện `e365` tự chọn phần cứng:
> Mac = videotoolbox + `scale_vt`, nháp `h264_videotoolbox`; Windows GPU NVIDIA = NVDEC (`-hwaccel cuda`) + `scale_cuda`, nháp `h264_nvenc`
> (không có `scale_cuda` → giải mã NVDEC + scale CPU; không có GPU → CPU). Ép bằng biến `E365_HW=vt|cuda|none`.
> Trần CPU = **50% số luồng của máy** (Mac 10 nhân → 500%; i7-14700K 28 luồng → 1400%); x264 bản giao Mac 2 luồng, Windows 4 luồng (`E365_X264_THREADS`).
> Các số đo bên dưới là trên Mac. Contact sheet theo mốc dùng `file@giây` (dấu @ vì đường dẫn Windows có "C:").

## 4. Giới hạn tài nguyên máy (bắt buộc — máy anh Việt làm việc khác song song)
- **Trần: tổng CPU ≤ 500%** (50% của 10 nhân) tính tổng `%CPU` trong `ps` của **mọi** ffmpeg + python render, kể cả job dự án khác.
  Được dùng hết 500%. Luật là trần CPU, không phải đếm tiến trình. Vượt trần → tạm dừng render của mình, chờ xuống dưới trần rồi chạy tiếp.
- Xử lý **từng đoạn tuần tự**, không Pool/song song nhiều đoạn. Cho phép trong một đoạn: **1 ffmpeg đọc + 1 python vẽ + 1 ffmpeg encode** nối ống.
- **Canh CPU suốt job:** `<python> scripts/cpu_watch.py <pid_job> <log> 50` (ps mỗi 60 s; vượt 500% → SIGSTOP mọi ffmpeg 15 s, ghi log).
  Script build tự bật bằng `e365.start_cpu_watch(...)` lúc khởi động (log `projects/X/work/cpu_watch.log`).
  Kiểm tay: `ps -axo pcpu,comm | awk '/ffmpeg|Python/{s+=$1} END{print s}'`.
- **Cách nhanh nhất đã đo** (11/10/2026, clip 76 s 9:16: **44 s**, CPU trung bình ~350%; cách cũ giải mã CPU: 347 s):
  - Giải mã phần cứng + scale **ngay trên GPU** về đúng cỡ cần, chỉ grade trên frame đã nhỏ (không xử lý ở 1728/4K):
    ```
    ffmpeg -threads 2 -hwaccel videotoolbox -hwaccel_output_format videotoolbox_vld -ss <t> -i <src> \
      -vf "scale_vt=w=<W>:h=<H>,hwdownload,format=p010le,fps=30,<grade>,format=rgb24" -an -f rawvideo -pix_fmt rgb24 -
    ```
    Nguồn 10-bit (DJI, iPhone HDR) → `format=p010le`; nguồn 8-bit → `format=nv12`. Đã đóng gói: `scripts/e365.py` class `VReader` (tự dò bit).
  - Python (Pillow) vẽ chữ trên frame đã nhỏ, pipe sang encode (`e365.Encoder`):
    nháp `-c:v h264_videotoolbox -b:v 12M` (gần như 0 CPU);
    bản giao `libx264 -crf 18 -preset medium -threads 2 -x264-params lookahead-threads=1`
    (đo 12/10: x264 4 luồng → đỉnh 648%, 3 luồng → 538%, **2 luồng → 446%**, chỉ chậm hơn ~16%).
  - ffmpeg phụ (mix tiếng, concat, đo LUFS) thêm `-threads 4`.
  - Khi xuất bản giao, ffmpeg đọc hình phải giữ 2 luồng (để 3 luồng + x264 4 luồng từng vọt 618%).
  - **Nguồn Sony XAVC** (major_brand `XAVC`, vd. C64xx.MP4): 4:2:2 10-bit thì videotoolbox không giải được; 4:2:0 8-bit giải được
    nhưng **rơi ~3,5% frame → hình khựng** (lỗi v2 VF3, 17/10/2026). `VReader` tự chuyển giải mã CPU **1 luồng** cho mọi clip XAVC
    (2 luồng từng vọt 570–733%; 1 luồng: bản giao 118 s mất ~3 phút, trung bình ~380%).
  - Cảnh motion graphics vẽ bằng Pillow (nhiều lớp GaussianBlur 1080x1920/frame) + x264 bản giao: từng vọt 720% (17/10) → khi làm MG nhiều, giảm lớp blur hoặc vẽ glow ở nửa độ phân giải.
  - Thẻ video nhỏ chèn trong khung (picture-in-picture): đọc từ **proxy 720p** làm trước (`work/proxy/`), không giải mã 4K lần 2 (17/10: 3 ffmpeg 4K → 623%).
  - Soát khựng hình: đếm frame liền nhau gần như giống hệt (chênh < 0,15/255) **chỉ trong các cảnh quay** (bỏ thẻ tĩnh/ảnh tĩnh).
  - Clip quay dọc có metadata xoay: đường GPU (scale_vt) không tự xoay → `VReader` đã tự `transpose` (sửa 17/10/2026).
  - Bản giao nguồn XAVC (giải mã CPU 1 luồng + x264 2 luồng + python vẽ nhiều hiệu ứng): đỉnh có lúc 579% (17/10, cpu_watch tự dừng 15 s).
- **Cấm / đã thử và bỏ:**
  - **Không dùng `taskpolicy -b`** cho render: ép chạy trên nhân tiết kiệm điện, chậm ~8 lần. (Lệnh cũ trong `STATUS.md`/script Mazda có `taskpolicy -b` là lỗi thời.)
  - Không giải mã bằng CPU ở độ phân giải gốc (4K → scale trong CPU).
  - **Không dùng PyAV** để đọc video khi render: `av` có cài trong `.venv` nhưng bộ ffmpeg đi kèm **thiếu filter `eq`** (phải thay bằng `lutrgb`+`hue`),
    filter graph tự ăn hết nhân (python lên 340% dù chỉ 1 tiến trình), và tổng thể chậm hơn đường videotoolbox ở trên.
  - Không Pool/multiprocessing nhiều đoạn (một bản dựng cũ chạy 6 tiến trình → ~80% cả máy, quạt quay mạnh).
- Render frame bằng trình duyệt (template motion): 1 trang duy nhất, không mở nhiều worker.

## 6. Quy trình bắt buộc
1. **Soát nguồn trước khi dựng**: `<python> scripts/qc.py <file>` (độ phân giải, fps, thời lượng, khoảng lặng), contact sheet 1 fps (`<python> scripts/contact_sheet.py`).
   Xem kỹ từng frame tìm **lỗi video AI**: vật thể mọc ra, tay/ngón tay sai, chữ méo, logo biến dạng, glow vô lý
   (đã gặp: đèn trên tay biến thành cánh tay robot đen + glow tím từ ~15 s ở `input/F10_Turbo_V2_goc.mp4`).
   Đoạn lỗi → cắt hình, giữ tiếng, phủ bằng insert phù hợp lời đọc. Báo anh mốc lỗi.
   Clip AI Gemini/Veo có dấu ✦ góc phải dưới → xoá bằng `scripts/unwm_gemini.py` (1280x720); cỡ khác thì đo alpha lại.
   Clip điện thoại quay dọc có metadata xoay → `e365.probe` trả w/h đã xoay. Clip camera chĩa trần/không có hình dùng được → chỉ lấy tiếng.
   Ghi danh mục tư liệu (file, nội dung, mốc dùng được, lỗi) vào `brief.md`.
2. **Transcript**: `<python> scripts/transcribe.py <video> projects/X/work/words.json` (cả thư mục: truyền thư mục), rồi **hiệu đính tay**
   tên sản phẩm, đơn vị W/K/lm, thuật ngữ cos/pha/bi gầm. Từ không chắc → đánh dấu và hỏi anh.
   - Lỗi nhận giọng đã gặp: "code"→**cos**, "cốt"→**cos**, "slide"→**X-Light**, "mỗi điện"→mỗi bên, "chứa ngại vật"→chướng ngại vật,
     "len 3 in"→lens 3 inch, "căng chỉnh"→căn chỉnh, "CX5/xe X5"→CX-5, "4300k"→4300K, "nhơm"→nhôm, "rảnh"→rãnh, "tảng"→tản, "dắt"→giắc, "cạn"→cản, "độ kính"→độ kín.
     Ghi bảng sửa của dự án vào `projects/X/work/fix.tsv` (mỗi dòng `sai<TAB>đúng`) để `words_to_caps.py --fix` áp tự động.
   - Câu nghi ngờ → nhận lại riêng đoạn đó (cắt `-ss/-t`) để so; hai lần ra giống nhau thì để theo lời nói thật (vd. "xem đồng bộ luôn nha").
   - Nhiều take cùng một câu → chọn **1 take**, không ghép hai nguồn (đã lỗi lặp từ khi ghép 2 take).
   - Gợi ý dòng phụ đề: `scripts/words_to_caps.py` (cắt ở khoảng ngừng > 0,3 s, dấu câu, ≤ 42 ký tự cho 9:16, ~46–48 cho 16:9);
     không tách từ ghép (nâng|cấp, ánh|sáng, đèn|gầm, nhiệt|màu, căn|chỉnh, F10|Turbo…). Đọc lại, sửa, rồi dán vào `caps` của SEGS.
3. **Mạch dựng** theo lời đọc: hook → reveal sản phẩm → lý do kỹ thuật → bằng chứng → lợi ích khi dùng → end card (nếu kênh cần).
   Không reveal hết ở frame đầu. Hero product phải rõ. Mở đầu clip phải thấy người dẫn.
4. **Insert khớp lời**: câu nói về thông số → zoom vào chỗ thông số in trên hộp/tài liệu (bằng chứng, không chỉ là chữ), kèm chip nguồn.
   Câu nói về vệt sáng → ảnh/clip beam thật. So sánh trước/sau → ghép đôi cùng khung, cân phơi sáng theo vùng không bị đèn chiếu.
   **Thiếu insert** → được tự gọi Codex CLI tạo ảnh (anh Việt cho phép 17/10/2026, không cần hỏi từng lần; cách gọi ở mục 5 "Tạo ảnh bằng Codex").
   Chỉ dùng cho ảnh **minh hoạ/bối cảnh** (đồ hoạ khái niệm, nền, cảnh tình huống); không thay bằng chứng (mục 9).
5. **Vùng chữ (anh chốt 17/10/2026, mọi clip 9:16):** chữ (tiêu đề, pill, số, phụ đề, chip nguồn) **không đè mặt, không đè logo**
   (biển "3M Pro Shop", biển số xe, logo áo…), **không đè sản phẩm**, và nằm trong **vùng an toàn TikTok In-Feed Ads**:
   1080x1920 → x 120–960, y 240–1260; dưới y 840 không vượt x 900 (cột nút bên phải). Nguồn: template TikTok (socialync.io/tools/safe-zones/tiktok).
   Build phải tự soát vùng an toàn (xem `projects/2026-10-17_VF3_3M_CR_BLK50_KinhLai/work/build.py` `Seg.check`) + soát mắt bằng ảnh từng cảnh có vẽ khung an toàn.
   Ảnh/video nền được tràn ngoài vùng an toàn, chỉ chữ phải nằm trong.
6. **Phụ đề** (anh chốt 17/10/2026): **frame nào đang có chữ pop up** (chữ lớn, tiêu đề, pill, chú thích, nhãn trên thẻ) **thì ẩn phụ đề** để không trùng;
   nhãn chương nhỏ, nhãn "Ảnh minh hoạ", chip nguồn không tính. PNG (mục 5), mặc định Inter Display ExtraBold 66 (16:9) / ~48–56 (9:16), trắng viền tối + bóng mềm, keyword màu nhấn
   (mặc định hổ phách `#FFC83D` = `&H3DC8FF&`; hoặc màu thương hiệu, mục 8), pop nhẹ 140 ms. Mỗi dòng ≤ 1 keyword.
   Vị trí: 16:9 ~86% chiều cao; 9:16 ~0,62–0,70 H (đặt `cap_y` theo từng shot để né mặt/sản phẩm).
7. **Âm thanh**: cắt khoảng lặng > 0,4 s (chừa 0,1 s), fade 12 ms vào / 15 ms ra ở mỗi mối cắt, highpass 90 Hz, chuẩn từng đoạn về -17 LUFS rồi nén nhẹ
   (2,5:1), nhạc duck theo giọng (sidechaincompress threshold 0.03 ratio 6), SFX tiết chế (whoosh ở chuyển cảnh lớn, tick ở số liệu, thump ở reveal/end,
   pop nhẹ ở keyword), bus SFX ~-6 dB dưới giọng. Chuẩn **-14 LUFS, true peak -1,5 dB** (`e365.final_mix`). Clip < 10 s: loudnorm 1 lượt có thể lệch ~±1 LU → đo lại.
   Ưu tiên nhạc/SFX trong `assets/`. Chỉ tự tổng hợp khi không có, và phải báo. Nhạc ngắn hơn clip → nối vòng theo nhịp.
   Giấy phép nhạc ghi ở `assets/music/_downloaded/SOURCES.md` (Mixkit Free License: dùng online/quảng cáo online được, không TV/radio).
   Tiếng hiện trường thật (tách vỏ, cắn, bấm công tắc) giữ lại khi tạo cảm giác ASMR; `keep` có `(None, giây)` để chừa khoảng nghe tiếng đó.
8. **Ghép**: khoá timeline theo lưới frame (`keep_len` làm tròn theo FPS); mỗi segment đệm thêm ~6 frame nếu dùng xfade (xfade bỏ phần dư);
   chuẩn hoá `fps,settb,setpts` trước xfade. Cắt thẳng thì concat `-c copy` các đoạn đã cache.
   **Chuyển cảnh (anh chốt 17/10/2026):** hai cảnh **khác khung hình → cắt thẳng**, không hiệu ứng, không tiếng swish;
   hai cảnh **cùng khung nối tiếp** (cùng nguồn, cỡ khung gần nhau) → hoà tan nhẹ ~6 frame cho đỡ khựng. **Hạn chế pop up**: chỉ giữ chữ thật sự cần
   (số liệu, tiêu đề chương, tên sản phẩm, CTA); còn lại để phụ đề.
9. **Tự kiểm trước khi giao**: contact sheet bản cuối (mỗi cảnh ≥ 1 frame), không chữ đè sản phẩm/thông số/mặt người, không còn frame lỗi AI,
   `<python> scripts/qc.py` (LUFS, TP, thời lượng tiếng = hình), soát bố cục tự động đã qua (`check_layout`). Sửa màu → so cùng khung hình bản trước/bản mới.

## 9. Luật nội dung (không thương lượng)
- **Không bịa thông số.** Chỉ đưa lên màn hình thông số có nguồn: lời đọc đã xác nhận, in trên hộp, fact sheet. Ghi rõ nguồn khi chèn
  (vd. "Thông số in trên hộp: POWER 75/45W").
- Không dùng claim không kiểm chứng được dù có in trên bao bì (vd. "Germany Technology", "Light beyond limits").
- Không gắn nhiệt độ màu (3000K/4300K/6500K…) cho ảnh beam nếu chưa xác nhận ảnh nào là màu nào. Không ghi "sáng gấp X lần" từ số đo ảnh.
- Ảnh AI (Codex) **không** dùng làm bằng chứng: không tạo ảnh sản phẩm thật, hộp/thông số, beam/vệt sáng, ảnh trước–sau, xe của khách.
  Những thứ đó thiếu → báo anh xin tư liệu thật.
- Không hiệu ứng làm màu: không flare không nguồn, không glow kiểu game, không khói, không speed line, không nhân bản người, không bóng người cắt AI.
- Tránh từ: đẳng cấp vượt trội, sang trọng bậc nhất, siêu phẩm, bứt phá, biến đêm thành ngày.
- Chỉ dùng nhạc/SFX có giấy phép rõ ràng; clip của kênh khác chỉ dùng tham khảo style, không đưa hình/tiếng vào bản dựng.

## 10. Khung hình
- Nguồn 16:9 → bản chính 16:9 1920x1080.
- Bản 9:16 (1080x1920): chỉ khi nguồn đủ phân giải (≥ 1080 chiều ngang cho phần crop); nếu không, dùng ít cảnh người dẫn, nhiều ảnh sản phẩm/beam độ phân giải cao.
- fps ra: **đúng fps nguồn chính** (24 cho clip AI 24 fps; DJI/điện thoại đo bằng ffprobe, có máy 25, có máy 30). Không đổi 25→30 (lặp frame, giật).

