"""Real-time dashboard for DataPrune — served at /dashboard."""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DataPrune — Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0e1a;
    --surface: rgba(255,255,255,0.04);
    --surface-hover: rgba(255,255,255,0.07);
    --border: rgba(255,255,255,0.08);
    --text: #e2e8f0;
    --text-dim: #94a3b8;
    --accent: #6366f1;
    --accent-glow: rgba(99,102,241,0.3);
    --green: #22c55e;
    --green-glow: rgba(34,197,94,0.2);
    --amber: #f59e0b;
    --red: #ef4444;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: 'Inter', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
  }
  body::before {
    content: '';
    position: fixed;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle at 30% 20%, rgba(99,102,241,0.08) 0%, transparent 50%),
                radial-gradient(circle at 70% 80%, rgba(34,197,94,0.05) 0%, transparent 50%);
    z-index: 0;
    pointer-events: none;
  }

  .container { max-width: 1200px; margin: 0 auto; padding: 2rem; position: relative; z-index: 1; }

  /* Header */
  .header { text-align: center; margin-bottom: 2.5rem; }
  .header h1 {
    font-size: 2.2rem; font-weight: 800;
    background: linear-gradient(135deg, #fff 0%, #6366f1 50%, #22c55e 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -0.03em;
  }
  .header p { color: var(--text-dim); margin-top: 0.5rem; font-size: 0.95rem; }
  .status-badge {
    display: inline-flex; align-items: center; gap: 0.4rem;
    margin-top: 0.75rem; padding: 0.35rem 1rem;
    background: var(--green-glow); border: 1px solid rgba(34,197,94,0.3);
    border-radius: 999px; font-size: 0.8rem; color: var(--green);
  }
  .status-dot {
    width: 8px; height: 8px; border-radius: 50%; background: var(--green);
    animation: pulse 2s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

  /* Stats Grid */
  .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.25rem; margin-bottom: 2rem; }
  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px; padding: 1.5rem;
    backdrop-filter: blur(20px);
    transition: all 0.3s ease;
    position: relative; overflow: hidden;
  }
  .stat-card:hover { background: var(--surface-hover); transform: translateY(-2px); border-color: rgba(99,102,241,0.3); }
  .stat-card::after {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0; transition: opacity 0.3s;
  }
  .stat-card:hover::after { opacity: 1; }
  .stat-label { font-size: 0.8rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; font-weight: 500; }
  .stat-value {
    font-size: 2.5rem; font-weight: 800; margin: 0.5rem 0 0.25rem;
    background: linear-gradient(135deg, #fff, var(--accent));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    transition: all 0.5s;
  }
  .stat-value.green { background: linear-gradient(135deg, #fff, var(--green)); -webkit-background-clip: text; }
  .stat-sub { font-size: 0.8rem; color: var(--text-dim); }
  .stat-icon { font-size: 1.8rem; position: absolute; top: 1.25rem; right: 1.25rem; opacity: 0.15; }

  /* Section */
  .section-title {
    font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem;
    display: flex; align-items: center; gap: 0.5rem;
  }

  /* Prune Tester */
  .tester {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; padding: 1.5rem; margin-bottom: 2rem;
    backdrop-filter: blur(20px);
  }
  .tester-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-top: 1rem; }
  .tester-col label { display: block; font-size: 0.8rem; color: var(--text-dim); margin-bottom: 0.4rem; text-transform: uppercase; letter-spacing: 0.06em; }
  textarea {
    width: 100%; height: 180px; background: rgba(0,0,0,0.3); border: 1px solid var(--border);
    border-radius: 10px; color: var(--text); font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.82rem; padding: 0.9rem; resize: vertical; outline: none;
    transition: border-color 0.2s;
  }
  textarea:focus { border-color: var(--accent); }
  select, input[type="text"] {
    width: 100%; padding: 0.6rem 0.9rem; background: rgba(0,0,0,0.3);
    border: 1px solid var(--border); border-radius: 8px; color: var(--text);
    font-family: 'Inter', sans-serif; font-size: 0.85rem; outline: none;
    transition: border-color 0.2s;
  }
  select:focus, input:focus { border-color: var(--accent); }
  .tester-controls { display: flex; gap: 0.75rem; align-items: flex-end; margin-top: 1rem; }
  .btn-prune {
    padding: 0.65rem 1.6rem; background: linear-gradient(135deg, var(--accent), #8b5cf6);
    color: #fff; border: none; border-radius: 10px; font-weight: 600;
    font-size: 0.9rem; cursor: pointer; transition: all 0.2s;
    box-shadow: 0 4px 15px var(--accent-glow);
  }
  .btn-prune:hover { transform: translateY(-1px); box-shadow: 0 6px 25px var(--accent-glow); }
  .btn-prune:active { transform: translateY(0); }
  .result-badge {
    display: inline-flex; align-items: center; gap: 0.3rem;
    padding: 0.3rem 0.8rem; border-radius: 999px; font-size: 0.78rem; font-weight: 600;
  }
  .badge-saved { background: var(--green-glow); color: var(--green); border: 1px solid rgba(34,197,94,0.3); }

  /* Audit Log Table */
  .log-table-wrapper {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; overflow: hidden; backdrop-filter: blur(20px);
  }
  table { width: 100%; border-collapse: collapse; }
  th {
    text-align: left; padding: 0.9rem 1rem; font-size: 0.75rem;
    text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-dim);
    border-bottom: 1px solid var(--border); background: rgba(0,0,0,0.2);
  }
  td { padding: 0.75rem 1rem; font-size: 0.85rem; border-bottom: 1px solid var(--border); }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(99,102,241,0.04); }
  .empty-state { text-align: center; padding: 2.5rem; color: var(--text-dim); font-size: 0.9rem; }

  @media (max-width: 768px) {
    .stats-grid { grid-template-columns: 1fr; }
    .tester-grid { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🔒 DataPrune</h1>
    <p>Generic LLM Context-Pruning Middleware</p>
    <div class="status-badge"><div class="status-dot"></div> Live — Auto-refreshing</div>
  </div>

  <!-- Stats -->
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-icon">⚡</div>
      <div class="stat-label">Total Operations</div>
      <div class="stat-value" id="totalOps">—</div>
      <div class="stat-sub">pruning requests processed</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">📦</div>
      <div class="stat-label">Bytes Saved</div>
      <div class="stat-value green" id="bytesSaved">—</div>
      <div class="stat-sub" id="bytesSub">data stripped from LLM context</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">🪙</div>
      <div class="stat-label">Tokens Saved</div>
      <div class="stat-value green" id="tokensSaved">—</div>
      <div class="stat-sub">estimated LLM token savings</div>
    </div>
  </div>

  <!-- Live Prune Tester -->
  <div class="tester">
    <div class="section-title">🧪 Live Prune Tester</div>
    <div class="tester-controls">
      <div style="flex:1">
        <label style="font-size:0.8rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:0.06em">Profile</label>
        <select id="profileSelect"></select>
      </div>
      <button class="btn-prune" onclick="runPrune()">Prune →</button>
    </div>
    <div class="tester-grid">
      <div class="tester-col">
        <label>Raw Input</label>
        <textarea id="rawInput">{
  "Name": "Acme Corp",
  "Industry": "Technology",
  "AnnualRevenue": 5000000,
  "SSN": "123-45-6789",
  "SystemModstamp": "2024-01-01",
  "IsDeleted": false,
  "PhotoUrl": "/services/images/photo.png",
  "BillingStreet": "123 Main St"
}</textarea>
      </div>
      <div class="tester-col">
        <label>Pruned Output <span id="resultBadge"></span></label>
        <textarea id="prunedOutput" readonly placeholder="Click 'Prune →' to see results..."></textarea>
      </div>
    </div>
  </div>

  <!-- Audit Log -->
  <div class="section-title">📋 Recent Audit Log</div>
  <div class="log-table-wrapper">
    <table>
      <thead>
        <tr>
          <th>Profile</th>
          <th>Original</th>
          <th>Pruned</th>
          <th>Saved</th>
          <th>Tokens Saved</th>
          <th>Time</th>
        </tr>
      </thead>
      <tbody id="logBody">
        <tr><td colspan="6" class="empty-state">Loading audit log...</td></tr>
      </tbody>
    </table>
  </div>
</div>

<script>
const API = '';

function fmt(n) {
  if (n >= 1_000_000) return (n/1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n/1_000).toFixed(1) + 'K';
  return n.toLocaleString();
}

function fmtBytes(b) {
  if (b >= 1_048_576) return (b/1_048_576).toFixed(1) + ' MB';
  if (b >= 1_024) return (b/1_024).toFixed(1) + ' KB';
  return b + ' B';
}

function timeAgo(ts) {
  const diff = (Date.now() - new Date(ts).getTime()) / 1000;
  if (diff < 60) return Math.floor(diff) + 's ago';
  if (diff < 3600) return Math.floor(diff/60) + 'm ago';
  if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
  return Math.floor(diff/86400) + 'd ago';
}

async function loadStats() {
  try {
    const r = await fetch(API + '/api/v1/audit/stats');
    const d = await r.json();
    document.getElementById('totalOps').textContent = fmt(d.total_operations);
    document.getElementById('bytesSaved').textContent = fmtBytes(d.total_bytes_saved);
    document.getElementById('tokensSaved').textContent = fmt(d.total_tokens_saved);
    document.getElementById('bytesSub').textContent = fmtBytes(d.total_bytes_saved) + ' stripped from LLM context';
  } catch(e) { console.error('Stats error:', e); }
}

async function loadProfiles() {
  try {
    const r = await fetch(API + '/api/v1/profiles');
    const d = await r.json();
    const sel = document.getElementById('profileSelect');
    sel.innerHTML = d.profiles.map(p => `<option value="${p}">${p}</option>`).join('');
  } catch(e) { console.error('Profiles error:', e); }
}

async function loadLogs() {
  try {
    const r = await fetch(API + '/api/v1/audit/logs?limit=20');
    const logs = await r.json();
    const body = document.getElementById('logBody');
    if (!logs.length) {
      body.innerHTML = '<tr><td colspan="6" class="empty-state">No pruning events yet. Use the tester above or call the API.</td></tr>';
      return;
    }
    body.innerHTML = logs.map(l => {
      const saved = l.original_payload_bytes - l.pruned_payload_bytes;
      const pct = l.original_payload_bytes > 0 ? Math.round(saved / l.original_payload_bytes * 100) : 0;
      return `<tr>
        <td><strong>${l.source_profile}</strong></td>
        <td>${fmtBytes(l.original_payload_bytes)}</td>
        <td>${fmtBytes(l.pruned_payload_bytes)}</td>
        <td><span class="result-badge badge-saved">↓${pct}%</span></td>
        <td>${fmt(l.tokens_saved_estimate)}</td>
        <td style="color:var(--text-dim)">${timeAgo(l.timestamp)}</td>
      </tr>`;
    }).join('');
  } catch(e) { console.error('Logs error:', e); }
}

async function runPrune() {
  const profile = document.getElementById('profileSelect').value;
  const rawText = document.getElementById('rawInput').value;
  const out = document.getElementById('prunedOutput');
  const badge = document.getElementById('resultBadge');

  try {
    const payload = JSON.parse(rawText);
    const r = await fetch(API + '/api/v1/prune', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({profile, payload})
    });
    const d = await r.json();
    if (r.ok) {
      out.value = JSON.stringify(d.pruned_payload, null, 2);
      const pct = d.original_bytes > 0 ? Math.round(d.bytes_saved / d.original_bytes * 100) : 0;
      badge.innerHTML = `<span class="result-badge badge-saved">↓${pct}% · ${d.tokens_saved_estimate} tokens saved</span>`;
      loadStats();
      loadLogs();
    } else {
      out.value = JSON.stringify(d, null, 2);
      badge.innerHTML = '';
    }
  } catch(e) {
    out.value = 'Error: ' + e.message;
    badge.innerHTML = '';
  }
}

// Init
loadStats();
loadProfiles();
loadLogs();
setInterval(loadStats, 5000);
setInterval(loadLogs, 10000);
</script>
</body>
</html>
"""
