"""Pack extracted positions into a compact binary (gzip) + stats json.
usage: python pack.py extracted.json out_dir
Binary (little endian): u32 nTracks, u32 nPts | per track: u16 start, u16 len, u8 flags | u16 lat[nPts] | u16 lon[nPts] | u8 alt[nPts]; values are per-track deltas (wrapping), first point absolute
"""
import json, sys, gzip, os, struct
import numpy as np

LAT0, LAT1, LON0, LON1 = 14.0, 58.0, -135.0, -52.0
CLAT0, CLAT1, CLON0, CLON1 = 24.0, 50.0, -125.5, -66.0
MAXGAP = 5

d = json.load(open(sys.argv[1]))
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
w0, w1 = d['w0'], d['w1']
N = (w1 - w0) // 60
tracks = []
airborne_airline = np.zeros(N, int)
airborne_all = np.zeros(N, int)
nbins = N // 5
tko = np.zeros(nbins, int); lnd = np.zeros(nbins, int)
for a in d['aircraft']:
    fl = 1 if a['airline'] else 0
    for k, t in a['events']:
        if not a['airline']:
            continue
        b = int((t - w0) // 300)
        if 0 <= b < nbins:
            (tko if k == 'T' else lnd)[b] += 1
    s = {int(k): v for k, v in a['samples'].items()}
    if len(s) < 2:
        continue
    ms = sorted(s)
    for m in ms:
        lat, lon, alt = s[m]
        if CLAT0 <= lat <= CLAT1 and CLON0 <= lon <= CLON1:
            airborne_all[m] += 1
            if fl: airborne_airline[m] += 1
    # split into runs, fill short gaps by interpolation
    run = [ms[0]]
    runs = []
    for m in ms[1:]:
        if m - run[-1] <= MAXGAP:
            run.append(m)
        else:
            runs.append(run); run = [m]
    runs.append(run)
    for r in runs:
        if len(r) < 2:
            continue
        mm = np.arange(r[0], r[-1] + 1)
        lat = np.interp(mm, r, [s[m][0] for m in r])
        lon = np.interp(mm, r, [s[m][1] for m in r])
        alt = np.interp(mm, r, [s[m][2] for m in r])
        tracks.append((int(r[0]), fl, lat, lon, alt))

tracks.sort(key=lambda t: t[0])
nP = sum(len(t[2]) for t in tracks)
hdr = struct.pack('<II', len(tracks), nP)
th = b''.join(struct.pack('<HHB', t[0], len(t[2]), t[1]) for t in tracks)
lat = np.concatenate([t[2] for t in tracks]); lon = np.concatenate([t[3] for t in tracks]); alt = np.concatenate([t[4] for t in tracks])
qlat = np.clip(np.round((lat - LAT0) / (LAT1 - LAT0) * 65535), 0, 65535).astype('<u2')
qlon = np.clip(np.round((lon - LON0) / (LON1 - LON0) * 65535), 0, 65535).astype('<u2')
qalt = np.clip(np.round(alt / 200), 0, 255).astype('u1')
# delta-encode within each track (first point absolute), stored as wrapping int16 / int8
starts = np.cumsum([0] + [len(t[2]) for t in tracks[:-1]])
def delta(q, dt):
    q = q.astype(np.int64)
    dq = np.diff(q, prepend=0)
    dq[starts] = q[starts]
    return (dq & (0xFFFF if dt == '<u2' else 0xFF)).astype(dt)
blob = hdr + th + delta(qlat, '<u2').tobytes() + delta(qlon, '<u2').tobytes() + delta(qalt, 'u1').tobytes()
with gzip.open(os.path.join(out, 'tracks.bin.gz'), 'wb', 9) as f:
    f.write(blob)
stats = {'w0': w0, 'minutes': int(N), 'airborneAirline': airborne_airline.tolist(), 'airborneAll': airborne_all.tolist(),
         'takeoffs5': tko.tolist(), 'landings5': lnd.tolist(), 'nTracks': len(tracks), 'nPts': int(nP),
         'nAircraft': len(d['aircraft'])}
json.dump(stats, open(os.path.join(out, 'stats.json'), 'w'))
print('tracks', len(tracks), 'pts', nP, 'raw MB', len(blob)/1e6, 'gz MB', os.path.getsize(os.path.join(out, 'tracks.bin.gz'))/1e6)
