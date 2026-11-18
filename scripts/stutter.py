#!/usr/bin/env python3
"""Nghe lại transcript, tìm chỗ NÓI LẶP và chỗ VẤP để cắt — giữ lại 1 lần nói duy nhất.

Dùng:  <python> scripts/stutter.py <words.json> [--out cuts.json] [--from a] [--to b]
Tìm:
  LẶP  cùng một từ/cụm 1–4 từ nói liền nhau ("cái cái đèn", "nó sáng nó sáng") → cắt các lần đầu, GIỮ LẦN CUỐI
       (người nói thường lặp lại để sửa/nói trọn). Cắt từ đầu lần thứ nhất tới đầu lần giữ.
  VẤP  từ đệm đứng riêng ("ờ", "ơ", "ừm", "à" có ngắt quãng hai bên), nói hỏng nửa chừng rồi nói lại (từ cụt < 0,12 s trước khoảng ngừng),
       khoảng ngừng giữa câu > 0,6 s.
Ra:    bảng gợi ý in màn hình + cuts.json [{kind, a, b, text, keep_text}] (giây nguồn).
Dùng kết quả: E.keep_minus(keep, cuts) bỏ các khúc này khỏi keep của đoạn; mỗi mối cắt nằm TRONG cảnh quay người nói
  phải được trám bằng insert/animation (E.joins + SEGS["covers"], xem build_template.py). Gợi ý chỉ là gợi ý:
  nghe lại từng chỗ (cắt -ss/-t rồi nhận giọng lại) trước khi chốt; câu lặp có chủ ý ("rất rất sáng") thì giữ.
"""
import json, re, sys, unicodedata

if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
LIKE = {"ở", "ờ", "à", "ừ", "ơ", "ạ", "á", "ả", "ấy", "thì", "là"}   # whisper hay viết tiếng "ờ…" thành "ở," → nghi vấp khi có dấu ngắt + ngừng
FILLERS = {"ờ", "ơ", "ừ", "ừm", "ưm", "ừ m", "à", "ạ", "hừm", "ờm", "ơm", "um", "uh", "ah", "eh"}


def norm(w):
    w = unicodedata.normalize("NFC", w.lower())
    return re.sub(r"[^\w]+", "", w)


def words_of(path, a=0, b=1e9):
    j = json.load(open(path, encoding="utf-8"))
    ws = [w for s in j["segments"] for w in s.get("words", [])]
    return [dict(w=w["w"], n=norm(w["w"]), s=float(w["s"]), e=float(w["e"])) for w in ws if a <= float(w["s"]) < b and norm(w["w"])]


def find(ws):
    cuts, i, N = [], 0, len(ws)
    while i < N:
        hit = None
        for n in (4, 3, 2, 1):                             # cụm dài trước
            if i + 2 * n > N: continue
            A, B = [w["n"] for w in ws[i:i + n]], [w["n"] for w in ws[i + n:i + 2 * n]]
            if A == B and ws[i + n]["s"] - ws[i + n - 1]["e"] < 1.2:
                k = i + n                                  # có thể lặp nhiều lần: tìm lần cuối
                while k + n <= N - n and [w["n"] for w in ws[k + n:k + 2 * n]] == A: k += n
                hit = dict(kind="LẶP", a=ws[i]["s"], b=ws[k]["s"] - 0.02, text=" ".join(w["w"] for w in ws[i:k]),
                           keep_text=" ".join(w["w"] for w in ws[k:k + n]))
                i = k; break
        if hit: cuts.append(hit); continue
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
    return [c for c in cuts if c["b"] - c["a"] > 0.04]


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args: raise SystemExit(__doc__)
    opt = lambda k, d: float(args[args.index(k) + 1]) if k in args else d
    out = args[args.index("--out") + 1] if "--out" in args else None
    cuts = find(words_of(args[0], opt("--from", 0), opt("--to", 1e9)))
    for c in cuts:
        print(f"  {c['kind']:6s} {c['a']:7.2f} – {c['b']:7.2f}  cắt: {c['text']}" + (f"   → giữ: {c['keep_text']}" if c["keep_text"] else ""))
    print(f"== {len(cuts)} chỗ gợi ý cắt ({sum(c['kind'] == 'LẶP' for c in cuts)} lặp, "
          f"{sum(c['kind'].startswith('VẤP') for c in cuts)} vấp, {sum(c['kind'] == 'NGỪNG' for c in cuts)} ngừng dài). Nghe lại từng chỗ trước khi chốt.")
    if out: json.dump(cuts, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
