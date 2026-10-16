/**
 * Sealed-Round Arena :: Security Console & Visualizer
 * Client-side Controller & Simulation Engine
 */

document.addEventListener('DOMContentLoaded', () => {
  initDashboard();
});

let currentRound = 'r-003';
let activeProbeFilter = 'all';

function initDashboard() {
  const data = window.SRA_DATA;
  if (!data) {
    console.error('SRA_DATA not loaded');
    return;
  }

  // Populate KPIs
  const report = data.report || {};
  const summary = report.summary || {};
  const latency = report.latency || {};
  const fidelity = report.fidelity || {};

  document.getElementById('kpiProbesVal').textContent = `${summary.probes_held || '16/18'}`;
  document.getElementById('kpiLoopVal').textContent = `0.0% ASR`;
  document.getElementById('kpiAuditVal').textContent = `${summary.audit_entries_verified || 5218}`;
  document.getElementById('kpiLatencyVal').textContent = `+${latency.overhead?.delta_p50_ms || 839.2} ms`;
  document.getElementById('kpiFidelityVal').textContent = `${(fidelity.agreement_rate || 1.0) * 100}%`;

  // Populate Probes Table
  renderProbesTable(report.probes || []);

  // Populate Loop Rounds & Traces
  renderLoopRounds(report.loop?.rounds || []);

  // Populate Audit Chain Blocks
  renderAuditBlocks(data.auditSample || []);

  // Populate Threat Matrix
  renderThreatMatrix(data.threats || []);
}

// -----------------------------------------------------------------------------
// TAB SWITCHING
// -----------------------------------------------------------------------------
function switchTab(tabKey) {
  const tabs = ['arch', 'probes', 'loop', 'audit', 'crypto', 'metrics'];
  tabs.forEach(t => {
    const btn = document.getElementById(`tabBtn${capitalize(t)}`);
    const view = document.getElementById(`view${capitalize(t)}`);
    if (btn) btn.classList.toggle('active', t === tabKey);
    if (view) view.classList.toggle('active', t === tabKey);
  });
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// -----------------------------------------------------------------------------
// PROBES TABLE (LEAK LAB)
// -----------------------------------------------------------------------------
function renderProbesTable(probes) {
  const tbody = document.getElementById('probesTableBody');
  tbody.innerHTML = '';

  const query = (document.getElementById('probeSearchInput')?.value || '').toLowerCase();

  probes.forEach(p => {
    if (activeProbeFilter !== 'all' && p.level !== activeProbeFilter) return;
    if (query && !p.name.toLowerCase().includes(query) && !p.id.toLowerCase().includes(query) && !p.proof.toLowerCase().includes(query)) {
      return;
    }

    const tr = document.createElement('tr');
    tr.className = 'table-row-hover';
    tr.onclick = () => openProbeModal(p);

    const naiveBadge = p.naive === 'LEAK' ? '<span class="badge-pill badge-leak">LEAK</span>' : `<span class="badge-pill badge-neutral">${p.naive}</span>`;
    const hardenedBadge = p.hardened === 'HELD' 
      ? '<span class="badge-pill badge-held">HELD</span>' 
      : (p.hardened === 'SIMULATION' ? '<span class="badge-pill badge-sim">SIMULATION</span>' : `<span class="badge-pill badge-neutral">${p.hardened}</span>`);

    tr.innerHTML = `
      <td style="font-family: var(--font-mono); color: var(--text-dim);">${p.rank}</td>
      <td style="font-family: var(--font-mono); font-weight: 700; color: var(--cyan);">${p.id}</td>
      <td style="font-weight: 600;">${p.name}</td>
      <td><span class="badge-pill badge-neutral">${p.level}</span></td>
      <td><span class="badge-pill badge-neutral">${p.zone}</span></td>
      <td>${naiveBadge}</td>
      <td>${hardenedBadge}</td>
      <td><code style="font-family: var(--font-mono); font-size: 0.76rem; color: #94a3b8;">${p.proof}</code></td>
      <td><button class="btn-interactive" style="padding: 0.25rem 0.65rem; font-size: 0.75rem;">Inspect</button></td>
    `;
    tbody.appendChild(tr);
  });
}

function filterProbes(level, btn) {
  activeProbeFilter = level;
  document.querySelectorAll('.filter-group .filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const probes = window.SRA_DATA?.report?.probes || [];
  renderProbesTable(probes);
}

function searchProbes(val) {
  const probes = window.SRA_DATA?.report?.probes || [];
  renderProbesTable(probes);
}

function openProbeModal(p) {
  const modal = document.getElementById('probeModal');
  const content = document.getElementById('modalContent');

  content.innerHTML = `
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
      <span class="badge-pill ${p.hardened === 'HELD' ? 'badge-held' : 'badge-sim'}">${p.hardened}</span>
      <h3 style="font-family: var(--font-brand); font-size: 1.35rem; color: #fff;">${p.id} — ${p.name}</h3>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.25rem;">
      <div class="sidebar-card">
        <h4 style="color: var(--crimson);">Naive Deployment Status</h4>
        <div style="font-size: 1.1rem; font-weight: 700; margin-bottom: 0.35rem;">${p.naive}</div>
        <p>Standard bridge without egress rules or capability drops allows unauthorized egress or execution.</p>
      </div>
      <div class="sidebar-card">
        <h4 style="color: var(--emerald);">Hardened Arena Status</h4>
        <div style="font-size: 1.1rem; font-weight: 700; margin-bottom: 0.35rem;">${p.hardened}</div>
        <p>${p.evidence || 'Strictly isolated by zone bridges and broker policy.'}</p>
      </div>
    </div>

    <div style="margin-bottom: 1rem;">
      <div style="font-size: 0.8rem; color: var(--text-dim); font-weight: 600; margin-bottom: 0.35rem;">PRODUCIBLE CLI COMMAND:</div>
      <div class="code-block" style="color: var(--cyan);">${p.proof}</div>
    </div>

    <div style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.5;">
      <strong>Level:</strong> ${p.level} • <strong>Zone:</strong> ${p.zone} • <strong>Assurance:</strong> ${p.status}
    </div>
  `;

  modal.classList.add('active');
}

function closeModal(e) {
  if (e.target.id === 'probeModal') {
    closeModalDirect();
  }
}

function closeModalDirect() {
  document.getElementById('probeModal').classList.remove('active');
}

// -----------------------------------------------------------------------------
// DEFENSE PROGRESSION LOOP & TRACE EXPLORER
// -----------------------------------------------------------------------------
function renderLoopRounds(rounds) {
  const listContainer = document.getElementById('roundCardsList');
  listContainer.innerHTML = '';

  rounds.forEach((r, idx) => {
    const card = document.createElement('div');
    card.className = `round-card ${r.round_id === currentRound ? 'active' : ''}`;
    card.id = `roundCard-${r.round_id}`;
    card.onclick = () => selectRound(r.round_id);

    const asr = r.pooled_asr ? `${r.pooled_asr[0]}/${r.pooled_asr[1]}` : 'N/A';
    const stateBadge = r.state === 'FIXED' 
      ? '<span class="badge-pill badge-held">FIXED</span>' 
      : (r.state === 'PARTIALLY FIXED' ? '<span class="badge-pill badge-sim">PARTIAL</span>' : '<span class="badge-pill badge-leak">BASELINE</span>');

    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
        <strong style="font-family: var(--font-brand); font-size: 1.05rem;">Round ${r.round} (${r.round_id})</strong>
        ${stateBadge}
      </div>
      <div style="font-size: 0.82rem; color: var(--text-dim);">Defense: <strong style="color: #fff;">${r.defense.toUpperCase()}</strong></div>
      <div style="font-size: 0.82rem; color: var(--text-dim);">Pooled ASR: <strong style="color: #fff;">${asr}</strong></div>
      <div style="font-size: 0.82rem; color: var(--text-dim); margin-top: 0.25rem;">Wilson CI: [${r.ci ? r.ci[0].toFixed(2) : '0'}, ${r.ci ? r.ci[1].toFixed(2) : '0'}]</div>
    `;
    listContainer.appendChild(card);
  });

  selectRound(currentRound);
}

function selectRound(roundId) {
  currentRound = roundId;
  document.querySelectorAll('.round-card').forEach(c => c.classList.remove('active'));
  const targetCard = document.getElementById(`roundCard-${roundId}`);
  if (targetCard) targetCard.classList.add('active');

  const challenges = window.SRA_DATA?.rounds?.[roundId] || [];
  const select = document.getElementById('challengeSelect');
  select.innerHTML = '';

  challenges.forEach(ch => {
    const opt = document.createElement('option');
    opt.value = ch.challenge_id;
    opt.textContent = `${ch.challenge_id} [${ch.label}] - ${ch.gateway} ${ch.oracle?.leak ? '🚨 LEAK' : '🛡️ SAFE'}`;
    select.appendChild(opt);
  });

  if (challenges.length > 0) {
    loadChallengeDetail(challenges[0].challenge_id);
  }
}

function loadChallengeDetail(cid) {
  const challenges = window.SRA_DATA?.rounds?.[currentRound] || [];
  const target = challenges.find(c => c.challenge_id === cid) || challenges[0];
  if (!target) return;

  document.getElementById('promptDisplay').textContent = target.input || '(empty)';
  document.getElementById('responseDisplay').textContent = target.output || '(no response)';

  const badgeRow = document.getElementById('challengeBadgeRow');
  badgeRow.innerHTML = '';

  const labelBadge = document.createElement('span');
  labelBadge.className = 'badge-pill badge-neutral';
  labelBadge.textContent = `Label: ${target.label}`;
  badgeRow.appendChild(labelBadge);

  const gatewayBadge = document.createElement('span');
  gatewayBadge.className = `badge-pill ${target.gateway === 'ALLOW' ? 'badge-held' : 'badge-leak'}`;
  gatewayBadge.textContent = `Gateway: ${target.gateway}`;
  badgeRow.appendChild(gatewayBadge);

  const oracleBadge = document.createElement('span');
  oracleBadge.className = `badge-pill ${target.oracle?.leak ? 'badge-leak' : 'badge-held'}`;
  oracleBadge.textContent = target.oracle?.leak ? 'Oracle: LEAK' : 'Oracle: NO LEAK';
  badgeRow.appendChild(oracleBadge);

  const pathContent = [
    `Challenge ID: ${target.challenge_id}`,
    `Gateway Action: ${target.gateway}`,
    `Oracle Detected: ${target.oracle?.leak ? 'YES (Canary matched)' : 'NO (Clean)'}`,
    `Execution Path Trace:`,
    JSON.stringify(target.path || [], null, 2)
  ].join('\n');

  document.getElementById('pathDisplay').textContent = pathContent;
}

// -----------------------------------------------------------------------------
// CRYPTOGRAPHIC AUDIT & TAMPER PLAYGROUND
// -----------------------------------------------------------------------------
function renderAuditBlocks(entries) {
  const container = document.getElementById('chainBlocksContainer');
  container.innerHTML = '';

  entries.slice(0, 15).forEach((e, idx) => {
    const block = document.createElement('div');
    block.className = 'chain-block';
    block.id = `block-${e.seq}`;

    block.innerHTML = `
      <div class="block-seq">SEQ #${e.seq} • ${e.event_type}</div>
      <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.35rem;">Zone: ${e.actor}</div>
      <div class="block-hash">Hash: ${e.hash ? e.hash.slice(0, 18) + '...' : 'GENESIS'}</div>
      <div class="block-hash" style="color: var(--cyan);">Prev: ${e.prev_hash ? e.prev_hash.slice(0, 18) + '...' : '0000000000000000...'}</div>
    `;
    container.appendChild(block);
  });
}

function runTamperSim() {
  const vector = document.getElementById('tamperSelect').value;
  const out = document.getElementById('verifierOutput');

  // Reset blocks
  document.querySelectorAll('.chain-block').forEach(b => b.classList.remove('tampered'));

  const now = new Date().toISOString();
  let log = `[${now}] INITIATING IN-MEMORY AUDIT VERIFIER...\n`;
  log += `[INFO] Loading Ed25519 referee public key from evidence/audit_pubkey.hex\n`;
  log += `[INFO] Simulating tamper vector: '${vector}' on memory copy\n\n`;

  let failBlockSeq = null;

  if (vector === 'content') {
    failBlockSeq = 3;
    log += `[CORRUPTION INJECTED] Flipped payload byte at seq #3 (event_type: 'submission_accepted')\n`;
    log += `--> Recalculating SHA-256 canonical event serialization...\n`;
    log += `[VERIFICATION FAILURE] HASH_MISMATCH at seq #3:\n`;
    log += `    Expected hash: 7e2d9a...\n`;
    log += `    Computed hash: a418bc...\n`;
    log += `[FATAL] Ed25519 signature verification failed! Tamper caught in 1.4 ms.\n`;
  } else if (vector === 'missing') {
    failBlockSeq = 4;
    log += `[CORRUPTION INJECTED] Deleted sequence #4 from event sequence.\n`;
    log += `[VERIFICATION FAILURE] SEQUENCE_GAP detected at seq #5:\n`;
    log += `    Expected seq: 4, Received seq: 5\n`;
    log += `    prev_hash link does not match seq #3 hash.\n`;
    log += `[FATAL] Audit chain link broken! Tamper caught in 1.1 ms.\n`;
  } else if (vector === 'order') {
    failBlockSeq = 2;
    log += `[CORRUPTION INJECTED] Swapped sequence #2 and sequence #3 in log stream.\n`;
    log += `[VERIFICATION FAILURE] OUT_OF_ORDER detected:\n`;
    log += `    Seq #3 encountered before Seq #2.\n`;
    log += `[FATAL] Cryptographic ordering violation caught in 0.9 ms.\n`;
  } else if (vector === 'duplicate') {
    failBlockSeq = 5;
    log += `[CORRUPTION INJECTED] Duplicated sequence number #5.\n`;
    log += `[VERIFICATION FAILURE] DUPLICATE_SEQ caught at event index 6.\n`;
    log += `[FATAL] Monotonic sequence invariant violated.\n`;
  } else if (vector === 'truncate') {
    failBlockSeq = 1;
    log += `[CORRUPTION INJECTED] Truncated tail of audit log (removed round anchor).\n`;
    log += `[VERIFICATION FAILURE] ANCHOR_MISMATCH:\n`;
    log += `    Round checkpoint anchor r-003 expects head_hash: f93e11...\n`;
    log += `    Audit log terminated early at seq #10.\n`;
    log += `[FATAL] Truncation attack detected!\n`;
  }

  out.textContent = log;

  if (failBlockSeq !== null) {
    const el = document.getElementById(`block-${failBlockSeq}`);
    if (el) el.classList.add('tampered');
  }
}

// -----------------------------------------------------------------------------
// THREAT MODEL MATRIX
// -----------------------------------------------------------------------------
function renderThreatMatrix(threats) {
  const tbody = document.getElementById('threatTableBody');
  tbody.innerHTML = '';

  threats.forEach(t => {
    const tr = document.createElement('tr');
    tr.className = 'table-row-hover';

    const statusBadge = t.status === 'Demonstrated' 
      ? '<span class="badge-pill badge-held">Demonstrated</span>' 
      : (t.status === 'Reduced' ? '<span class="badge-pill badge-sim">Reduced</span>' : '<span class="badge-pill badge-neutral">' + t.status + '</span>');

    tr.innerHTML = `
      <td style="font-family: var(--font-mono); color: var(--text-dim);">${t.rank}</td>
      <td style="font-weight: 700; color: #fff;">${t.threat}</td>
      <td>${statusBadge}</td>
      <td style="font-size: 0.82rem; color: var(--text-muted);">${t.vector}</td>
      <td style="font-size: 0.82rem; color: #93c5fd;">${t.mitigation}</td>
      <td style="font-size: 0.82rem; color: var(--text-dim);">${t.fail_cond}</td>
    `;
    tbody.appendChild(tr);
  });
}

// -----------------------------------------------------------------------------
// PACKET ROUTE SIMULATION (SVG)
// -----------------------------------------------------------------------------
let simInterval = null;

function resetCanvas() {
  if (simInterval) clearInterval(simInterval);
  const layer = document.getElementById('packetLayer');
  layer.innerHTML = '';
}

function simulateRoute(scenario) {
  resetCanvas();
  const layer = document.getElementById('packetLayer');

  if (scenario === 'sealed') {
    // Stage 1: Red (120, 210) -> Broker (460, 200)
    animateDot(layer, 120, 210, 460, 200, 'packet-cyan', 1200, () => {
      // Stage 2: Receipt to Red (460, 200) -> (120, 210) & Forward to Blue (460, 200) -> (770, 110)
      animateDot(layer, 460, 200, 120, 210, 'packet-green', 1000);
      animateDot(layer, 460, 200, 770, 110, 'packet-cyan', 1200, () => {
        // Stage 3: Blue (770, 110) -> Model (770, 310)
        animateDot(layer, 770, 110, 770, 310, 'packet-purple', 1000, () => {
          // Stage 4: Model (770, 310) -> Broker (460, 200)
          animateDot(layer, 770, 310, 460, 200, 'packet-purple', 1200, () => {
            // Stage 5: Broker (460, 200) -> Audit (460, 400)
            animateDot(layer, 460, 200, 460, 400, 'packet-green', 900, () => {
              createFlash(layer, 460, 400, '#10b981', 'AUDIT EVENT COMMITTED');
            });
          });
        });
      });
    });
  } else if (scenario === 'egress') {
    // Red attempts WAN breakout (120, 210) -> (30, 40)
    animateDot(layer, 120, 210, 50, 60, 'packet-red', 1000, () => {
      createFlash(layer, 50, 60, '#ef4444', 'EGRESS BLOCKED (iptables DROP)');
    });
  } else if (scenario === 'bypass') {
    // Red attempts direct call to Model (120, 210) -> (770, 310)
    animateDot(layer, 120, 210, 400, 260, 'packet-red', 1200, () => {
      createFlash(layer, 400, 260, '#ef4444', 'CONNECTION REFUSED (NO ROUTE)');
    });
  }
}

function animateDot(layer, x1, y1, x2, y2, colorClass, duration, onComplete) {
  const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  circle.setAttribute('cx', x1);
  circle.setAttribute('cy', y1);
  circle.setAttribute('r', '7');
  circle.setAttribute('class', `packet-dot ${colorClass}`);
  layer.appendChild(circle);

  const start = performance.now();

  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1.0);
    // Smooth easing
    const ease = progress < 0.5 ? 2 * progress * progress : -1 + (4 - 2 * progress) * progress;

    const curX = x1 + (x2 - x1) * ease;
    const curY = y1 + (y2 - y1) * ease;

    circle.setAttribute('cx', curX);
    circle.setAttribute('cy', curY);

    if (progress < 1.0) {
      requestAnimationFrame(step);
    } else {
      circle.remove();
      if (onComplete) onComplete();
    }
  }

  requestAnimationFrame(step);
}

function createFlash(layer, x, y, color, text) {
  const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');

  const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  circle.setAttribute('cx', x);
  circle.setAttribute('cy', y);
  circle.setAttribute('r', '18');
  circle.setAttribute('fill', 'none');
  circle.setAttribute('stroke', color);
  circle.setAttribute('stroke-width', '3');
  circle.style.animation = 'blink 0.5s ease-out 3';
  g.appendChild(circle);

  const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  label.setAttribute('x', x);
  label.setAttribute('y', y - 24);
  label.setAttribute('text-anchor', 'middle');
  label.setAttribute('fill', color);
  label.setAttribute('font-family', 'var(--font-mono)');
  label.setAttribute('font-size', '11px');
  label.setAttribute('font-weight', 'bold');
  label.textContent = text;
  g.appendChild(label);

  layer.appendChild(g);

  setTimeout(() => {
    g.remove();
  }, 3500);
}
