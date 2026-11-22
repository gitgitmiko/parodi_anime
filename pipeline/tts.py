"""Langkah 3: narasi per adegan dengan edge-tts (suara Ardi) + waktu tiap kata -> runs/<seri>-epNN/audio/NN.mp3, tts.json

edge-tts tidak punya gaya bicara untuk bahasa Indonesia, jadi suasana adegan dibawakan lewat tempo, nada, dan volume.

    python pipeline/tts.py naruto 1
"""
import asyncio
import re
import sys

import edge_tts

from common import *

VOICE = "id-ID-ArdiNeural"
# suasana -> (rate, pitch, volume)
DELIVERY = {  # tempo sedikit dipercepat agar ±420 kata muat ±200 detik, tetap tenang untuk narasi serius
    "normal": ("+10%", "+0Hz", "+0%"),
    "semangat": ("+16%", "+2Hz", "+6%"),
    "tegang": ("+6%", "-3Hz", "-2%"),
    "kaget": ("+14%", "+2Hz", "+6%"),
    "sedih": ("+0%", "-4Hz", "-6%"),
}
# Kata asing/istilah yang salah dibaca suara Indonesia; hanya suara yang melihat ejaan ini, subtitle tetap asli.
SAY = {"Kyuubi": "Kyubi", "Hokage": "Hokage", "Konoha": "Konoha", "Kage Bunshin": "Kage Bunsyin", "kunai": "kunai",
       "Iruka": "Iruka", "Mizuki": "Mizuki", "Minato": "Minato", "Sasuke": "Saske", "shuriken": "syuriken",
       "Kakashi": "Kakasyi"}
GAP = 0.25  # jeda antar adegan (detik)


def spoken(text):
    for w, say in sorted(SAY.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(rf"(?<!\w){re.escape(w)}(?!\w)", say, text)
    return text


async def synth(text, mood, path):
    rate, pitch, volume = DELIVERY.get(mood, DELIVERY["normal"])
    com = edge_tts.Communicate(spoken(text), VOICE, rate=rate, pitch=pitch, volume=volume, boundary="WordBoundary")
    words = []
    with open(path, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append([round(start, 3), round(start + chunk["duration"] / 1e7, 3), chunk["text"]])
    return words


def align_written(written, spoken_words):
    """Subtitle memakai kata tertulis (bukan ejaan suara): petakan per indeks bila jumlah kata sama."""
    w = written.split()
    if len(w) == len(spoken_words):
        return [[a, b, t] for (a, b, _), t in zip(spoken_words, w)]
    return spoken_words


def main(series_key, ep):
    d = run_dir(series_key, ep)
    sc = load(d / "script.json")
    out_dir = d / "audio"
    out_dir.mkdir(exist_ok=True)
    scenes, t = [], 0.0
    for i, a in enumerate(sc["adegan"], 1):
        path = out_dir / f"{i:02}.mp3"
        words = asyncio.run(synth(a["narasi"], a.get("suasana", "normal"), path))
        dur = ffprobe_seconds(path)
        scenes.append({"file": str(path), "start": round(t, 3), "dur": round(dur, 3),
                       "words": align_written(a["narasi"], words)})
        t += dur + GAP
    save(d / "tts.json", {"scenes": scenes, "total": round(t, 2)})
    log(f"narasi {len(scenes)} adegan, total {t:.1f} detik")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
