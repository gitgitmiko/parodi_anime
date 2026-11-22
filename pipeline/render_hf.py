"""Uji coba: versi HyperFrames dari sebuah episode -> runs/<seri>-epNN/hf/final-hf.mp4

Memakai ulang gambar, klip adegan (seg/), narasi, dan lagu dari render biasa; final.mp4 tidak disentuh.
Video dasar dirakit tanpa subtitle (ffmpeg), lalu lapisan animasi dibuat sebagai HTML dan dirender HyperFrames:

- Hook: kata demi kata menghentak masuk di detik pertama, label seri/part di atasnya.
- Caption kinetik: potongan 2-3 kata muncul dengan efek "pop", kata yang diucapkan membesar & kuning.
- Progress bar di atas, label part kecil sepanjang video.
- Penutup: kartu part berikutnya + ajakan follow yang berdenyut.

    python pipeline/render_hf.py naruto 12            # rakit + render
    python pipeline/render_hf.py naruto 12 --no-render
"""
import html
import json
import shutil
import subprocess
import sys

from common import *
from render import FADE, FPS, TAIL, H, W, pick_music

HF = "hyperframes@0.9.79"
HOOK_MIN, HOOK_MAX = 3.5, 5.0
END_CARD = 6.0


def build_base(series_key, ep, s, d, tts, out):
    """Video adegan + audio campuran yang sama dengan render.py, tanpa subtitle."""
    scenes = tts["scenes"]
    n = len(scenes)
    total = scenes[-1]["start"] + scenes[-1]["dur"] + TAIL
    slots = [(scenes[i + 1]["start"] - scenes[i]["start"]) if i + 1 < n else (total - scenes[i]["start"])
             for i in range(n)]
    seg = d / "seg"
    for i in range(n):
        if not (seg / f"{i + 1:02}.mp4").exists():
            sys.exit(f"klip adegan {i + 1} belum ada; jalankan render.py dulu")
    track = pick_music(s.get("music_mood", "seru"), f"{series_key}{ep}")
    inputs, parts = [], []
    for i in range(n):
        inputs += ["-i", seg / f"{i + 1:02}.mp4"]
    last, offset = "0:v", 0.0
    for i in range(1, n):
        offset += slots[i - 1]
        parts.append(f"[{last}][{i}:v]xfade=transition=fade:duration={FADE}:offset={offset - FADE / 2:.3f}[x{i}]")
        last = f"x{i}"
    parts.append(f"[{last}]null[vout]")
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
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-r", FPS,
           "-c:a", "aac", "-b:a", "192k", out)
    return total


def chunks_of(words):
    """Potong per 2-3 kata (atau setelah tanda baca) supaya tiap potongan cepat dibaca."""
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 3 or sum(len(x[2]) + 1 for x in cur) > 15 or w[2][-1:] in ".,!?;:":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def esc(t):
    return html.escape(t.upper())


def build_html(s, sc, tts, total):
    scenes = tts["scenes"]
    hook = (sc.get("hook_layar") or "").strip()
    hook_end = max(HOOK_MIN, min(HOOK_MAX, scenes[0]["dur"] + 0.3)) if hook else 0.0
    nxt = next((e.get("next") for e in s["episodes"] if e["ep"] == sc["ep"]), None)
    end_t0 = max(0.0, total - END_CARD) if nxt else total

    caps, tl = [], []
    cid = 0
    for scn in scenes:
        chs = chunks_of(scn["words"])
        for ci, ch in enumerate(chs):
            st = scn["start"] + ch[0][0]
            en = scn["start"] + (chs[ci + 1][0][0] if ci + 1 < len(chs) else min(scn["dur"] + 0.15, ch[-1][1] + 0.35))
            if en <= hook_end or st >= end_t0:  # hook & kartu penutup sudah menampilkan teksnya sendiri
                continue
            st = max(st, hook_end)
            spans = "".join(
                f'<span class="w" id="w{cid}_{k}">{esc(w[2])}<span class="hl">{esc(w[2])}</span></span> '
                for k, w in enumerate(ch))
            caps.append(f'<div class="cap" id="c{cid}">{spans.strip()}</div>')
            tl.append(f'tl.set("#c{cid}",{{autoAlpha:1}},{st:.3f});'
                      f'tl.fromTo("#c{cid}",{{scale:.72,y:28}},{{scale:1,y:0,duration:.16,ease:"back.out(2.6)"}},{st:.3f});')
            for k, w in enumerate(ch):
                ws = max(st, scn["start"] + w[0])
                we = scn["start"] + (ch[k + 1][0] if k + 1 < len(ch) else w[1])
                off = max(ws + .08, we - .02)
                tl.append(f'tl.to("#w{cid}_{k} .hl",{{opacity:1,duration:.05}},{ws:.3f});'
                          f'tl.to("#w{cid}_{k}",{{scale:1.14,duration:.08,ease:"power2.out"}},{ws:.3f});'
                          f'tl.to("#w{cid}_{k}",{{scale:1,duration:.12}},{off:.3f});'
                          f'tl.to("#w{cid}_{k} .hl",{{opacity:0,duration:.08}},{off:.3f});')
            tl.append(f'tl.set("#c{cid}",{{autoAlpha:0}},{en:.3f});')
            cid += 1

    hook_words = "".join(f'<span class="hw" id="hw{i}">{esc(w)}</span> ' for i, w in enumerate(hook.split()))
    hook_tl = ""
    if hook:
        n_hw = len(hook.split())
        step = min(0.14, 1.6 / max(1, n_hw))
        hook_tl = (
            'tl.fromTo("#label",{autoAlpha:0,y:-30},{autoAlpha:1,y:0,duration:.3,ease:"power3.out"},0);'
            + "".join(f'tl.fromTo("#hw{i}",{{autoAlpha:0,scale:1.9,rotation:{(-4 if i % 2 else 4)}}},'
                      f'{{autoAlpha:1,scale:1,rotation:0,duration:.22,ease:"back.out(2)"}},{0.05 + i * step:.3f});'
                      for i in range(n_hw))
            + f'tl.fromTo("#hookbox",{{x:-6}},{{x:6,duration:.05,repeat:5,yoyo:true}},{0.05 + n_hw * step:.3f});'
            + f'tl.to("#hook",{{autoAlpha:0,scale:.92,duration:.25}},{hook_end - .25:.3f});'
            + f'tl.to("#label",{{autoAlpha:0,duration:.25}},{hook_end - .25:.3f});'
        )
    end_tl = ""
    if nxt:
        end_tl = (
            f'tl.fromTo("#endshade",{{autoAlpha:0}},{{autoAlpha:1,duration:.4}},{end_t0:.3f});'
            f'tl.fromTo("#endpart",{{autoAlpha:0,y:60}},{{autoAlpha:1,y:0,duration:.35,ease:"back.out(1.8)"}},{end_t0 + .15:.3f});'
            f'tl.fromTo("#endtitle",{{autoAlpha:0,y:60}},{{autoAlpha:1,y:0,duration:.35,ease:"back.out(1.8)"}},{end_t0 + .35:.3f});'
            f'tl.fromTo("#follow",{{autoAlpha:0,scale:.6}},{{autoAlpha:1,scale:1,duration:.35,ease:"back.out(2.4)"}},{end_t0 + .9:.3f});'
            f'tl.to("#follow",{{scale:1.08,duration:.45,repeat:{int((END_CARD - 1.4) / .45)},yoyo:true,ease:"sine.inOut"}},{end_t0 + 1.3:.3f});'
        )
    series_label = esc(f"{s['title']} · PART {sc['ep']}")
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
@font-face {{ font-family: "Bangers"; src: url("Bangers-Regular.ttf"); }}
@font-face {{ font-family: "Anton"; src: url("Anton-Regular.ttf"); }}
html, body {{ margin: 0; background: #000; }}
#root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
#base {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
.layer {{ position: absolute; inset: 0; pointer-events: none; }}
.stroke {{ -webkit-text-stroke: 12px #111; paint-order: stroke fill; text-shadow: 0 8px 18px rgba(0,0,0,.65); }}
#bar {{ position: absolute; left: 0; top: 0; height: 14px; width: {W}px; background: #ffd400; transform-origin: 0 50%;
        box-shadow: 0 0 16px rgba(255,212,0,.7); }}
#pill {{ position: absolute; top: 46px; left: 50%; transform: translateX(-50%); font: 44px "Anton"; letter-spacing: 3px;
         color: #fff; background: rgba(0,0,0,.55); padding: 8px 26px; border-radius: 40px; border: 2px solid rgba(255,212,0,.8); }}
.cap {{ position: absolute; left: 60px; right: 60px; top: 1180px; text-align: center; font: 132px/1.08 "Bangers";
        color: #fff; letter-spacing: 3px; visibility: hidden; transform-origin: 50% 60%; }}
.w {{ position: relative; display: inline-block; transform-origin: 50% 70%; margin: 0 .13em;
      -webkit-text-stroke: 12px #111; paint-order: stroke fill; text-shadow: 0 8px 18px rgba(0,0,0,.65); }}
.hl {{ position: absolute; left: 0; top: 0; color: #ffd400; opacity: 0;
       -webkit-text-stroke: 12px #111; paint-order: stroke fill; }}
#hook {{ position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 42%, rgba(0,0,0,.15), rgba(0,0,0,.72)); }}
#label {{ position: absolute; top: 300px; width: 100%; text-align: center; font: 70px "Anton"; letter-spacing: 6px;
          color: #fff; visibility: hidden; }}
#hookbox {{ position: absolute; left: 70px; right: 70px; top: 430px; text-align: center; font: 160px/1.05 "Bangers";
            color: #ffd400; letter-spacing: 3px; }}
.hw {{ display: inline-block; visibility: hidden; }}
#endshade {{ position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,.25), rgba(0,0,0,.82)); visibility: hidden; }}
#endpart {{ position: absolute; top: 520px; width: 100%; text-align: center; font: 120px "Anton"; color: #ffd400; letter-spacing: 8px; visibility: hidden; }}
#endtitle {{ position: absolute; top: 680px; left: 70px; right: 70px; text-align: center; font: 150px/1.05 "Bangers"; color: #fff; visibility: hidden; }}
#follow {{ position: absolute; top: 1180px; left: 50%; margin-left: -330px; width: 660px; text-align: center; font: 74px "Anton";
           letter-spacing: 4px; color: #111; background: #ffd400; padding: 26px 0; border-radius: 90px; visibility: hidden;
           box-shadow: 0 12px 40px rgba(255,212,0,.45); }}
#follow small {{ display: block; font: 40px "Anton"; letter-spacing: 2px; margin-top: 6px; }}
</style></head>
<body>
<div id="root" data-composition-id="root" data-start="0" data-duration="{total:.3f}" data-width="{W}" data-height="{H}" data-fps="{FPS}">
  <video id="base" class="clip" src="base.mp4" data-start="0" data-duration="{total:.3f}" data-track-index="0" data-has-audio="true" playsinline></video>
  <div class="layer" id="ui" data-start="0" data-duration="{total:.3f}" data-track-index="1">
    <div id="bar"></div>
    <div id="pill">{series_label}</div>
    {"".join(caps)}
    <div id="hook"><div id="label">{series_label}</div><div id="hookbox" class="stroke">{hook_words}</div></div>
    <div id="endshade"></div>
    <div id="endpart" class="stroke">PART {sc['ep'] + 1}</div>
    <div id="endtitle" class="stroke">{esc(nxt or "")}</div>
    <div id="follow">FOLLOW<small>BIAR NGGAK KETINGGALAN</small></div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#bar", {{scaleX: 0}}, {{scaleX: 1, duration: {total:.3f}, ease: "none"}}, 0);
    tl.fromTo("#pill", {{autoAlpha: 0}}, {{autoAlpha: 1, duration: .3}}, {hook_end:.3f});
    tl.to("#pill", {{autoAlpha: 0, duration: .3}}, {end_t0:.3f});
    {hook_tl}
    {"".join(tl)}
    {end_tl}
    window.__timelines = window.__timelines || {{}};
    window.__timelines["root"] = tl;
  </script>
</div>
</body></html>
"""


def main(series_key, ep, render=True):
    s = load(SERIES / f"{series_key}.json")
    d = run_dir(series_key, ep)
    sc, tts = load(d / "script.json"), load(d / "tts.json")
    hf = d / "hf"
    hf.mkdir(exist_ok=True)
    for f in ("Bangers-Regular.ttf", "Anton-Regular.ttf"):
        shutil.copy(FONTS / f, hf / f)
    if not (hf / "base.mp4").exists():
        log("rakit video dasar tanpa subtitle…")
    total = build_base(series_key, ep, s, d, tts, hf / "base.mp4") if not (hf / "base.mp4").exists() \
        else tts["scenes"][-1]["start"] + tts["scenes"][-1]["dur"] + TAIL
    (hf / "index.html").write_text(build_html(s, sc, tts, total))
    log(f"komposisi: {hf / 'index.html'} ({total:.1f} detik)")
    if render:
        subprocess.run(["npx", "-y", HF, "render", "-o", "final-hf.mp4", "-q", "delivery", "-w", "4"],
                       cwd=hf, check=True)
        log(f"selesai: {hf / 'final-hf.mp4'}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), render="--no-render" not in sys.argv)
