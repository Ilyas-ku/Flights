"""Extract 1-minute aircraft positions over North America from adsb.lol globe_history traces.
usage: python extract.py <out.json> <win_start_unix> <win_end_unix> <traces_dir> [<traces_dir> ...]
"""
import gzip, json, os, re, sys
from multiprocessing import Pool

LAT0, LAT1, LON0, LON1 = 14.0, 58.0, -135.0, -52.0
# CONUS box for takeoff/landing counting
CLAT0, CLAT1, CLON0, CLON1 = 24.0, 50.0, -125.5, -66.0
AIRLINE = re.compile(r'^[A-Z]{3}\d{1,4}[A-Z]{0,2}$')

def load(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)

def proc(path):
    try:
        d = load(path)
    except Exception:
        return None
    base = d['timestamp']
    W0, W1 = WIN
    pts = []
    cs = None
    for p in d['trace']:
        t = base + p[0]
        if t < W0 - 900 or t > W1 + 900:
            continue
        lat, lon, alt = p[1], p[2], p[3]
        if lat is None or lon is None:
            continue
        info = p[8]
        if isinstance(info, dict) and info.get('flight'):
            cs = info['flight'].strip()
        if not (LAT0 <= lat <= LAT1 and LON0 <= lon <= LON1):
            continue
        ground = alt == 'ground'
        a = 0 if ground else (alt if isinstance(alt, (int, float)) else None)
        pts.append((t, lat, lon, a, ground))
    if not pts:
        return None
    # 1-minute samples, airborne only (alt >= 300 ft)
    samples = {}
    for t, lat, lon, a, g in pts:
        if t < W0 or t >= W1 or g or a is None or a < 300:
            continue
        m = int((t - W0) // 60)
        samples[m] = (lat, lon, a)
    # takeoff / landing detection inside CONUS
    events = []
    low = None  # last time seen low/ground
    high = None
    for t, lat, lon, a, g in pts:
        if a is None:
            continue
        inbox = CLAT0 <= lat <= CLAT1 and CLON0 <= lon <= CLON1
        if g or a < 800:
            if high is not None and t - high[0] < 600 and inbox:
                events.append(('L', t))
            low = (t,)
            high = None
        elif a > 2500:
            if low is not None and t - low[0] < 600 and inbox:
                events.append(('T', low[0]))
            low = None
            high = (t,)
        else:
            if high is not None:
                high = (high[0],)
    events = [(k, t) for k, t in events if W0 <= t < W1]
    if not samples and not events:
        return None
    airline = bool(cs and AIRLINE.match(cs))
    return {'hex': d['icao'], 'cs': cs or '', 'type': d.get('t', ''), 'reg': d.get('r', ''),
            'airline': airline, 'samples': samples, 'events': events}

def init(w):
    global WIN
    WIN = w

if __name__ == '__main__':
    # usage: extract.py out.json w0 w1 traces_dir [traces_dir ...]  (one dir per UTC day; merged by ICAO hex)
    out, w0, w1, roots = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]
    files = [os.path.join(dp, f) for root in roots for dp, _, fs in os.walk(root) for f in fs if f.startswith('trace_full_')]
    print(len(files), 'files', file=sys.stderr)
    merged = {}
    with Pool(os.cpu_count(), initializer=init, initargs=((w0, w1),)) as pool:
        for r in pool.imap_unordered(proc, files, chunksize=200):
            if not r:
                continue
            m = merged.get(r['hex'])
            if m is None:
                merged[r['hex']] = r
            else:
                m['samples'].update(r['samples'])
                m['events'] += r['events']
                m['airline'] = m['airline'] or r['airline']
                m['cs'] = m['cs'] or r['cs']
    res = list(merged.values())
    for r in res:
        r['samples'] = {str(k): v for k, v in r['samples'].items()}
    json.dump({'w0': w0, 'w1': w1, 'aircraft': res}, open(out, 'w'))
    print(len(res), 'aircraft kept', file=sys.stderr)
