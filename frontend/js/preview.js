/* ================================================
   preview.js — Attendance Preview + Finalize page
   ================================================ */

function renderPreview(root) {
  if (!State.pendingRecords || !State.pendingMeta) {
    root.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">⚠️</span>
        <div class="empty-title">No attendance data to preview</div>
        <div class="empty-desc">Please process images first.</div>
        <button class="btn btn-primary mt-4" onclick="navigate('take')">Take Attendance</button>
      </div>`;
    return;
  }

  const meta = State.pendingMeta;
  const records = State.pendingRecords;  // array; we'll track edits in-place

  const presentCount = records.filter(r => r.status === 'Present').length;
  const absentCount  = records.filter(r => r.status === 'Absent').length;
  const pct = records.length > 0 ? Math.round((presentCount / records.length) * 100) : 0;

  root.innerHTML = `
    <div class="page-header-row">
      <div class="page-header" style="margin-bottom:0;">
        <h1>Attendance Preview</h1>
        <p>Review and correct the AI results before finalizing.</p>
      </div>
      <div style="display:flex; gap:10px;">
        <button class="btn btn-ghost" onclick="navigate('take')">← Back</button>
        <button class="btn btn-success btn-lg" onclick="confirmFinalize()">
          ✓ Finalize Attendance
        </button>
      </div>
    </div>

    <!-- Session meta -->
    <div class="card" style="margin-bottom:20px;">
      <div class="session-meta">
        <div class="session-meta-item">
          <span class="session-meta-label">Subject</span>
          <span class="session-meta-value">${escHtml(meta.subject_name)}</span>
        </div>
        <div class="session-meta-item">
          <span class="session-meta-label">Lecture</span>
          <span class="session-meta-value">${escHtml(meta.lecture)}</span>
        </div>
        <div class="session-meta-item">
          <span class="session-meta-label">Date</span>
          <span class="session-meta-value">${formatDate(meta.date)}</span>
        </div>
        <div class="session-meta-item">
          <span class="session-meta-label">Time</span>
          <span class="session-meta-value">${formatTime(meta.time)}</span>
        </div>
        <div class="session-meta-item" style="margin-left:auto;">
          <span class="session-meta-label">Attendance</span>
          <span class="session-meta-value" id="live-pct">
            <span style="color:var(--present-fg);">${presentCount} Present</span>
            &nbsp;·&nbsp;
            <span style="color:var(--absent-fg);">${absentCount} Absent</span>
            &nbsp;·&nbsp; ${pct}%
          </span>
        </div>
      </div>
    </div>

    <!-- AI notice -->
    <div style="
      background: hsl(38,90%,96%);
      border: 1px solid hsl(38,80%,78%);
      border-radius: var(--radius-md);
      padding: 12px 16px;
      font-size: 13px;
      color: hsl(38,60%,30%);
      margin-bottom:16px;
      display:flex; gap:10px; align-items:flex-start;">
      <span style="font-size:18px; flex-shrink:0;">💡</span>
      <span>The AI recognition may make mistakes. <strong>Review every row</strong> and use the
        <strong>Present / Absent</strong> buttons to correct errors before finalizing.</span>
    </div>

    <!-- Attendance table -->
    <div class="card" style="padding:0; overflow:hidden;">
      <div class="table-wrapper" style="border:none; border-radius:0;">
        <table id="preview-table">
          <thead>
            <tr>
              <th>Roll No</th>
              <th>Student Name</th>
              <th>Status</th>
              <th>Confidence</th>
              <th>Mark Attendance</th>
            </tr>
          </thead>
          <tbody id="preview-tbody">
            ${records.map((rec, i) => renderPreviewRow(rec, i)).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Bottom finalize button -->
    <div style="display:flex; justify-content:flex-end; margin-top:20px; gap:10px;">
      <button class="btn btn-ghost" onclick="navigate('take')">← Back</button>
      <button class="btn btn-success btn-lg" onclick="confirmFinalize()">
        ✓ Finalize Attendance
      </button>
    </div>`;
}

function renderPreviewRow(rec, i) {
  const isPresent  = rec.status === 'Present';
  const isAbsent   = rec.status === 'Absent';
  const isManual   = rec.manually_edited;

  return `
    <tr id="preview-row-${i}" class="${isManual ? 'manually-edited' : ''}">
      <td style="font-weight:700;">${escHtml(rec.roll_no)}</td>
      <td>${escHtml(rec.name || rec.roll_no)}</td>
      <td>
        <span class="badge ${isPresent ? 'badge-present' : 'badge-absent'}" id="badge-${i}">
          ${rec.status}
        </span>
        ${isManual ? '<span title="Manually edited" style="margin-left:6px; font-size:11px; color:hsl(38,80%,40%);">✎ Edited</span>' : ''}
      </td>
      <td style="color:var(--text-secondary); font-variant-numeric: tabular-nums; font-size:13px;">
        ${rec.confidence != null ? rec.confidence.toFixed(4) : '—'}
      </td>
      <td>
        <div class="status-toggle">
          <button id="btn-present-${i}"
            class="${isPresent ? 'active-present' : ''}"
            onclick="setStatus(${i}, 'Present')">
            Present
          </button>
          <button id="btn-absent-${i}"
            class="${isAbsent ? 'active-absent' : ''}"
            onclick="setStatus(${i}, 'Absent')">
            Absent
          </button>
        </div>
      </td>
    </tr>`;
}

function setStatus(index, status) {
  const rec = State.pendingRecords[index];
  const wasManual = rec.manually_edited;

  // Detect if teacher is manually changing the model's result
  if (rec.status !== status) {
    rec.status = status;
    rec.manually_edited = true;
  }

  // Update badge
  const badge = document.getElementById(`badge-${index}`);
  badge.className = `badge ${status === 'Present' ? 'badge-present' : 'badge-absent'}`;
  badge.innerHTML = status + (rec.manually_edited ? ' <span title="Manually edited" style="font-size:10px;">✎</span>' : '');

  // Update toggle buttons
  const btnP = document.getElementById(`btn-present-${index}`);
  const btnA = document.getElementById(`btn-absent-${index}`);
  if (btnP) { btnP.className = status === 'Present' ? 'active-present' : ''; }
  if (btnA) { btnA.className = status === 'Absent'  ? 'active-absent'  : ''; }

  // Update row class
  const row = document.getElementById(`preview-row-${index}`);
  if (row) {
    row.className = rec.manually_edited ? 'manually-edited' : '';
  }

  // Update live stats
  updateLiveStats();
}

function updateLiveStats() {
  const records = State.pendingRecords;
  const presentCount = records.filter(r => r.status === 'Present').length;
  const absentCount  = records.filter(r => r.status === 'Absent').length;
  const pct = records.length > 0 ? Math.round((presentCount / records.length) * 100) : 0;

  const el = document.getElementById('live-pct');
  if (el) el.innerHTML = `
    <span style="color:var(--present-fg);">${presentCount} Present</span>
    &nbsp;·&nbsp;
    <span style="color:var(--absent-fg);">${absentCount} Absent</span>
    &nbsp;·&nbsp; ${pct}%`;
}

function confirmFinalize() {
  const meta = State.pendingMeta;
  const records = State.pendingRecords;
  const presentCount = records.filter(r => r.status === 'Present').length;
  const manualCount  = records.filter(r => r.manually_edited).length;

  showModal({
    title: 'Finalize Attendance',
    body: `
      <strong>Subject:</strong> ${escHtml(meta.subject_name)}<br>
      <strong>Lecture:</strong> ${escHtml(meta.lecture)}<br>
      <strong>Date:</strong> ${formatDate(meta.date)}<br><br>
      <strong>${presentCount}</strong> students Present &nbsp;·&nbsp; <strong>${records.length - presentCount}</strong> Absent<br>
      ${manualCount > 0 ? `<span style="color:hsl(38,70%,35%);">✎ ${manualCount} record(s) manually corrected</span><br>` : ''}
      <br>
      This will save to the database and update the Excel file for
      <strong>${escHtml(meta.subject_name)}.xlsx</strong> → <em>${escHtml(meta.lecture)}</em> sheet.<br><br>
      <strong>This action cannot be undone.</strong>`,
    confirmText: 'Finalize',
    cancelText: 'Review Again',
    onConfirm: finalizeAttendance
  });
}

async function finalizeAttendance() {
  const meta = State.pendingMeta;
  const records = State.pendingRecords;

  // Show loading overlay
  const root = document.getElementById('app-root');
  root.insertAdjacentHTML('beforeend', `
    <div id="finalize-overlay" style="
      position:fixed; inset:0; background:rgba(0,0,0,0.4);
      display:flex; align-items:center; justify-content:center; z-index:999;">
      <div class="card" style="text-align:center; padding:40px 48px;">
        <div class="spinner spinner-dark" style="margin:0 auto 16px; width:36px; height:36px; border-width:3px;"></div>
        <div style="font-size:15px; font-weight:600;">Saving attendance…</div>
        <div style="font-size:13px; color:var(--text-secondary); margin-top:6px;">Updating database & Excel file</div>
      </div>
    </div>`);

  try {
    const payload = {
      subject_id:   meta.subject_id,
      subject_name: meta.subject_name,
      lecture:      meta.lecture,
      date:         meta.date,
      time:         meta.time,
      records:      records.map(r => ({
        roll_no:        r.roll_no,
        status:         r.status,
        confidence:     r.confidence,
        manually_edited: r.manually_edited || false
      }))
    };

    const res = await apiPost('/api/attendance/finalize', payload);
    if (!res.ok) throw new Error(res.error);

    document.getElementById('finalize-overlay')?.remove();

    // Show success page
    root.innerHTML = `
      <div style="max-width:520px; margin:80px auto; text-align:center;">
        <div style="font-size:72px; margin-bottom:20px;">✅</div>
        <h1 style="font-size:24px; font-weight:800; margin-bottom:8px;">Attendance Finalized!</h1>
        <p style="color:var(--text-secondary); margin-bottom:32px; font-size:15px;">
          ${escHtml(meta.subject_name)} — ${escHtml(meta.lecture)} &nbsp;·&nbsp; ${formatDate(meta.date)}
        </p>
        <div class="stat-grid" style="max-width:400px; margin:0 auto 32px;">
          <div class="stat-card" style="text-align:center;">
            <div class="stat-value" style="color:var(--present-fg);">${records.filter(r=>r.status==='Present').length}</div>
            <div class="stat-label">Present</div>
          </div>
          <div class="stat-card" style="text-align:center;">
            <div class="stat-value" style="color:var(--absent-fg);">${records.filter(r=>r.status==='Absent').length}</div>
            <div class="stat-label">Absent</div>
          </div>
        </div>
        <div style="display:flex; gap:12px; justify-content:center; flex-wrap:wrap;">
          <button class="btn btn-outline" onclick="navigate('history')">View History</button>
          <a class="btn btn-success" href="/api/sessions/${res.session_id}/excel" download>
            ⬇ Download Excel
          </a>
          <button class="btn btn-primary" onclick="startNewSession()">+ New Session</button>
        </div>
      </div>`;

    // Clear state
    State.pendingRecords = null;
    State.pendingMeta    = null;
    _uploadedFiles       = [];

  } catch (err) {
    document.getElementById('finalize-overlay')?.remove();
    toast('Finalization failed: ' + err.message, 'error');
  }
}

function startNewSession() {
  State.pendingRecords = null;
  State.pendingMeta    = null;
  _uploadedFiles       = [];
  navigate('take');
}
