import os
import json
import http.server
import socketserver
import sys
import urllib.parse

ROOT = os.path.dirname(__file__)
WEB_DIR = os.path.join(ROOT, "web")
DATA_PATH = os.path.join(WEB_DIR, "data.jsonl")
RAG_PATH = os.path.join(WEB_DIR, "rag.jsonl")
LOC_NAME = os.environ.get("FRONTEND_LOCATION")

HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Enviro Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root { --bg: linear-gradient(180deg,#0b1430 0%,#0a1026 50%,#070c1d 100%); --card: rgba(255,255,255,0.06); --border: rgba(255,255,255,0.12); --text: #eaf2ff; --muted: rgba(234,242,255,0.76); --low:#4ade80; --med:#facc15; --high:#f87171; }
    * { box-sizing: border-box; }
    body { margin:0; min-height:100vh; background:var(--bg); color:var(--text); font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, "Helvetica Neue", Arial; display:grid; place-items:start; padding:24px; }
    .wrap { width:min(1200px,96vw); margin:auto; display:grid; gap:20px; }
    .header { display:flex; align-items:center; justify-content:space-between; padding:18px 22px; border-radius:18px; background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(250,204,21,0.15)); border:1px solid var(--border); box-shadow: 0 10px 30px rgba(0,0,0,0.35); }
    .title { font-size:20px; letter-spacing:.4px; }
    .status { display:grid; gap:6px; }
    .score { font-size:26px; font-weight:700; }
    .desc { font-size:14px; color: var(--muted); }
    .bar { height:10px; border-radius:999px; background: linear-gradient(90deg,#22c55e 0%,#facc15 50%,#ef4444 100%); position:relative; }
    .thumb { position:absolute; top:-3px; width:16px; height:16px; border-radius:50%; background:#fff; box-shadow:0 0 14px rgba(255,255,255,0.5); }
    .grid { display:grid; grid-template-columns: 1fr 1fr; gap:18px; }
    .card { border-radius:18px; background: var(--card); border:1px solid var(--border); padding:18px; box-shadow:0 8px 26px rgba(0,0,0,0.35); backdrop-filter: blur(10px); }
    .chip { display:inline-flex; align-items:center; gap:10px; padding:10px 14px; border-radius:999px; border:1px solid var(--border); margin-top:6px; font-weight:600; letter-spacing:.8px; text-transform:uppercase; }
    .chip.low { color: var(--low); }
    .chip.medium { color: var(--med); }
    .chip.high { color: var(--high); }
    table { width:100%; border-collapse: collapse; }
    th, td { border-bottom:1px solid var(--border); padding:8px 10px; text-align:left; font-size:13px; }
    th { font-weight:600; }
    .metrics { display:grid; grid-template-columns: repeat(3,1fr); gap:12px; }
    .metric { border-radius:14px; background: var(--card); border:1px solid var(--border); padding:12px; }
    .big { font-size:32px; font-weight:700; }
    .unit { font-size:14px; opacity:.8; margin-left:6px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <div class="title" id="locName">Your Location</div>
      <div class="status">
        <div class="score" id="scoreText">Satisfactory 93</div>
        <div class="desc" id="descText">Air conditions are acceptable.</div>
        <div class="bar"><div class="thumb" id="thumb" style="left: 75%;"></div></div>
      </div>
    </div>
    <div class="grid">
      <div class="card">
        <canvas id="chart"></canvas>
      </div>
      <div class="card">
        <div id="riskTag" class="chip low">LOW</div>
        <div class="metrics">
          <div class="metric"><div>Timestamp</div><div class="big" id="ts">—</div></div>
          <div class="metric"><div>Avg Rainfall</div><div class="big" id="rain">— <span class="unit">mm</span></div></div>
          <div class="metric"><div>River Level</div><div class="big" id="river">— <span class="unit">cm</span></div></div>
        </div>
      </div>
    </div>
    <div class="card">
      <table>
        <thead><tr><th>Timestamp</th><th>Avg Rainfall</th><th>River Level</th><th>Risk</th><th>Explanation</th></tr></thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
  </div>
  <script>
    const riskClass = v => v === 'HIGH' ? 'high' : v === 'MEDIUM' ? 'medium' : 'low';
    const scoreFor = v => v === 'HIGH' ? 30 : v === 'MEDIUM' ? 65 : 93;
    const descFor = v => v === 'HIGH' ? 'Flood risk is high. Limit outdoor activity.' : v === 'MEDIUM' ? 'Monitor river conditions; carry umbrella.' : 'Air and river conditions are acceptable.';
    const ts = document.getElementById('ts');
    const rain = document.getElementById('rain');
    const river = document.getElementById('river');
    const riskTag = document.getElementById('riskTag');
    const scoreText = document.getElementById('scoreText');
    const descText = document.getElementById('descText');
    const thumb = document.getElementById('thumb');
    const rows = document.getElementById('rows');
    const locName = document.getElementById('locName');

    let chart;
    function ensureChart() {
      if (chart) return chart;
      const ctx = document.getElementById('chart').getContext('2d');
      chart = new Chart(ctx, {
        type: 'line',
        data: { labels: [], datasets: [
          { label: 'Avg Rainfall (mm)', borderColor: '#60a5fa', backgroundColor: 'rgba(96,165,250,0.25)', tension: 0.25, data: [] },
          { label: 'River Level (cm)', borderColor: '#34d399', backgroundColor: 'rgba(52,211,153,0.25)', tension: 0.25, data: [] }
        ]},
        options: { plugins: { legend: { labels: { color: '#eaf2ff' } } }, scales: { x: { ticks: { color: '#eaf2ff' } }, y: { ticks: { color: '#eaf2ff' } } } }
      });
      return chart;
    }

    async function setLocation() {
      try {
        const r = await fetch('/api/location', { cache: 'no-store' });
        if (r.ok) { const j = await r.json(); if (j.name) locName.textContent = j.name; }
      } catch {}
      if (locName.textContent === 'Your Location' && navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(async pos => {
          try {
            const { latitude, longitude } = pos.coords;
            const resp = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}`);
            if (resp.ok) {
              const g = await resp.json();
              const name = g.address?.city || g.address?.town || g.address?.village || g.address?.state || 'Your Location';
              locName.textContent = name;
            }
          } catch {}
        }, () => {});
      }
    }

    async function refreshLatest() {
      try {
        const r = await fetch('/api/latest', { cache: 'no-store' });
        if (!r.ok) return;
        const j = await r.json();
        ts.textContent = j.timestamp || '—';
        rain.firstChild.nodeValue = (Math.round((j.avg_rainfall ?? j.rainfall ?? 0) * 10) / 10).toString();
        river.firstChild.nodeValue = (j.river_level ?? 0).toString();
        const rk = (j.risk || 'LOW').toUpperCase();
        riskTag.textContent = rk;
        riskTag.className = 'chip ' + riskClass(rk);
        const s = scoreFor(rk);
        scoreText.textContent = (rk === 'LOW' ? 'Satisfactory ' : rk === 'MEDIUM' ? 'Moderate ' : 'Poor ') + s;
        descText.textContent = descFor(rk);
        thumb.style.left = Math.min(95, Math.max(5, s)) + '%';
      } catch {}
    }

    async function refreshHistory() {
      try {
        const r = await fetch('/api/history?n=50', { cache: 'no-store' });
        if (!r.ok) return;
        const arr = await r.json();
        const c = ensureChart();
        c.data.labels = arr.map(x => x.timestamp);
        c.data.datasets[0].data = arr.map(x => x.avg_rainfall ?? x.rainfall ?? 0);
        c.data.datasets[1].data = arr.map(x => x.river_level ?? 0);
        c.update();
        rows.innerHTML = '';
        arr.slice().reverse().forEach(x => {
          const tr = document.createElement('tr');
          tr.innerHTML = `<td>${x.timestamp ?? ''}</td><td>${x.avg_rainfall ?? x.rainfall ?? ''}</td><td>${x.river_level ?? ''}</td><td>${x.risk ?? ''}</td><td>${x.explanation ?? ''}</td>`;
          rows.appendChild(tr);
        });
      } catch {}
    }

    setLocation();
    refreshLatest();
    refreshHistory();
    setInterval(refreshLatest, 1500);
    setInterval(refreshHistory, 3000);
  </script>
</body>
</html>
"""

class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, ctype="text/plain", body=b""):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        if body:
            self.wfile.write(body)
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self._send(200, "text/html; charset=utf-8", HTML.encode())
        elif self.path.startswith("/api/latest"):
            last = None
            for p in (DATA_PATH, RAG_PATH):
                try:
                    with open(p, "rb") as f:
                        for line in f:
                            t = line.strip()
                            if t:
                                last = t
                    if last:
                        break
                except FileNotFoundError:
                    continue
            if last:
                self._send(200, "application/json", last)
            else:
                self._send(204)
        elif self.path.startswith("/api/history"):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query or "")
            n = int(qs.get("n", ["50"])[0])
            def read_lines(p):
                out = []
                try:
                    with open(p, "rb") as f:
                        for line in f:
                            t = line.strip()
                            if t:
                                out.append(json.loads(t.decode()))
                except FileNotFoundError:
                    pass
                return out
            data = read_lines(DATA_PATH)
            if not data:
                data = read_lines(RAG_PATH)
            if data:
                body = json.dumps(data[-n:])
                self._send(200, "application/json", body.encode())
            else:
                self._send(204)
        elif self.path == "/api/location":
            if LOC_NAME:
                self._send(200, "application/json", json.dumps({"name": LOC_NAME}).encode())
            else:
                self._send(204)
        else:
            self._send(404)

def main():
    os.makedirs(WEB_DIR, exist_ok=True)
    start = int(os.environ.get("DASHBOARD_PORT", "8010"))
    for p in range(start, start + 20):
        try:
            with socketserver.TCPServer(("", p), Handler) as httpd:
                print(f"http://localhost:{p}/")
                httpd.serve_forever()
        except OSError:
            continue
    print("no free port")
    sys.exit(1)

if __name__ == "__main__":
    main()
