"""Path, log, pembungkus Claude Code CLI (pola sama dengan whatif-automation)."""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
SERIES = ROOT / "series"
CLAUDE = os.path.expanduser("~/.local/bin/claude")
CLAUDE_CWD = RUNS / ".claude-cwd"  # folder kosong: CLAUDE.md proyek tidak ikut terbaca
FFMPEG = os.path.expanduser("~/game-toolchain/bin/ffmpeg")
FFPROBE = os.path.expanduser("~/game-toolchain/bin/ffprobe")
FONTS = Path.home() / "github-repos/whatif-automation/assets/fonts"
MUSIC = Path.home() / "github-repos/scraper-data-gitgit/assets/music"


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def claude(model, system, user, timeout=1500, retries=2):
    CLAUDE_CWD.mkdir(parents=True, exist_ok=True)
    args = [CLAUDE, "-p", "--output-format", "json", "--model", model, "--tools", "", "--strict-mcp-config",
            "--setting-sources", "", "--no-session-persistence", "--system-prompt", system]
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE") and k != "CLAUDECODE"}
    err = None
    for attempt in range(retries + 1):
        try:
            p = subprocess.run(args, input=user, capture_output=True, text=True, cwd=CLAUDE_CWD, timeout=timeout,
                               env=env)
            out = json.loads(p.stdout)
            if out.get("is_error"):
                raise RuntimeError(str(out.get("result") or out.get("subtype"))[:400])
            return out["result"]
        except Exception as e:  # noqa: BLE001
            err = e
            log(f"claude {model} percobaan {attempt + 1} gagal: {str(e)[:300]}")
            time.sleep(20 * (attempt + 1))
    raise RuntimeError(f"claude {model} gagal: {err}")


def parse_json(text):
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    raw = fenced.group(1) if fenced else text
    return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])


def claude_json(model, system, user, **kw):
    reply = claude(model, system, user, **kw)
    try:
        return parse_json(reply)
    except ValueError as e:
        log(f"JSON tidak valid dari {model}: {e}; ulang")
        return parse_json(claude(model, system, user + "\n\nBalas HANYA dengan satu objek JSON valid.", **kw))


def run_dir(series, ep):
    d = RUNS / f"{series}-ep{int(ep):02d}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load(path):
    return json.loads(Path(path).read_text())


def save(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1))


def ffprobe_seconds(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def ffmpeg(*args):
    p = subprocess.run([FFMPEG, "-y", "-loglevel", "error", *map(str, args)], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg gagal: " + p.stderr[-1500:])


if __name__ == "__main__":
    sys.exit("modul pustaka")
