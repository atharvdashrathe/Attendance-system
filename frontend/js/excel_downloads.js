/* ================================================
   excel_downloads.js — Excel Downloads page
   (registered as renderExcelDownloads in app.js)
   ================================================ */

async function renderExcelDownloads(root) {
  root.innerHTML = `
    <div class="page-header">
      <h1>Excel Downloads</h1>
      <p>Download subject-wise attendance Excel files. Each file contains one sheet per lecture.</p>
    </div>

    <div class="card" style="margin-bottom:20px; background:var(--primary-light);
      border-color:var(--primary-mid); padding:16px 20px;">
      <div style="display:flex; gap:12px; align-items:flex-start;">
        <span style="font-size:24px;">📊</span>
        <div>
          <div style="font-weight:600; color:var(--primary-dark); margin-bottom:4px;">File Structure</div>
          <div style="font-size:13px; color:var(--primary-dark); line-height:1.7;">
            <strong>DSA.xlsx</strong> → Sheet: "Lecture 1", Sheet: "Lecture 2", …<br>
            <strong>DBMS.xlsx</strong> → Sheet: "Lecture 1", Sheet: "Lecture 3", …<br>
            Each sheet contains: Roll No, Name, Date, Time, Status, Manually Edited
          </div>
        </div>
      </div>
    </div>

    <div id="excel-list-container">
      <div style="text-align:center; padding:48px; color:var(--text-muted);">
        <div class="spinner spinner-dark" style="margin:0 auto 12px;"></div>
        Loading files…
      </div>
    </div>`;

  await loadExcelList();
}

async function loadExcelList() {
  const container = document.getElementById('excel-list-container');
  if (!container) return;

  try {
    const res = await apiGet('/api/excel/list');
    if (!res.ok) throw new Error(res.error);
    const files = res.data;

    if (!files || files.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon">📂</span>
          <div class="empty-title">No Excel files yet</div>
          <div class="empty-desc">
            Excel files are created automatically when you finalize an attendance session.
          </div>
          <button class="btn btn-primary mt-4" onclick="navigate('take')">Take Attendance</button>
        </div>`;
      return;
    }

    container.innerHTML = files.map(f => `
      <div class="excel-file-card">
        <div class="excel-icon">📗</div>
        <div style="flex:1;">
          <div class="excel-file-name">${escHtml(f.filename)}</div>
          <div class="excel-file-sub">Subject: ${escHtml(f.subject)}</div>
        </div>
        <a class="btn btn-success btn-sm"
          href="/api/excel/download/${encodeURIComponent(f.filename)}"
          download="${escHtml(f.filename)}">
          ⬇ Download
        </a>
      </div>`).join('');

  } catch (err) {
    container.innerHTML = `<div style="padding:20px; color:var(--absent-fg);">Error: ${err.message}</div>`;
  }
}
