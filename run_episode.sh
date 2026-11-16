#!/bin/bash
# Satu episode dari nol: naskah -> gambar (gflow) -> narasi -> render. Bisa diulang; tahap yang sudah ada dilanjutkan.
#   ./run_episode.sh naruto 1
set -euo pipefail
cd "$(dirname "$0")"; s="$1"; ep="$2"; py=.venv/bin/python; d="runs/$s-ep$(printf %02d "$ep")"
[ -f "$d/script.json" ] || { echo "STAGE naskah $(date +%H:%M)"; $py pipeline/script.py "$s" "$ep"; }
echo "STAGE gambar $(date +%H:%M)"; $py pipeline/images.py "$s" "$ep"
[ -f "$d/tts.json" ] || { echo "STAGE narasi $(date +%H:%M)"; $py pipeline/tts.py "$s" "$ep"; }
echo "STAGE render $(date +%H:%M)"; $py pipeline/render.py "$s" "$ep"
echo "SELESAI $d/final.mp4  (caption: $d/caption.txt)"
