# parodi-anime

Seri ringkasan anime serius untuk Reels Facebook/Instagram (9:16, ±200 detik per part), dibuat otomatis:
naskah dramatis + analisis berbahasa Indonesia → gambar adegan bergaya chibi sendiri → narasi suara → video lengkap dengan
subtitle, judul, kartu part berikutnya, dan lagu latar.

```
./run_episode.sh naruto 1          # hasil: runs/naruto-ep01/final.mp4 + caption.txt
```

| Tahap | Alat | Keterangan |
|---|---|---|
| `pipeline/script.py` | Claude Code CLI (`claude -p`, sonnet) | 18–22 adegan, 450–480 kata, nada serius + 3–4 kalimat analisis, hook di adegan 1, cliffhanger ke part berikutnya |
| `pipeline/images.py` | gflow-cli (Google Flow / Nano Banana), 9:16 | gaya & desain tokoh dari `series/<seri>.json`; bisa dilanjutkan; kunci bersama `/tmp/gflow-profile.lock`, Xvfb `:99`, mode classic |
| `pipeline/tts.py` | edge-tts `id-ID-ArdiNeural` | tempo/nada per suasana adegan, waktu per kata untuk subtitle |
| `pipeline/render.py` | ffmpeg (zoompan, xfade, libass) | gerak kamera pelan, subtitle 3 kata dengan kata aktif kuning, judul & kartu part berikutnya, lagu Kevin MacLeod (CC BY 4.0) yang mengecil saat narator bicara |

Seri = `series/<key>.json`: `style` (gaya visual — **gaya sendiri**, jangan meniru kreator lain), `characters`
(desain tiap tokoh, dirujuk lewat kunci), `episodes` (judul, momen wajib, judul part berikutnya).

## Aturan konten

- Gambar & suara 100% dibuat sendiri: tanpa cuplikan anime, OST, suara asli, logo/poster resmi.
- Nama tokoh & alur cerita dipakai sebagai ringkasan; analisis (motivasi tokoh, makna, lore, foreshadowing) dan
  sudut pandang sendiri adalah nilai aslinya, jadi jangan sekadar menceritakan ulang.
- Naruto part 1–11 memakai narasi parodi lama; mulai part 12 narasi serius (gaya gambar chibi tetap sama).
- Kredit lagu wajib di caption (sudah otomatis di `caption.txt`).

## Biaya per episode

±21 gambar dari kuota gambar harian Google Flow (±1.000/hari), ±25 menit gambar (bergantian dengan otomasi lain),
1 permintaan Claude, render ±6 menit CPU.
