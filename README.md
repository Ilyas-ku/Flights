# US Ground Stop, 13 Nov 2026

Animated map of real ADS-B traffic over the US during the FAA nationwide ground stop (3:54–8:15 pm ET).

- `site/` — interactive page (serve with `python3 -m http.server` inside `site/`)
- `video/ground_stop_2026-11-13.mp4` — 1080p render
- `scripts/extract.py`, `scripts/pack.py` — build data from adsb.lol `globe_history` daily release
- `scripts/render_video.js` — frame-by-frame render with Playwright

Data: [adsb.lol](https://adsb.lol) globe_history_2026, `v2026.11.13-planes-readsb-prod-0` (ODbL). Window 19:00–24:00 UTC.
