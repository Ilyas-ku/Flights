#!/usr/bin/env bash
# Full rebuild: 2:00 pm ET Nov 13 -> 9:15 pm ET Nov 13 (19:00 -> 02:15 UTC), needs adsb.lol releases for Nov 13 and Nov 14.
set -euo pipefail
DATA=${DATA:-/home/user/data}; REPO=$(cd "$(dirname "$0")/.." && pwd)
REL=https://github.com/adsblol/globe_history_2026/releases/download
for day in 13 14; do
  d=$DATA/raw$day; [ "$day" = 13 ] && d=$DATA/raw
  if [ ! -d "$d/traces" ]; then
    mkdir -p "$d"; B=$REL/v2026.11.$day-planes-readsb-prod-0/v2026.11.$day-planes-readsb-prod-0.tar
    { for s in aa ab ac ad; do curl -fsSL --retry 5 "$B.$s" || break; done; } | tar -x -C "$d"
  fi
done
python3 "$REPO/scripts/extract.py" "$DATA/ext.json" 1794596400 1794622500 "$DATA/raw/traces" "$DATA/raw14/traces"
python3 "$REPO/scripts/pack.py" "$DATA/ext.json" "$REPO/site"
base64 -w0 "$REPO/site/tracks.bin.gz" > "$REPO/site/tracks.b64.txt" && rm "$REPO/site/tracks.bin.gz"
cd "$REPO/site" && (python3 -m http.server 8765 >/dev/null 2>&1 &) && sleep 1
cd "$REPO" && rm -rf video/frames && mkdir -p video/frames && node scripts/render_video.js video/frames
ffmpeg -y -loglevel error -framerate 30 -i video/frames/f%05d.png -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart -vf scale=1920:1080 video/ground_stop_2026-11-13.mp4
rm -rf video/frames; pkill -f "http.server 8765" || true
