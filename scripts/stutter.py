#!/usr/bin/env python3
"""Nghe lại lời thoại, tìm chỗ NÓI LẶP / NÓI LẠI / VẤP để cắt — giữ lại 1 lần nói duy nhất.

Dùng:
  <python> scripts/stutter.py <words.json> --audio <video|wav> [--out cuts.json] [--from a] [--to b]
  <python> scripts/stutter.py --check <bản_giao.mp4>      soát bản giao: tự nhận giọng + nghe sâu, phải ra 0 chỗ lặp (thoát mã 1 nếu còn)

VÌ SAO PHẢI "NGHE SÂU" (lỗi Corolla Cross v2, 18/11/2026): whisper nhận cả clip một lượt sẽ GỘP các lần nói lại thành một và
kéo dài 1 từ ~2 s để che (vd. "mặt@43,5 trời@45,3" thật ra là đọc lại cả câu "được phát triển … mặt trời"). Đọc transcript thường
sẽ không thấy lặp. Cách bắt:
  1. Dò từ bị kéo dài (> 0,55 s) hoặc khoảng hở giữa 2 từ (> 0,35 s) mà âm thanh vẫn có tiếng nói liên tục.
  2. Nhận giọng RIÊNG đoạn đó (không ngữ cảnh) → lộ ra các từ bị giấu → chèn vào chuỗi từ.
  3. Tìm trên chuỗi đã bổ sung:
     LẶP     từ/cụm nói liền nhau 2 lần ("cái cái", "được phát được phát triển")
     NÓI LẠI cụm ≥ 2 từ lặp lại sau vài từ nói hỏng ("theo em thì mức độ ưu, theo em thì việc này") → cắt từ lần đầu tới lần cuối
     VẤP     tiếng đệm "ờ/à/ừm" (whisper hay ghi "ờ…" thành "ở,"), từ cụt rồi ngừng
     NGỪNG   ngừng giữa câu > 0,6 s
  Luôn GIỮ LẦN NÓI CUỐI (người nói lặp lại để nói cho trọn). Lặp có chủ ý ("rất rất sáng") → tự giữ lại, không cắt.
Ra: bảng gợi ý + cuts.json [{kind, a, b, text, keep_text}] (giây nguồn) → SEGS "cuts"; mối cắt tự trám (build_template.py).
"""
import json, re, subprocess, sys, tempfile, unicodedata
from pathlib import Path
import numpy as np

if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
FILLERS = {"ờ", "ơ", "ừ", "ừm", "ưm", "à", "ạ", "hừm", "ờm", "ơm", "um", "uh", "ah", "eh"}
LIKE = {"ở", "ờ", "à", "ừ", "ơ", "ạ", "á", "ả"}            # whisper hay viết tiếng "ờ…" thành "ở," → nghi vấp khi có dấu ngắt + ngừng
EMPH = {"rất", "quá", "cực", "thật", "nhiều", "lắm", "từ", "dần", "từng", "mỗi"}   # lặp nhấn mạnh có chủ ý: "rất rất", "dần dần", "từng từng"?
HALLU = ("cảm ơn các bạn", "subscribe", "đăng ký kênh", "hẹn gặp lại")             # câu ảo whisper hay bịa ở đoạn ngắn
STRETCH, GAP, SR = 0.55, 0.35, 16000


def norm(w): return re.sub(r"[^\w]+", "", unicodedata.normalize("NFC", w.lower()))


def words_of(path, a=0, b=1e9):
    j = json.load(open(path, encoding="utf-8"))
    ws = [w for s in j["segments"] for w in s.get("words", [])]
    return [dict(w=w["w"], n=norm(w["w"]), s=float(w["s"]), e=float(w["e"])) for w in ws if a <= float(w["s"]) < b and norm(w["w"])]


def _audio(src):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32)


def _speechy(x, a, b, thr=-38):
    """Tỉ lệ khung 50 ms trong [a,b] có tiếng (RMS > thr dBFS so với đỉnh đoạn nói)."""
    seg = x[int(a * SR):int(b * SR)]; n = len(seg) // 800
    if n < 2: return 0.0
    r = 20 * np.log10(np.sqrt((seg[:n * 800].reshape(n, 800) ** 2).mean(1)) + 1e-9)
    ref = 20 * np.log10(np.abs(x).max() + 1e-9)
    return float((r > ref + thr).mean())


def deep_listen(ws, src, verbose=True):
    """Bước 1–2: tìm từ kéo dài / khoảng hở có tiếng, nhận giọng riêng đoạn đó, chèn từ bị giấu. Trả chuỗi từ đã bổ sung."""
    sys.path.insert(0, str(Path(__file__).resolve().parent)); import transcribe as T
    x = _audio(src); spans = []
    for i, w in enumerate(ws):
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        if w["e"] - w["s"] > STRETCH and _speechy(x, w["s"] + 0.25, w["e"]) > 0.6: spans.append((w["s"], nxt["s"] if nxt else w["e"]))
        elif nxt and nxt["s"] - w["e"] > GAP and _speechy(x, w["e"] + 0.05, nxt["s"] - 0.05) > 0.6: spans.append((w["s"], nxt["s"]))
    out = list(ws)
    with tempfile.TemporaryDirectory() as td:
        for a, b in spans:
            f = Path(td) / "s.wav"; pa = max(0, a - 0.12)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{pa:.3f}", "-t", f"{b - pa + 0.12:.3f}", "-i", str(src), "-vn", "-ac", "1",
                            "-ar", str(SR), str(f)], check=True)
            text, segs = T.run(str(f))
            if any(h in text.lower() for h in HALLU): continue
            hid = [dict(w=v["w"], n=norm(v["w"]), s=pa + v["s"], e=pa + v["e"], hidden=True) for s_ in segs for v in s_["words"]
                   if norm(v["w"]) and a - 0.05 <= pa + v["s"] < b - 0.02]
            old = [w for w in out if a - 0.05 <= w["s"] < b - 0.02]
            if len(hid) / max(b - a, 0.3) > 7.5: continue  # > 7,5 từ/s là whisper tự lặp ảo, không phải lời thật
            if len(hid) > len(old):                       # đoạn riêng nghe ra NHIỀU từ hơn → có lời bị giấu
                if verbose: print(f"  nghe sâu {a:7.2f}–{b:6.2f}: '{' '.join(w['w'] for w in old)}' → '{' '.join(w['w'] for w in hid)}'")
                out = [w for w in out if w not in old] + hid
    return sorted(out, key=lambda w: w["s"])


def find(ws):
    cuts, i, N = [], 0, len(ws)
    key = [w["n"] for w in ws]
    while i < N:
        hit = None
        for n in range(min(12, (N - i) // 2), 0, -1):     # cụm dài trước
            A = key[i:i + n]
            for g in range(0, 5 if n >= 2 else 1):        # g = số từ nói hỏng nằm giữa 2 lần (chỉ cụm ≥ 2 từ)
                k = i + n + g
                if k + n > N or key[k:k + n] != A or ws[k]["s"] - ws[i]["s"] > 8: continue
                if n == 1 and A[0] in EMPH: continue     # "rất rất", "dần dần": nhấn mạnh có chủ ý
                while k + n + n <= N and key[k + n:k + 2 * n] == A: k += n   # lặp nhiều lần: giữ lần cuối
                hit = dict(kind="LẶP" if g == 0 else "NÓI LẠI", a=ws[i]["s"] - 0.02, b=ws[k]["s"] - 0.03,
                           text=" ".join(w["w"] for w in ws[i:k]), keep_text=" ".join(w["w"] for w in ws[k:k + n]))
                break
            if hit: break
        if hit: cuts.append(hit); i = k; continue
        w = ws[i]; prv = ws[i - 1] if i else None; nxt = ws[i + 1] if i + 1 < N else None
        gap_b = w["s"] - prv["e"] if prv else 1; gap_a = nxt["s"] - w["e"] if nxt else 1
        if w["n"] in FILLERS and (gap_b > 0.12 or gap_a > 0.12):
            cuts.append(dict(kind="VẤP", a=max(w["s"] - 0.03, prv["e"] if prv else 0), b=min(w["e"] + 0.05, nxt["s"] if nxt else w["e"] + 0.05),
                             text=w["w"], keep_text=""))
        elif w["n"] in LIKE and re.search(r"[,.…]+$", w["w"]) and (gap_a > 0.15 or not nxt):
            cuts.append(dict(kind="VẤP?", a=max(w["s"] - 0.03, prv["e"] if prv else 0), b=(nxt["s"] - 0.05) if nxt else w["e"],
                             text=f"{w['w']} (nghi tiếng đệm 'ờ/à', nghe lại)", keep_text=""))
        elif nxt and w["e"] - w["s"] < 0.12 and gap_a > 0.25 and len(w["n"]) <= 3:
            cuts.append(dict(kind="VẤP?", a=w["s"] - 0.02, b=nxt["s"] - 0.03, text=w["w"] + " … (từ cụt rồi ngừng)", keep_text=""))
        elif nxt and gap_a > 0.6:
            cuts.append(dict(kind="NGỪNG", a=w["e"] + 0.12, b=nxt["s"] - 0.12, text=f"ngừng {gap_a:.2f}s sau '{w['w']}'", keep_text=""))
        i += 1
    cuts = sorted((c for c in cuts if c["b"] - c["a"] > 0.04), key=lambda c: c["a"]); merged = []
    for c in cuts:                                        # các lần nói lại nối nhau (đọc 3 lần) → gộp 1 khúc cắt, giữ lần cuối
        if merged and c["a"] <= merged[-1]["b"] + 0.05 and c["kind"] in ("LẶP", "NÓI LẠI") and merged[-1]["kind"] in ("LẶP", "NÓI LẠI"):
            m = merged[-1]; m["b"] = max(m["b"], c["b"]); m["text"] += " | " + c["text"]; m["keep_text"] = c["keep_text"]; m["kind"] = "NÓI LẠI"
        else: merged.append(dict(c))
    return merged


def report(cuts):
    for c in cuts:
        print(f"  {c['kind']:7s} {c['a']:7.2f} – {c['b']:7.2f}  cắt: {c['text']}" + (f"   → giữ: {c['keep_text']}" if c["keep_text"] else ""))
    rep = [c for c in cuts if c["kind"] in ("LẶP", "NÓI LẠI")]
    print(f"== {len(cuts)} chỗ ({len(rep)} lặp/nói lại, {sum(c['kind'].startswith('VẤP') for c in cuts)} vấp, "
          f"{sum(c['kind'] == 'NGỪNG' for c in cuts)} ngừng dài).")
    return rep


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args: raise SystemExit(__doc__)
    opt = lambda k, d: args[args.index(k) + 1] if k in args else d
    if "--check" in args:                                 # soát bản giao: nhận giọng cả file rồi nghe sâu
        src = opt("--check", None); sys.path.insert(0, str(Path(__file__).resolve().parent)); import transcribe as T
        with tempfile.TemporaryDirectory() as td:
            j = Path(td) / "w.json"; T.tx(src, str(j)); ws = deep_listen(words_of(j), src)
        rep = report(find(ws))
        print("SOÁT BẢN GIAO:", "ĐẠT — không còn lặp/nói lại." if not rep else f"CHƯA ĐẠT — còn {len(rep)} chỗ lặp/nói lại, sửa cuts rồi xuất lại.")
        sys.exit(1 if rep else 0)
    ws = words_of(args[0], float(opt("--from", 0)), float(opt("--to", 1e9)))
    if "--audio" in args: ws = deep_listen(ws, opt("--audio", None))
    else: print("(chưa nghe sâu: thêm --audio <file nguồn> — whisper hay giấu chỗ nói lại)")
    cuts = find(ws); report(cuts); print("Nghe lại từng chỗ trước khi chốt.")
    if "--out" in args: json.dump(cuts, open(opt("--out", None), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
