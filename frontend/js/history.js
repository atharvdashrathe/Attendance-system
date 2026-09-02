/* ================================================
   history.js — Attendance History + Session Detail
   ================================================ */

async function renderHistory(root) {
  root.innerHTML = `
    <div class="page-header-row">
      <div class="page-header" style="margin-bottom:0;">
        <h1>Attendance History</h1>
        <p>View all past attendance sessions and download Excel reports.</p>
      </div>
    </div>

    <div class="card" style="margin-top:24px; padding:0; overflow:hidden;">
      <div style="padding:20px 24px; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between;">
        <div>
          <div class="card-title">All Sessions</div>
          <div class="card-subtitle" id="session-count-label">Loading…</div>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <input type="text" id="history-search" class="form-control"
            placeholder="Search subject or lecture…"
            style="width:220px;"
            oninput="filterHistory()" />
          <button class="btn btn-primary btn-sm" onclick="navigate('take')">+ New Session</button>
        </div>
      </div>

      <div id="history-table-container">
        <div style="padding:48px; text-align:center; color:var(--text-muted);">
          <div class="spinner spinner-dark" style="margin:0 auto 12px;"></div>
          Loading sessions…
        </div>
      </div>
    </div>`;

  await loadHistory();
}

let _allSessions = [];

async function loadHistory() {
  const container = document.getElementById('history-table-container');
  const countLabel = document.getElementById('session-count-label');

  try {
    const res = await apiGet('/api/sessions');
    if (!res.ok) throw new Error(res.error);
    _allSessions = res.data;

    if (countLabel) countLabel.textContent = `${_allSessions.length} session${_allSessions.length !== 1 ? 's' : ''} total`;

    renderHistoryTable(_allSessions);
  } catch (err) {
    if (container) container.innerHTML = `<div style="padding:32px; color:var(--absent-fg);">Error: ${err.message}</div>`;
  }
}

function filterHistory() {
  const query = (document.getElementById('history-search')?.value || '').toLowerCase();
  const filtered = _allSessions.filter(s =>
    s.subject_name.toLowerCase().includes(query) ||
    s.lecture.toLowerCase().includes(query)
  );
  renderHistoryTable(filtered);
}

function renderHistoryTable(sessions) {
  const container = document.getElementById('history-table-container');
  if (!container) return;

  if (!sessions || sessions.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">📋</span>
        <div class="empty-title">No sessions found</div>
        <div class="empty-desc">Start by taking attendance from the Take Attendance page.</div>
        <button class="btn btn-primary mt-4" onclick="navigate('take')">Take Attendance</button>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="table-wrapper" style="border:none; border-radius:0;">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Date</th>
            <th>Time</th>
            <th>Subject</th>
            <th>Lecture</th>
            <th>Present / Total</th>
            <th>Attendance %</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${sessions.map((s, idx) => {
            const pct = s.total_count > 0
              ? Math.round((s.present_count / s.total_count) * 100)
              : 0;
            const pctColor = pct >= 75
              ? 'var(--present-fg)'
              : pct >= 50
              ? 'hsl(38,80%,35%)'
              : 'var(--absent-fg)';

            return `
              <tr>
                <td style="color:var(--text-muted); font-size:12px;">${s.id}</td>
                <td style="font-weight:500;">${formatDate(s.date)}</td>
                <td style="color:var(--text-secondary);">${formatTime(s.session_time)}</td>
                <td>
                  <span class="subject-tag" style="font-size:12px; padding:4px 10px;">
                    ${escHtml(s.subject_name)}
                  </span>
                </td>
                <td>${escHtml(s.lecture)}</td>
                <td>
                  <span style="font-weight:600; color:var(--present-fg);">${s.present_count || 0}</span>
                  <span style="color:var(--text-muted);"> / ${s.total_count || 0}</span>
                </td>
                <td>
                  <div style="display:flex; align-items:center; gap:8px;">
                    <div style="
                      height:6px; width:80px; background:var(--border);
                      border-radius:100px; overflow:hidden;">
                      <div style="
                        height:100%; width:${pct}%;
                        background:${pctColor};
                        border-radius:100px;
                        transition: width 0.6s ease;">
                      </div>
                    </div>
                    <span style="font-size:12px; font-weight:600; color:${pctColor};">${pct}%</span>
                  </div>
                </td>
                <td>
                  <div style="display:flex; gap:6px;">
                    <button class="btn btn-ghost btn-sm" onclick="navigate('session', ${s.id})">
                      View
                    </button>
                    <a class="btn btn-ghost btn-sm"
                      href="/api/sessions/${s.id}/excel"
                      download
                      title="Download Excel for ${escHtml(s.subject_name)}">
                      ⬇ Excel
                    </a>
                  </div>
                </td>
              </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>`;
}

// ------------------------------------------------
// Session Detail
// ------------------------------------------------

async function renderSessionDetail(root, sessionId) {
  root.innerHTML = `
    <div style="padding:48px; text-align:center; color:var(--text-muted);">
      <div class="spinner spinner-dark" style="margin:0 auto 12px;"></div>
      Loading session…
    </div>`;

  try {
    const res = await apiGet(`/api/sessions/${sessionId}`);
    if (!res.ok) throw new Error(res.error);

    const { session, records } = res.data;
    const presentCount = records.filter(r => r.status === 'Present').length;
    const absentCount  = records.filter(r => r.status === 'Absent').length;
    const manualCount  = records.filter(r => r.manually_edited).length;
    const pct = records.length > 0
      ? Math.round((presentCount / records.length) * 100)
      : 0;

    root.innerHTML = `
      <div class="page-header-row" style="margin-bottom:20px;">
        <div class="page-header" style="margin-bottom:0;">
          <h1>${escHtml(session.subject_name)} — ${escHtml(session.lecture)}</h1>
          <p>${formatDate(session.date)} &nbsp;·&nbsp; ${formatTime(session.session_time)}</p>
        </div>
        <div style="display:flex; gap:10px;">
          <button class="btn btn-ghost" onclick="navigate('history')">← Back</button>
          <a class="btn btn-success" href="/api/sessions/${sessionId}/excel" download>
            ⬇ Download Excel
          </a>
        </div>
      </div>

      <!-- Stats row -->
      <div class="stat-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom:20px;">
        <div class="stat-card">
          <div class="stat-icon blue">👨‍🎓</div>
          <div class="stat-value">${records.length}</div>
          <div class="stat-label">Total Students</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon green">✅</div>
          <div class="stat-value" style="color:var(--present-fg);">${presentCount}</div>
          <div class="stat-label">Present</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon red">❌</div>
          <div class="stat-value" style="color:var(--absent-fg);">${absentCount}</div>
          <div class="stat-label">Absent</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon amber">📊</div>
          <div class="stat-value">${pct}%</div>
          <div class="stat-label">Attendance Rate</div>
        </div>
      </div>

      ${manualCount > 0 ? `
        <div style="
          background:hsl(38,90%,96%); border:1px solid hsl(38,80%,78%);
          border-radius:var(--radius-md); padding:10px 16px;
          font-size:13px; color:hsl(38,60%,30%); margin-bottom:16px;">
          ✎ ${manualCount} record(s) were manually corrected by the teacher.
        </div>` : ''}

      <!-- Attendance table -->
      <div class="card" style="padding:0; overflow:hidden;">
        <div class="table-wrapper" style="border:none; border-radius:0;">
          <table>
            <thead>
              <tr>
                <th>Roll No</th>
                <th>Student Name</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Manually Edited</th>
              </tr>
            </thead>
            <tbody>
              ${records.map(r => `
                <tr class="${r.manually_edited ? 'manually-edited' : ''}">
                  <td style="font-weight:700;">${escHtml(r.roll_no)}</td>
                  <td>${escHtml(r.name || r.roll_no)}</td>
                  <td>
                    <span class="badge ${r.status === 'Present' ? 'badge-present' : 'badge-absent'}">
                      ${r.status}
                    </span>
                  </td>
                  <td style="color:var(--text-secondary); font-variant-numeric:tabular-nums; font-size:13px;">
                    ${r.confidence != null ? parseFloat(r.confidence).toFixed(4) : '—'}
                  </td>
                  <td>
                    ${r.manually_edited
                      ? '<span style="color:hsl(38,70%,35%); font-size:12.5px; font-weight:600;">✎ Yes</span>'
                      : '<span style="color:var(--text-muted); font-size:12.5px;">—</span>'}
                  </td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>`;

  } catch (err) {
    root.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">⚠️</span>
        <div class="empty-title">Could not load session</div>
        <div class="empty-desc">${err.message}</div>
        <button class="btn btn-ghost mt-4" onclick="navigate('history')">← Back to History</button>
      </div>`;
  }
}
