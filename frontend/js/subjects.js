/* ================================================
   subjects.js — Manage Subjects page
   ================================================ */

async function renderSubjects(root) {
  root.innerHTML = `
    <div class="page-header-row">
      <div class="page-header" style="margin-bottom:0">
        <h1>Manage Subjects</h1>
        <p>Add or remove subjects. They will appear in the Take Attendance dropdown.</p>
      </div>
    </div>

    <div style="display:grid; grid-template-columns: 380px 1fr; gap:24px; margin-top:24px; align-items:start;">

      <!-- Add Subject Form -->
      <div class="card">
        <div class="card-title mb-4">Add New Subject</div>
        <div class="form-group">
          <label class="form-label">Subject Name <span>*</span></label>
          <input type="text" id="subject-input" class="form-control"
            placeholder="e.g. Data Structures, DBMS…"
            maxlength="100" autocomplete="off" />
        </div>
        <button class="btn btn-primary" id="add-subject-btn" onclick="addSubject()" style="width:100%;">
          + Add Subject
        </button>
        <div id="add-subject-error" style="color:var(--absent-fg); font-size:12.5px; margin-top:10px; display:none;"></div>
      </div>

      <!-- Subject List -->
      <div class="card">
        <div class="flex justify-between items-center mb-4">
          <div class="card-title">Current Subjects</div>
          <span id="subject-count" class="badge" style="background:var(--primary-light); color:var(--primary-dark);">—</span>
        </div>
        <div id="subjects-list">
          <div style="text-align:center; padding:32px; color:var(--text-muted);">
            <div class="spinner spinner-dark" style="margin:0 auto 12px;"></div>
            Loading…
          </div>
        </div>
      </div>
    </div>`;

  // Allow Enter key to add subject
  document.getElementById('subject-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') addSubject();
  });

  await loadSubjectsList();
}

async function loadSubjectsList() {
  const list = document.getElementById('subjects-list');
  const countEl = document.getElementById('subject-count');
  if (!list) return;

  try {
    const res = await apiGet('/api/subjects');
    if (!res.ok) throw new Error(res.error);
    const subjects = res.data;

    if (countEl) countEl.textContent = subjects.length;

    if (subjects.length === 0) {
      list.innerHTML = `
        <div class="empty-state" style="padding:32px 0;">
          <span class="empty-icon">📚</span>
          <div class="empty-title">No subjects yet</div>
          <div class="empty-desc">Add your first subject using the form on the left.</div>
        </div>`;
      return;
    }

    list.innerHTML = subjects.map(s => `
      <div class="flex items-center justify-between" style="
        padding: 12px 16px;
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        margin-bottom: 8px;
        background: var(--surface-2);
        transition: box-shadow var(--transition);"
        onmouseenter="this.style.boxShadow='var(--shadow-sm)'"
        onmouseleave="this.style.boxShadow='none'"
      >
        <div style="display:flex; align-items:center; gap:10px;">
          <span style="font-size:18px;">📖</span>
          <span style="font-weight:600; font-size:14px;">${escHtml(s.name)}</span>
        </div>
        <button class="btn btn-ghost btn-sm" style="color:var(--absent-fg); border-color:var(--absent-border);"
          onclick="deleteSubject(${s.id}, '${escHtml(s.name)}')">
          Remove
        </button>
      </div>`).join('');

  } catch (err) {
    list.innerHTML = `<div style="color:var(--absent-fg); padding:12px;">Error: ${err.message}</div>`;
  }
}

async function addSubject() {
  const input = document.getElementById('subject-input');
  const btn = document.getElementById('add-subject-btn');
  const errEl = document.getElementById('add-subject-error');
  const name = input.value.trim();

  if (!name) {
    errEl.textContent = 'Please enter a subject name.';
    errEl.style.display = 'block';
    input.focus();
    return;
  }

  errEl.style.display = 'none';
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Adding…';

  try {
    const res = await apiPost('/api/subjects', { name });
    if (!res.ok) throw new Error(res.error);
    input.value = '';
    toast(`Subject "${name}" added successfully.`, 'success');
    await loadSubjectsList();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.innerHTML = '+ Add Subject';
  }
}

async function deleteSubject(id, name) {
  showModal({
    title: 'Remove Subject',
    body: `Are you sure you want to remove <strong>${escHtml(name)}</strong>?<br><br>
           <span style="color:var(--absent-fg); font-size:13px;">
             ⚠ This will not delete historical attendance records for this subject.
           </span>`,
    confirmText: 'Remove',
    danger: true,
    onConfirm: async () => {
      try {
        const res = await apiDelete(`/api/subjects/${id}`);
        if (!res.ok) throw new Error(res.error);
        toast(`Subject "${name}" removed.`, 'info');
        await loadSubjectsList();
      } catch (err) {
        toast(`Error: ${err.message}`, 'error');
      }
    }
  });
}
