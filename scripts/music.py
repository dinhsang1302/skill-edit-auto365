#!/usr/bin/env python3
"""Tự tìm nhạc nền có giấy phép rõ ràng và chọn bài hợp clip.

Dùng (từ thư mục làm việc):
  <python> scripts/music.py --install            tải bộ nhạc Mixkit mặc định vào assets/music/_downloaded (setup tự gọi), ghi SOURCES.md
  <python> scripts/music.py [mood] [giây]        in bài sẽ chọn (mood: tech | drive | groove | warm | auto)
Trong build: MUSIC = "auto" (hoặc "auto:drive") → e365 gọi pick() lúc ghép tiếng.

Cách chọn: ưu tiên nhạc người dùng tự bỏ vào assets/music (ngoài _downloaded, có giấy phép của họ); không có thì dùng bộ Mixkit.
Theo mood nếu chỉ định; "auto" = theo hash tên dự án để các clip khác nhau không cùng một bài. Nhạc ngắn hơn clip thì e365.music_bed
nối vòng có hoà âm 1,5 s. Nhạc tự duck theo giọng trong final_mix (sidechain), fade vào 0,3 s / ra 1,5 s.

Giấy phép bộ mặc định: Mixkit Stock Music Free License — dùng thương mại/online (YouTube, Facebook, TikTok, quảng cáo online) được,
không cần ghi công; KHÔNG dùng cho TV/radio, CD/DVD, game (https://mixkit.co/license/#musicFree).
"""
import hashlib, json, sys, urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
DL = ROOT / "assets/music/_downloaded"
LIB = [  # id Mixkit, file, tên bài, tác giả, mood, sha256 (đã kiểm 18/11/2026, tải trùng byte với bản xưởng dùng từ 11/10/2026)
    (1167, "mixkit_deep_urban_1167.mp3", "Deep Urban", "Eugenio Mininni", "tech",
     "a7f05a29d07a84d38072ccd2b35204bca812db86e75b2a837e71cc144d3e739b"),
    (136, "mixkit_autofahren_136.mp3", "Autofahren", "Mauro Urbina", "drive",
     "bb63977d73d7f4ba277f506831e762afc4032b48a0f9e5e5f3b17d66e41519cf"),
    (721, "mixkit_dub_techno_groove_721.mp3", "Dub Techno Groove", "—", "groove",
     "05d7c18d8d20983b539c079e9b2c98f235e9c7090640d9e51a65c0604bbc25a5"),
    (440, "mixkit_better_times_are_coming_440.mp3", "Better Times are Coming", "Alejandro Magaña (A. M.)", "warm",
     "b39a014450d406cfb5dc59dedb41823e44c0f9c89ca228c44b52ed63c8a39861"),
]
MOODS = {"tech": "công nghệ, đèn LED, thông số", "drive": "chạy xe, đi đêm, đường trường", "groove": "thi công, cận chi tiết, ASMR nhẹ",
         "warm": "tâm sự khách hàng, trước/sau, kết vui"}
EXT = (".mp3", ".wav", ".m4a", ".aac", ".flac")


def install():
    DL.mkdir(parents=True, exist_ok=True); rows = []
    for i, f, name, by, mood, sha in LIB:
        p = DL / f
        if not (p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == sha):
            print(f"tải nhạc Mixkit: {name}…", flush=True)
            b = urllib.request.urlopen(f"https://assets.mixkit.co/music/{i}/{i}.mp3", timeout=60).read()
            if hashlib.sha256(b).hexdigest() != sha: print(f"  bỏ qua {name}: file khác bản đã kiểm"); continue
            p.write_bytes(b)
        rows.append(f"| {f} | {name} | {by} | https://mixkit.co/free-stock-music/ (assets.mixkit.co/music/{i}) | "
                    f"Mixkit Stock Music Free License — online/quảng cáo online được, không TV/radio | mood: {mood} |")
    (DL / "SOURCES.md").write_text("# Nhạc tải về (giấy phép rõ ràng)\n\n| File | Bài | Tác giả | Nguồn | Giấy phép | Ghi chú |\n|---|---|---|---|---|---|\n"
                                   + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"OK: {len(rows)} bài trong {DL}")


def pick(mood="auto", key=""):
    """Trả (đường dẫn, mô tả) bài nhạc. Nhạc người dùng (assets/music ngoài _downloaded) thắng bộ mặc định."""
    own = sorted(p for p in (ROOT / "assets/music").rglob("*") if p.suffix.lower() in EXT and "_downloaded" not in p.parts)
    if own and mood in ("auto", "", None):
        p = own[int(hashlib.md5(key.encode()).hexdigest(), 16) % len(own)]; return p, f"nhạc của bạn: {p.name} (tự chịu giấy phép)"
    have = [x for x in LIB if (DL / x[1]).exists()]
    if not have:
        try: install(); have = [x for x in LIB if (DL / x[1]).exists()]
        except Exception as e: print("không tải được nhạc:", e)
    if not have: return None, "KHÔNG CÓ NHẠC (không tải được) — clip ra không nhạc nền, phải báo người dùng"
    cand = [x for x in have if x[4] == mood] or have
    x = cand[int(hashlib.md5(key.encode()).hexdigest(), 16) % len(cand)]
    return DL / x[1], f"{x[2]} — {x[3]} (Mixkit Free License, mood {x[4]})"


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if "--install" in sys.argv: install(); sys.exit()
    p, d = pick(a[0] if a else "auto", a[1] if len(a) > 1 else ""); print(p, "·", d)
    print("mood:", json.dumps(MOODS, ensure_ascii=False))
