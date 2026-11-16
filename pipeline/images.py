"""Langkah 2: satu gambar 9:16 per adegan lewat gflow (Google Flow / Nano Banana) -> runs/<seri>-epNN/img/NN.jpg

Bisa dilanjutkan: adegan yang gambarnya sudah ada dilewati. Aturan pemakaian gflow sama dengan whatif-automation:
Xvfb :99, mode classic (kuota gambar harian paket), kunci bersama /tmp/gflow-profile.lock.

    python pipeline/images.py naruto 1
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from common import *

GFLOW = Path.home() / "github-repos/gflow-cli/.venv/bin/gflow"
LOCK, LOCK_WAIT = "/tmp/gflow-profile.lock", 1800
BATCH = 7
DISPLAY = ":99"


def ensure_display():
    n = DISPLAY.lstrip(":")
    if Path(f"/tmp/.X11-unix/X{n}").exists():
        return
    Path(f"/tmp/.X{n}-lock").unlink(missing_ok=True)
    subprocess.Popen(["Xvfb", DISPLAY, "-screen", "0", "1920x1080x24", "-nolisten", "tcp"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(50):
        if Path(f"/tmp/.X11-unix/X{n}").exists():
            return
        time.sleep(0.2)
    sys.exit(f"Xvfb tidak hidup di {DISPLAY}")


def gflow(*a, timeout=2400):
    env = {**os.environ, "DISPLAY": DISPLAY, "GFLOW_CLI_UI_MODE": "classic"}
    return subprocess.run(["flock", "-w", str(LOCK_WAIT), LOCK, str(GFLOW), *map(str, a)], capture_output=True,
                          text=True, timeout=timeout + LOCK_WAIT, env=env)


MAX_PROMPT = 1950  # gflow menolak prompt > 2000 karakter


def scene_prompt(series, scene):
    """Gaya + adegan + desain tokoh. Bila kepanjangan (banyak tokoh): desain tokoh dipersingkat ke ciri utama
    (bagian sebelum koma pertama "wearing"), lalu tokoh ke-4 dst dibuang, terakhir adegan dipotong."""
    keys = [k for k in scene.get("tokoh", []) if k in series["characters"]]
    visual = re.sub(r"\{(\w+)\}", lambda m: series["characters"].get(m.group(1), m.group(1)), scene["visual"])

    def build(descs, vis):
        chars = [f"{k.replace('_', ' ')}: {d}" for k, d in descs]
        text = f"{series['style']} Scene: {vis}" + (
            f" Characters (keep exactly this design): {' | '.join(chars)}." if chars else "")
        return " ".join(text.split())  # satu baris per prompt (file prompt gflow)

    full = [(k, series["characters"][k]) for k in keys]
    text = build(full, visual)
    if len(text) > MAX_PROMPT:
        short = [(k, d.split(", wearing")[0].split(", carrying")[0]) for k, d in full]
        text = build(short, visual)
        if len(text) > MAX_PROMPT:
            text = build(short[:3], visual)
        if len(text) > MAX_PROMPT:
            over = len(text) - MAX_PROMPT
            text = build(short[:3], visual[: max(80, len(visual) - over - 5)].rsplit(" ", 1)[0])
    return text[:MAX_PROMPT]


def project_id(d, series_key):
    pf = d.parent / f".gflow-project-{series_key}.txt"
    if pf.exists():
        return pf.read_text().strip()
    r = gflow("project", "create", "--name", f"parodi-{series_key}", "--json", timeout=300)
    out = json.loads(r.stdout[r.stdout.index("{"):]) if "{" in r.stdout else {}
    if "project_id" not in out:
        sys.exit(f"gflow project create gagal: {(out.get('error') or {}).get('detail')} {r.stderr[-400:]}")
    pf.write_text(out["project_id"])
    return out["project_id"]


def main(series_key, ep):
    ensure_display()
    s = load(SERIES / f"{series_key}.json")
    d = run_dir(series_key, ep)
    sc = load(d / "script.json")
    img = d / "img"
    img.mkdir(exist_ok=True)
    project = project_id(d, series_key)
    fails = 0
    while True:
        todo = [i for i in range(len(sc["adegan"])) if not (img / f"{i + 1:02}.jpg").exists()]
        log(f"gambar {len(sc['adegan']) - len(todo)}/{len(sc['adegan'])}")
        if not todo:
            return
        part = todo[:BATCH]
        tmp = d / "tmp-img"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        (tmp / "p.txt").write_text("\n".join(scene_prompt(s, sc["adegan"][i]) for i in part) + "\n")
        r = gflow("image", "t2i", "--prompts-file", tmp / "p.txt", "--aspect", "9:16", "--jitter", "10-30",
                  "--project", project, "--out", tmp)
        made = 0
        for n, i in enumerate(part):
            f = next(iter(sorted(tmp.glob(f"prompt_{n}_*.jpg")) + sorted(tmp.glob(f"prompt_{n}_*.png"))), None)
            if f:
                shutil.move(f, img / f"{i + 1:02}.jpg")
                made += 1
        with open(d / "gflow.log", "a") as fh:
            fh.write(r.stdout[-3000:] + r.stderr[-1500:] + "\n")
        said = " ".join(re.sub(r"[^\w\s]", " ", r.stdout + r.stderr).lower().split())
        if not made and ("batas kuota" in said or "quota" in said):
            sys.exit("kuota gambar Google Flow habis; coba lagi besok")
        fails = 0 if made else fails + 1
        if fails >= 3:
            sys.exit(f"gflow tidak menghasilkan gambar 3 batch berturut-turut; lihat {d / 'gflow.log'}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
