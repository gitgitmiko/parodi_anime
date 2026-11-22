"""Langkah 1: naskah episode (narasi serius + analisis bahasa Indonesia + deskripsi visual per adegan) -> runs/<seri>-epNN/script.json

    python pipeline/script.py naruto 1
"""
import json
import sys

from common import *

SYS = """Kamu penulis naskah seri ringkasan anime yang serius untuk Reels Facebook/Instagram berbahasa Indonesia:
"{series_name}". Setiap part ±200 detik menceritakan ulang bagian cerita asli dengan nada dramatis ala dokumenter,
setia pada alur dan momen ikoniknya, lalu menambahkan nilai yang tidak ada di tontonan aslinya: analisis singkat
tentang motivasi tokoh, makna/tema di balik momen, lore dunia ceritanya, dan petunjuk (foreshadowing) ke cerita
selanjutnya. Narator bercerita (bukan dialog panjang); boleh kutipan pendek tokoh.

Aturan narasi:
- Nada serius, hangat, dan menghormati cerita. TANPA lelucon, plesetan, komentar jenaka, atau humor lokal.
  Momen yang di cerita aslinya konyol tetap boleh disebut, tetapi ceritakan apa adanya dan fokus pada maknanya.
- Total 450–480 kata (±200 detik dibacakan). 18–22 adegan, tiap adegan 18–30 kata.
- Sisipkan 3–4 kalimat analisis di sela alur (mis. "Di sinilah terlihat bahwa...", "Yang jarang disadari...",
  "Momen ini penting karena..."), jangan dikumpulkan di akhir dan jangan mengulang frasa pembuka yang sama.
- Adegan 1 = HOOK 3 detik: pertanyaan atau fakta paling menggugah dari episode ini (bukan salam, bukan judul).
- "hook_layar" = teks besar di layar pada detik pertama (kebanyakan orang menonton tanpa suara): maks. 6 kata,
  janji yang sama dengan adegan 1, nada serius (contoh: "KEMATIAN YANG MENGUBAH SEGALANYA").
- Adegan terakhir = cliffhanger + ajakan: sebut part berikutnya "{next}" dan ajak follow agar tidak ketinggalan.
- Bahasa lisan yang enak dibacakan suara TTS: kalimat pendek, tanpa emoji, tanpa singkatan aneh, angka ditulis kata.
- Jangan menyalin dialog/terjemahan resmi panjang; ceritakan dengan kata-katamu sendiri.

Aturan visual (untuk generator gambar, bahasa Inggris):
- Satu adegan = satu gambar diam yang jelas, fokus pada 1–3 tokoh, ekspresi dan pose serius/emosional,
  sebut sudut kamera dan pencahayaan singkat.
- JANGAN tulis nama tokoh atau judul anime. Rujuk tokoh HANYA dengan kunci di kurung kurawal dari daftar ini:
  {chars}. Tokoh lain: deskripsikan secara umum.
- Sebut latar dan suasana singkat. Jangan minta teks/tulisan di gambar.

Balas HANYA JSON:
{{"judul": "...", "hook_layar": "...", "caption": "caption Facebook 2-3 kalimat serius yang memancing rasa penasaran + satu ajakan follow",
  "hashtags": ["maks. 5 tag spesifik: anime, tokoh/momen episode, seri; tanpa tag generik seperti Reels/fyp/viral"],
  "adegan": [{{"narasi": "...", "visual": "...", "tokoh": ["kunci", ...], "suasana": "normal|tegang|kaget|sedih|semangat"}}]}}"""


def main(series_key, ep):
    s = load(SERIES / f"{series_key}.json")
    e = next(x for x in s["episodes"] if x["ep"] == int(ep))
    d = run_dir(series_key, ep)
    sys_prompt = SYS.format(series_name=s["series_name"], next=e.get("next") or "berikutnya",
                            chars=", ".join("{" + k + "}" for k in s["characters"]))
    user = (f"Anime: {s['title']}\nPart {e['ep']}: {e['title']}\nMomen yang wajib ada (urut): {e['beats']}\n"
            f"Part berikutnya: {e.get('next')}")
    out = claude_json("sonnet", sys_prompt, user)
    for a in out["adegan"]:  # model kadang menulis kunci tokoh dengan kurung kurawal: "{naruto}"
        a["tokoh"] = [k.strip("{} ") for k in a.get("tokoh", [])]
    words = sum(len(a["narasi"].split()) for a in out["adegan"])
    bad = [k for a in out["adegan"] for k in a.get("tokoh", []) if k not in s["characters"]]
    hook_words = len(out.get("hook_layar", "").split())
    if hook_words > 6:
        log(f"hook_layar {hook_words} kata (> 6): {out['hook_layar']}")
    log(f"naskah: {len(out['adegan'])} adegan, {words} kata" + (f", kunci tokoh tak dikenal: {set(bad)}" if bad else ""))
    out.update(series=series_key, ep=int(ep), part_title=e["title"])
    save(d / "script.json", out)
    return out


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
