"""Langkah 4: rakit video Reel 1080x1920 -> runs/<seri>-epNN/final.mp4

- Tiap adegan: gambar dengan gerak kamera pelan (zoom/geser, bergantian arah), transisi silang antar adegan.
- Subtitle besar per 3–4 kata dengan kata yang sedang diucapkan disorot kuning (zona aman Reels: di atas UI bawah).
- Judul seri di awal, kartu "Part berikutnya" di akhir.
- Narasi + lagu latar (Kevin MacLeod, CC BY 4.0) yang otomatis mengecil saat narator bicara.

    python pipeline/render.py naruto 1
"""
import json
import random
import sys

from common import *

W, H, FPS = 1080, 1920, 30
FADE = 0.35
SUB_FONT = "Bangers"
TAIL = 1.5  # detik setelah narasi terakhir


def ass_time(t):
    t = max(0.0, t)
    h, m = int(t // 3600), int(t % 3600 // 60)
    return f"{h}:{m:02}:{t % 60:05.2f}"


def ass_escape(s):
    return s.replace("\\", "").replace("{", "(").replace("}", ")")


def build_ass(series, sc, tts, path, total):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{SUB_FONT},150,&H00FFFFFF,&H00FFFFFF,&H00141414,&H64000000,0,0,0,0,100,100,1,0,1,9,4,2,70,70,560,1
Style: Title,{SUB_FONT},250,&H0000E1FF,&H00FFFFFF,&H00141414,&H64000000,0,0,0,0,100,100,2,0,1,9,4,8,60,60,250,1
Style: Part,{SUB_FONT},130,&H00FFFFFF,&H00FFFFFF,&H00141414,&H64000000,0,0,0,0,100,100,2,0,1,9,4,8,60,60,470,1
Style: Label,{SUB_FONT},90,&H00FFFFFF,&H00FFFFFF,&H00141414,&H64000000,0,0,0,0,100,100,2,0,1,7,3,8,90,230,250,1
Style: Hook,{SUB_FONT},165,&H0000E1FF,&H00FFFFFF,&H00141414,&H64000000,0,0,0,0,100,100,1,0,1,10,5,8,90,230,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    # judul seri (awal) & kartu part berikutnya (akhir)
    fade = r"{\fad(250,250)}"
    hook = (sc.get("hook_layar") or "").strip()
    if hook:  # hook di layar sejak frame pertama (tanpa fade masuk); judul seri jadi label kecil di atasnya
        until = max(3.5, min(5.0, tts["scenes"][0]["dur"] + 0.3))
        out = r"{\fad(0,250)}"
        ev.append(f"Dialogue: 1,{ass_time(0)},{ass_time(until)},Label,,0,0,0,,{out}"
                  f"{ass_escape(series['title']).upper()} · PART {sc['ep']}")
        ev.append(f"Dialogue: 1,{ass_time(0)},{ass_time(until)},Hook,,0,0,0,,{out}{ass_escape(hook).upper()}")
    else:  # naskah lama tanpa hook_layar
        ev.append(f"Dialogue: 1,{ass_time(0.2)},{ass_time(3.8)},Title,,0,0,0,,{fade}{ass_escape(series['title'])}")
        ev.append(f"Dialogue: 1,{ass_time(0.2)},{ass_time(3.8)},Part,,0,0,0,,{fade}DALAM 200 DETIK - PART {sc['ep']}")
    nxt = next((e.get("next") for e in series["episodes"] if e["ep"] == sc["ep"]), None)
    if nxt:
        t0 = max(0.0, total - 6.0)
        ev.append(f"Dialogue: 1,{ass_time(t0)},{ass_time(total)},Part,,0,0,0,,{fade}PART {sc['ep'] + 1}:\\N"
                  f"{ass_escape(nxt.upper())}")
    hl = r"{\c&H0000E5FF&\fscx108\fscy108}"
    norm = r"{\c&H00FFFFFF&\fscx100\fscy100}"
    for s in tts["scenes"]:
        words = s["words"]
        chunks, cur = [], []
        for w in words:  # potong per 3 kata / ±16 huruf, atau setelah tanda baca
            cur.append(w)
            text_len = sum(len(x[2]) + 1 for x in cur)
            if len(cur) >= 3 or text_len > 16 or w[2][-1:] in ".,!?;:":
                chunks.append(cur)
                cur = []
        if cur:
            chunks.append(cur)
        for ci, ch in enumerate(chunks):
            chunk_end = (chunks[ci + 1][0][0] if ci + 1 < len(chunks) else s["dur"] + 0.2)
            for wi, w in enumerate(ch):
                st = s["start"] + w[0]
                en = s["start"] + (ch[wi + 1][0] if wi + 1 < len(ch) else chunk_end)
                txt = " ".join((hl + ass_escape(x[2]).upper() + norm) if k == wi else ass_escape(x[2]).upper()
                               for k, x in enumerate(ch))
                ev.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Sub,,0,0,0,,{txt}")
    Path(path).write_text(head + "\n".join(ev) + "\n")


def segment(img, seconds, out, seed):
    """Gambar diam -> klip dengan zoom/geser pelan (Ken Burns)."""
    rnd = random.Random(seed)
    frames = max(1, round(seconds * FPS))
    zin = rnd.random() < 0.6
    z0, z1 = (1.0, 1.10) if zin else (1.10, 1.0)
    dx, dy = rnd.choice([(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)])
    z = f"{z0}+({z1}-{z0})*on/{frames}"
    x = f"(iw-iw/zoom)/2+{dx}*(iw-iw/zoom)/2*(on/{frames}-0.5)"
    y = f"(ih-ih/zoom)/2+{dy}*(ih-ih/zoom)/2*(on/{frames}-0.5)"
    vf = (f"scale={int(W * 1.5)}:{int(H * 1.5)}:force_original_aspect_ratio=increase,"
          f"crop={int(W * 1.5)}:{int(H * 1.5)},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},"
          "format=yuv420p")
    ffmpeg("-loop", "1", "-i", img, "-vf", vf, "-frames:v", frames, "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "20", "-threads", "4", out)


FILLER_TAGS = {"reels", "reelsinstagram", "fyp", "foryou", "foryoupage", "viral", "viralreels", "explore",
               "explorepage", "trending", "otaku", "instagood"}


def hashtags(tags, limit=5):
    """Maks. 5 tag spesifik (batas Instagram sejak Des 2025; tag generik tidak menambah jangkauan)."""
    out = []
    for h in tags:
        h = h.lstrip("#").replace(" ", "")
        if h and h.lower() not in FILLER_TAGS and h.lower() not in {o.lower() for o in out}:
            out.append(h)
    return ["#" + h for h in out[:limit]]


def pick_music(mood, seed):
    tracks = [t for t in load(MUSIC / "tracks.json")["tracks"] if t["mood"] == mood] or load(MUSIC / "tracks.json")["tracks"]
    return random.Random(seed).choice(tracks)


def main(series_key, ep):
    s = load(SERIES / f"{series_key}.json")
    d = run_dir(series_key, ep)
    sc, tts = load(d / "script.json"), load(d / "tts.json")
    scenes = tts["scenes"]
    n = len(scenes)
    total = scenes[-1]["start"] + scenes[-1]["dur"] + TAIL
    seg_dir = d / "seg"
    seg_dir.mkdir(exist_ok=True)
    # durasi slot tiap adegan = sampai adegan berikutnya mulai (narasi + jeda); klip diberi lebih FADE untuk transisi
    slots = [(scenes[i + 1]["start"] - scenes[i]["start"]) if i + 1 < n else (total - scenes[i]["start"])
             for i in range(n)]
    for i in range(n):
        out = seg_dir / f"{i + 1:02}.mp4"
        img = d / "img" / f"{i + 1:02}.jpg"
        if not img.exists():
            sys.exit(f"gambar adegan {i + 1} belum ada")
        if not out.exists():
            segment(img, slots[i] + (FADE if i + 1 < n else 0), out, f"{series_key}{ep}{i}")
    log(f"{n} klip adegan siap, total {total:.1f} detik")

    build_ass(s, sc, tts, d / "subs.ass", total)
    track = pick_music(s.get("music_mood", "seru"), f"{series_key}{ep}")
    inputs, parts = [], []
    for i in range(n):
        inputs += ["-i", seg_dir / f"{i + 1:02}.mp4"]
    last, offset = "0:v", 0.0
    for i in range(1, n):
        offset += slots[i - 1]
        parts.append(f"[{last}][{i}:v]xfade=transition=fade:duration={FADE}:offset={offset - FADE / 2:.3f}[x{i}]")
        last = f"x{i}"
    fonts = str(FONTS).replace(":", r"\:")
    parts.append(f"[{last}]ass={d / 'subs.ass'}:fontsdir={fonts}[vout]")
    # narasi: tiap adegan ditempatkan di waktu mulainya
    for i, sc_ in enumerate(scenes):
        inputs += ["-i", sc_["file"]]
        ms = int(sc_["start"] * 1000)
        parts.append(f"[{n + i}:a]adelay={ms}|{ms},aformat=sample_rates=44100:channel_layouts=stereo[n{i}]")
    parts.append("".join(f"[n{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0:dropout_transition=0,"
                 f"apad=whole_dur={total:.2f},asplit=2[voice][key]")
    inputs += ["-stream_loop", "-1", "-i", MUSIC / track["file"]]
    parts.append(f"[{2 * n}:a]atrim=0:{total:.2f},asetpts=N/SR/TB,volume=0.22,afade=t=in:d=1,"
                 f"afade=t=out:st={total - 2.5:.2f}:d=2.5,aformat=sample_rates=44100:channel_layouts=stereo[mus]")
    parts.append("[mus][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck]")
    parts.append("[voice][duck]amix=inputs=2:normalize=0,alimiter=limit=0.95[aout]")
    ffmpeg(*inputs, "-filter_complex", ";".join(parts), "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.2f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-r", FPS, "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", d / "final.mp4")
    credit = f'Musik: "{track["title"]}" - Kevin MacLeod (incompetech.com), CC BY 4.0'
    caption = f"{sc['judul']}\n\n{sc['caption']}\n\n🎵 {credit}\n\n" + " ".join(hashtags(sc.get("hashtags", [])))
    (d / "caption.txt").write_text(caption)
    log(f"selesai: {d / 'final.mp4'} ({ffprobe_seconds(d / 'final.mp4'):.1f} detik), caption: {d / 'caption.txt'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
