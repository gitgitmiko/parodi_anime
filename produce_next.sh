#!/bin/bash
# Dijalankan cron 2x sehari: buat episode berikutnya yang belum jadi dari antrean seri (queue.txt, satu seri per baris).
# Satu produksi dalam satu waktu (flock). Log: runs/production.log
set -uo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$HOME/game-toolchain/bin:/usr/local/bin:/usr/bin:/bin"
exec 9>runs/.produce.lock
flock -n 9 || { echo "$(date '+%F %T') produksi lain masih berjalan, lewati" >> runs/production.log; exit 0; }
next=$(.venv/bin/python - <<'PY'
import json, pathlib
root = pathlib.Path(".")
for key in [l.strip() for l in (root / "queue.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]:
    s = json.loads((root / "series" / f"{key}.json").read_text())
    for e in sorted(s["episodes"], key=lambda e: e["ep"]):
        if not (root / "runs" / f"{key}-ep{e['ep']:02d}" / "final.mp4").exists():
            print(key, e["ep"]); raise SystemExit
PY
)
if [ -z "$next" ]; then echo "$(date '+%F %T') semua episode di antrean sudah jadi" >> runs/production.log; exit 0; fi
set -- $next
echo "$(date '+%F %T') mulai $1 part $2" >> runs/production.log
if ./run_episode.sh "$1" "$2" >> "runs/$1-ep$(printf %02d "$2").log" 2>&1; then
  echo "$(date '+%F %T') selesai $1 part $2" >> runs/production.log
else
  echo "$(date '+%F %T') GAGAL $1 part $2 (lihat runs/$1-ep$(printf %02d "$2").log)" >> runs/production.log
fi
