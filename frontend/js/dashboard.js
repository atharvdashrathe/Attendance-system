/* ================================================
   dashboard.js — Dashboard page
   ================================================ */

async function renderDashboard(root) {
  root.innerHTML = `
    <div class="page-header">
      <h1>Dashboard</h1>
      <p>Welcome back. Here's a summary of today's attendance activity.</p>
    </div>

    <div class="stat-grid" id="stat-grid">
      ${[0,1,2,3].map(() => `
        <div class="stat-card">
          <div class="stat-icon blue" style="background:var(--border-light)"></div>
          <div class="stat-value" style="color:var(--border); background:var(--border-light); border-radius:8px; width:60px; height:36px;"></div>
          <div class="stat-label" style="color:var(--border-light); background:var(--border-light); border-radius:4px; width:80px; height:14px;"></div>
        </div>`).join('')}
    </div>

    <div class="card">
      <div class="flex justify-between items-center mb-4">
        <div>
          <div class="card-title">Recent Attendance Sessions</div>
          <div class="card-subtitle">Last 5 sessions</div>
        </div>
        <button class="btn btn-primary btn-sm" onclick="navigate('take')">
          + New Session
        </button>
      </div>
      <div class="table-wrapper" id="recent-table">
        <div style="padding:32px; text-align:center; color:var(--text-muted);">
          <div class="spinner spinner-dark" style="margin: 0 auto 12px;"></div>
          Loading…
        </div>
      </div>
    </div>`;

  try {
    const res = await apiGet('/api/dashboard');
    if (!res.ok) throw new Error(res.error);
    const d = res.data;

    // Stat cards
    document.getElementById('stat-grid').innerHTML = `
      <div class="stat-card">
        <div class="stat-icon blue">👨‍🎓</div>
        <div class="stat-value">${d.total_students}</div>
        <div class="stat-label">Registered Students</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon amber">📋</div>
        <div class="stat-value">${d.total_sessions}</div>
        <div class="stat-label">Total Sessions</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon green">📅</div>
        <div class="stat-value">${d.today_sessions}</div>
        <div class="stat-label">Today's Sessions</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon blue">🤖</div>
        <div class="stat-value" style="font-size:18px;">YuNet</div>
        <div class="stat-label">+ SFace Active</div>
      </div>`;

    // Recent table
    if (!d.recent_sessions || d.recent_sessions.length === 0) {
      document.getElementById('recent-table').innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">📋</span>
          <div class="empty-title">No sessions yet</div>
          <div class="empty-desc">Start by taking attendance</div>
          <button class="btn btn-primary mt-4" onclick="navigate('take')">Take Attendance</button>
        </div>`;
      return;
    }

    document.getElementById('recent-table').innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Time</th>
            <th>Subject</th>
            <th>Lecture</th>
            <th>Present</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${d.recent_sessions.map(s => `
            <tr>
              <td>${formatDate(s.date)}</td>
              <td>${formatTime(s.session_time)}</td>
              <td><span class="subject-tag" style="font-size:12px; padding:4px 10px;">${escHtml(s.subject_name)}</span></td>
              <td>${escHtml(s.lecture)}</td>
              <td>
                <span class="badge badge-present">${s.present_count || 0}</span>
                <span style="color:var(--text-muted); font-size:12px;"> / ${s.total_count || 0}</span>
              </td>
              <td>
                <button class="btn btn-ghost btn-sm" onclick="navigate('session', ${s.id})">View →</button>
              </td>
            </tr>`).join('')}
        </tbody>
      </table>`;

  } catch (err) {
    document.getElementById('stat-grid').innerHTML = `<div style="color:var(--absent-fg); padding:12px;">Failed to load: ${err.message}</div>`;
  }
}

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}
