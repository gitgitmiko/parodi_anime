"""Langkah 1: naskah episode (narasi lucu bahasa Indonesia + deskripsi visual per adegan) -> runs/<seri>-epNN/script.json

    python pipeline/script.py naruto 1
"""
import json
import sys

from common import *

SYS = """Kamu penulis naskah seri parodi anime untuk Reels Facebook/Instagram berbahasa Indonesia: "{series_name}".
Setiap part ±200 detik meringkas bagian cerita asli dengan narasi lucu, santai, dan penuh komentar jenaka khas
anak muda Indonesia (boleh humor lokal: antre BPJS, emak-emak, tukang parkir, ujian sekolah, dsb.), tetapi alur dan
momen ikoniknya tetap setia pada cerita asli. Narator bercerita (bukan dialog panjang); boleh kutipan pendek tokoh.

Aturan narasi:
- Total 430–480 kata (±200 detik dibacakan). 18–22 adegan, tiap adegan 15–30 kata.
- Adegan 1 = HOOK 3 detik: kalimat paling bikin penasaran/lucu dari episode ini (bukan salam, bukan judul).
- Adegan terakhir = cliffhanger + ajakan: sebut part berikutnya "{next}" dan ajak follow agar tidak ketinggalan.
- Bahasa lisan yang enak dibacakan suara TTS: kalimat pendek, tanpa emoji, tanpa singkatan aneh, angka ditulis kata.
- Jangan menyalin dialog/terjemahan resmi panjang; ceritakan dengan kata-katamu sendiri.

Aturan visual (untuk generator gambar, bahasa Inggris):
- Satu adegan = satu gambar diam yang jelas, fokus pada 1–3 tokoh, aksi/ekspresi lucu yang berlebihan.
- JANGAN tulis nama tokoh atau judul anime. Rujuk tokoh HANYA dengan kunci di kurung kurawal dari daftar ini:
  {chars}. Tokoh lain: deskripsikan secara umum.
- Sebut latar dan suasana singkat. Jangan minta teks/tulisan di gambar.

Balas HANYA JSON:
{{"judul": "...", "caption": "caption Facebook 2-3 kalimat lucu + ajakan follow", "hashtags": ["..."],
  "adegan": [{{"narasi": "...", "visual": "...", "tokoh": ["kunci", ...], "suasana": "normal|lucu|tegang|kaget|sedih|semangat"}}]}}"""


def main(series_key, ep):
    s = load(SERIES / f"{series_key}.json")
    e = next(x for x in s["episodes"] if x["ep"] == int(ep))
    d = run_dir(series_key, ep)
    sys_prompt = SYS.format(series_name=s["series_name"], next=e.get("next") or "berikutnya",
                            chars=", ".join("{" + k + "}" for k in s["characters"]))
    user = (f"Anime: {s['title']}\nPart {e['ep']}: {e['title']}\nMomen yang wajib ada (urut): {e['beats']}\n"
            f"Part berikutnya: {e.get('next')}")
    out = claude_json("sonnet", sys_prompt, user)
    words = sum(len(a["narasi"].split()) for a in out["adegan"])
    bad = [k for a in out["adegan"] for k in a.get("tokoh", []) if k not in s["characters"]]
    log(f"naskah: {len(out['adegan'])} adegan, {words} kata" + (f", kunci tokoh tak dikenal: {set(bad)}" if bad else ""))
    out.update(series=series_key, ep=int(ep), part_title=e["title"])
    save(d / "script.json", out)
    return out


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
