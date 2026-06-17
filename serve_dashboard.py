#!/usr/bin/env python3
"""Serve an aesthetic local web dashboard for candidate rankings."""

import csv
import json
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_PORT = 8765
HOST = "127.0.0.1"


def load_rankings(csv_path):
    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "candidate_id": row["candidate_id"],
                "rank": int(row["rank"]),
                "score": float(row["score"]),
                "reasoning": row["reasoning"],
            })
    rows.sort(key=lambda r: r["rank"])
    return rows


def build_html(rows, source_file):
    data_json = json.dumps(rows, ensure_ascii=False)
    top_score = rows[0]["score"] if rows else 1.0
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Redrob AI Candidate Rankings</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-deep: #0a0e17;
      --bg-card: rgba(18, 24, 38, 0.72);
      --border: rgba(120, 160, 255, 0.14);
      --text: #e8edf7;
      --text-muted: #8b9bb8;
      --accent: #6c8cff;
      --accent-glow: rgba(108, 140, 255, 0.35);
      --gold: #f5c842;
      --silver: #c8d0dc;
      --bronze: #d4956a;
      --success: #4ade80;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: "DM Sans", system-ui, sans-serif;
      color: var(--text);
      min-height: 100vh;
      background: var(--bg-deep);
      overflow-x: hidden;
    }}

    .bg {{
      position: fixed;
      inset: 0;
      z-index: 0;
      background:
        radial-gradient(ellipse 80% 60% at 15% 10%, rgba(108, 140, 255, 0.18), transparent 55%),
        radial-gradient(ellipse 70% 50% at 85% 85%, rgba(168, 85, 247, 0.12), transparent 50%),
        radial-gradient(ellipse 50% 40% at 50% 50%, rgba(34, 211, 238, 0.06), transparent 60%),
        linear-gradient(165deg, #0a0e17 0%, #0f1525 40%, #121a2e 100%);
    }}

    .bg::before {{
      content: "";
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
      background-size: 48px 48px;
      mask-image: radial-gradient(ellipse 90% 80% at 50% 40%, black 20%, transparent 75%);
    }}

    .orb {{
      position: absolute;
      border-radius: 50%;
      filter: blur(80px);
      opacity: 0.5;
      animation: float 18s ease-in-out infinite;
    }}
    .orb-1 {{ width: 420px; height: 420px; background: #3b5bdb; top: -120px; left: -80px; }}
    .orb-2 {{ width: 360px; height: 360px; background: #7c3aed; bottom: -100px; right: -60px; animation-delay: -6s; }}
    .orb-3 {{ width: 280px; height: 280px; background: #0891b2; top: 40%; left: 55%; animation-delay: -12s; opacity: 0.3; }}

    @keyframes float {{
      0%, 100% {{ transform: translate(0, 0) scale(1); }}
      33% {{ transform: translate(30px, -20px) scale(1.05); }}
      66% {{ transform: translate(-20px, 15px) scale(0.95); }}
    }}

    .page {{
      position: relative;
      z-index: 1;
      max-width: 1100px;
      margin: 0 auto;
      padding: 2.5rem 1.5rem 4rem;
    }}

    header {{
      text-align: center;
      margin-bottom: 2.5rem;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.35rem 0.85rem;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--accent);
      background: rgba(108, 140, 255, 0.12);
      border: 1px solid rgba(108, 140, 255, 0.25);
      margin-bottom: 1rem;
    }}

    h1 {{
      font-size: clamp(1.8rem, 4vw, 2.6rem);
      font-weight: 700;
      letter-spacing: -0.03em;
      line-height: 1.15;
      background: linear-gradient(135deg, #fff 0%, #a5b8ff 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }}

    .subtitle {{
      margin-top: 0.75rem;
      color: var(--text-muted);
      font-size: 1rem;
    }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 1rem;
      margin: 2rem 0 2.5rem;
    }}

    .stat {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.1rem 1.25rem;
      backdrop-filter: blur(12px);
    }}

    .stat-label {{
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      margin-bottom: 0.35rem;
    }}

    .stat-value {{
      font-size: 1.5rem;
      font-weight: 700;
      font-family: "JetBrains Mono", monospace;
    }}

    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
      align-items: center;
    }}

    .search {{
      flex: 1;
      min-width: 220px;
      padding: 0.75rem 1rem 0.75rem 2.6rem;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--bg-card);
      color: var(--text);
      font-family: inherit;
      font-size: 0.95rem;
      backdrop-filter: blur(12px);
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }}

    .search:focus {{
      border-color: rgba(108, 140, 255, 0.5);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }}

    .search-wrap {{
      position: relative;
      flex: 1;
      min-width: 220px;
    }}

    .search-wrap svg {{
      position: absolute;
      left: 0.85rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      pointer-events: none;
    }}

    .filter-btn {{
      padding: 0.75rem 1.1rem;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--bg-card);
      color: var(--text-muted);
      font-family: inherit;
      font-size: 0.85rem;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .filter-btn:hover, .filter-btn.active {{
      color: var(--text);
      border-color: rgba(108, 140, 255, 0.4);
      background: rgba(108, 140, 255, 0.1);
    }}

    .list {{
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }}

    .card {{
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 1.25rem;
      align-items: start;
      padding: 1.25rem 1.35rem;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      backdrop-filter: blur(14px);
      transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
      animation: fadeUp 0.5s ease backwards;
    }}

    .card:hover {{
      transform: translateY(-2px);
      border-color: rgba(108, 140, 255, 0.28);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(108, 140, 255, 0.08);
    }}

    @keyframes fadeUp {{
      from {{ opacity: 0; transform: translateY(12px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    .card.top-1 {{ border-color: rgba(245, 200, 66, 0.35); background: linear-gradient(135deg, rgba(245,200,66,0.08), var(--bg-card)); }}
    .card.top-2 {{ border-color: rgba(200, 208, 220, 0.3); }}
    .card.top-3 {{ border-color: rgba(212, 149, 106, 0.3); }}

    .rank-badge {{
      width: 52px;
      height: 52px;
      border-radius: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 1.15rem;
      font-family: "JetBrains Mono", monospace;
      background: rgba(108, 140, 255, 0.12);
      border: 1px solid rgba(108, 140, 255, 0.2);
      flex-shrink: 0;
    }}

    .card.top-1 .rank-badge {{ background: rgba(245, 200, 66, 0.15); border-color: rgba(245, 200, 66, 0.4); color: var(--gold); }}
    .card.top-2 .rank-badge {{ background: rgba(200, 208, 220, 0.12); border-color: rgba(200, 208, 220, 0.35); color: var(--silver); }}
    .card.top-3 .rank-badge {{ background: rgba(212, 149, 106, 0.12); border-color: rgba(212, 149, 106, 0.35); color: var(--bronze); }}

    .card-body h3 {{
      font-size: 0.82rem;
      font-weight: 600;
      font-family: "JetBrains Mono", monospace;
      color: var(--accent);
      margin-bottom: 0.45rem;
    }}

    .reasoning {{
      font-size: 0.92rem;
      line-height: 1.55;
      color: var(--text-muted);
    }}

    .score-block {{
      text-align: right;
      min-width: 90px;
    }}

    .score-value {{
      font-family: "JetBrains Mono", monospace;
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--success);
    }}

    .score-bar-wrap {{
      width: 90px;
      height: 4px;
      background: rgba(255,255,255,0.08);
      border-radius: 2px;
      margin-top: 0.5rem;
      overflow: hidden;
    }}

    .score-bar {{
      height: 100%;
      border-radius: 2px;
      background: linear-gradient(90deg, var(--accent), #4ade80);
      transition: width 0.6s ease;
    }}

    .empty {{
      text-align: center;
      padding: 3rem;
      color: var(--text-muted);
    }}

    footer {{
      margin-top: 2.5rem;
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-muted);
    }}

    @media (max-width: 640px) {{
      .card {{ grid-template-columns: auto 1fr; }}
      .score-block {{ grid-column: 2; text-align: left; display: flex; align-items: center; gap: 1rem; }}
      .score-bar-wrap {{ margin-top: 0; flex: 1; max-width: 120px; }}
    }}
  </style>
</head>
<body>
  <div class="bg">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
  </div>

  <div class="page">
    <header>
      <div class="badge">Redrob Hackathon</div>
      <h1>AI Candidate Rankings</h1>
      <p class="subtitle">Top 100 candidates ranked by fit score &mdash; sourced from <code style="color:var(--accent)">{source_file}</code></p>
    </header>

    <div class="stats" id="stats"></div>

    <div class="controls">
      <div class="search-wrap">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
        </svg>
        <input type="search" class="search" id="search" placeholder="Search by ID or reasoning text...">
      </div>
      <button class="filter-btn active" data-filter="all">All</button>
      <button class="filter-btn" data-filter="top10">Top 10</button>
      <button class="filter-btn" data-filter="top25">Top 25</button>
    </div>

    <div class="list" id="list"></div>
    <footer>Local dashboard &bull; Press Ctrl+C in the terminal to stop the server</footer>
  </div>

  <script>
    const ROWS = {data_json};
    const TOP_SCORE = {top_score};

    function renderStats(filtered) {{
      const scores = filtered.map(r => r.score);
      const avg = scores.reduce((a,b) => a+b, 0) / scores.length;
      document.getElementById("stats").innerHTML = `
        <div class="stat"><div class="stat-label">Showing</div><div class="stat-value">${{filtered.length}}</div></div>
        <div class="stat"><div class="stat-label">Top Score</div><div class="stat-value">${{TOP_SCORE.toFixed(4)}}</div></div>
        <div class="stat"><div class="stat-label">Avg Score</div><div class="stat-value">${{avg.toFixed(4)}}</div></div>
        <div class="stat"><div class="stat-label">Lowest</div><div class="stat-value">${{Math.min(...scores).toFixed(4)}}</div></div>
      `;
    }}

    function renderList(rows) {{
      const list = document.getElementById("list");
      if (!rows.length) {{
        list.innerHTML = '<div class="empty">No candidates match your search.</div>';
        return;
      }}
      list.innerHTML = rows.map((r, i) => {{
        const topClass = r.rank <= 3 ? ` top-${{r.rank}}` : "";
        const medal = r.rank === 1 ? "&#127942;" : r.rank === 2 ? "&#129352;" : r.rank === 3 ? "&#129353;" : r.rank;
        const pct = Math.round((r.score / TOP_SCORE) * 100);
        return `
          <article class="card${{topClass}}" style="animation-delay:${{Math.min(i * 0.03, 1.2)}}s">
            <div class="rank-badge">${{medal}}</div>
            <div class="card-body">
              <h3>${{r.candidate_id}}</h3>
              <p class="reasoning">${{r.reasoning}}</p>
            </div>
            <div class="score-block">
              <div class="score-value">${{r.score.toFixed(4)}}</div>
              <div class="score-bar-wrap"><div class="score-bar" style="width:${{pct}}%"></div></div>
            </div>
          </article>
        `;
      }}).join("");
    }}

    let activeFilter = "all";
    let query = "";

    function applyFilters() {{
      let rows = ROWS;
      if (activeFilter === "top10") rows = rows.filter(r => r.rank <= 10);
      if (activeFilter === "top25") rows = rows.filter(r => r.rank <= 25);
      if (query) {{
        const q = query.toLowerCase();
        rows = rows.filter(r =>
          r.candidate_id.toLowerCase().includes(q) ||
          r.reasoning.toLowerCase().includes(q)
        );
      }}
      renderStats(rows);
      renderList(rows);
    }}

    document.getElementById("search").addEventListener("input", e => {{
      query = e.target.value.trim();
      applyFilters();
    }});

    document.querySelectorAll(".filter-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeFilter = btn.dataset.filter;
        applyFilters();
      }});
    }});

    applyFilters();
  </script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    html_content = ""

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            body = self.html_content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("team.csv")
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    if not csv_path.exists():
        print(f"Error: rankings file not found: {csv_path}")
        sys.exit(1)

    rows = load_rankings(csv_path)
    if not rows:
        print(f"Error: no ranking data in {csv_path}")
        sys.exit(1)

    html = build_html(rows, csv_path.name)
    DashboardHandler.html_content = html

    url = f"http://{HOST}:{port}/"
    server = HTTPServer((HOST, port), DashboardHandler)

    print(f"Dashboard ready at {url}")
    print(f"Showing {len(rows)} ranked candidates from {csv_path.name}")
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
