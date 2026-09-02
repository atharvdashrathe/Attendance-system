/* ================================================
   take_attendance.js — Take Attendance page
   ================================================ */

let _uploadedFiles = [];   // File objects selected by teacher
let _subjectList   = [];   // [{id, name}]

async function renderTakeAttendance(root) {
  root.innerHTML = `
    <div class="page-header">
      <h1>Take Attendance</h1>
      <p>Upload 2–4 classroom photographs. The system will recognize all students across all images.</p>
    </div>

    <div style="display:grid; grid-template-columns: 1fr 420px; gap:24px; align-items:start;">

      <!-- Left: Form + Upload -->
      <div>
        <div class="card" style="margin-bottom:20px;">
          <div class="card-title mb-4" style="margin-bottom:18px;">Session Details</div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Subject <span>*</span></label>
              <select id="subject-select" class="form-control" onchange="onSubjectChange()">
                <option value="">— Select Subject —</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Lecture <span>*</span></label>
              <input type="text" id="lecture-input" class="form-control"
                placeholder="e.g. Lecture 12" maxlength="100" />
            </div>
          </div>
          <div class="form-group" style="max-width:220px;">
            <label class="form-label">Date <span>*</span></label>
            <input type="date" id="date-input" class="form-control" />
          </div>
          <div id="no-subjects-warn" style="display:none; color:var(--absent-fg); font-size:13px; margin-top:-8px; margin-bottom:12px;">
            ⚠ No subjects found. <a href="#" onclick="navigate('subjects')" style="color:var(--primary);">Add a subject first →</a>
          </div>
        </div>

        <div class="card">
          <div class="card-title" style="margin-bottom:4px;">Upload Classroom Images</div>
          <p style="font-size:12.5px; color:var(--text-secondary); margin-bottom:16px;">
            Upload 2–4 classroom photographs. All faces will be detected across all images.
          </p>

          <!-- Drop zone -->
          <div class="upload-zone" id="drop-zone"
            ondragover="onDragOver(event)"
            ondragleave="onDragLeave(event)"
            ondrop="onDrop(event)">
            <input type="file" id="file-input" accept="image/*" multiple
              onchange="onFileSelect(event)" />
            <span class="upload-icon">📷</span>
            <div class="upload-text">Drag & drop classroom photos here</div>
            <div class="upload-hint" style="margin-top:4px;">or click to browse &nbsp;·&nbsp; JPG, PNG, WEBP &nbsp;·&nbsp; Max 4 images</div>
          </div>

          <!-- Image previews -->
          <div class="preview-grid" id="preview-grid" style="display:none; margin-top:16px;"></div>

          <div id="upload-count-msg" style="font-size:12.5px; color:var(--text-secondary); margin-top:10px; display:none;"></div>

          <div id="upload-error" style="color:var(--absent-fg); font-size:13px; margin-top:10px; display:none;"></div>
        </div>
      </div>

      <!-- Right: Instructions + Process button -->
      <div>
        <div class="card" style="margin-bottom:20px;">
          <div class="card-title mb-4" style="margin-bottom:12px;">Processing Steps</div>
          <div id="progress-steps" class="progress-steps">
            ${['Upload classroom images','Detect all faces (YuNet)','Recognize students (SFace)','Remove duplicates','Generate attendance'].map((s,i) => `
              <div class="progress-step" id="step-${i}">
                <div class="step-icon">${i+1}</div>
                <span>${s}</span>
              </div>`).join('')}
          </div>
        </div>

        <div class="card">
          <div style="font-size:13px; color:var(--text-secondary); margin-bottom:16px; line-height:1.7;">
            <strong>📌 Requirements:</strong><br>
            • Select subject and lecture<br>
            • Upload at least 2 images<br>
            • Maximum 4 images per session<br>
            • Same student in multiple photos = counted once
          </div>
          <button class="btn btn-primary btn-lg" id="process-btn"
            onclick="processAttendance()" style="width:100%;">
            ▶ Process Attendance
          </button>
          <div id="process-error" style="color:var(--absent-fg); font-size:13px; margin-top:12px; display:none;"></div>
        </div>
      </div>

    </div>`;

  // Set today's date
  document.getElementById('date-input').value = todayISO();

  // Load subjects
  await loadSubjectsDropdown();
}

async function loadSubjectsDropdown() {
  const select = document.getElementById('subject-select');
  const warn = document.getElementById('no-subjects-warn');
  if (!select) return;

  try {
    const res = await apiGet('/api/subjects');
    if (!res.ok) throw new Error(res.error);
    _subjectList = res.data;

    select.innerHTML = '<option value="">— Select Subject —</option>' +
      _subjectList.map(s => `<option value="${s.id}" data-name="${escHtml(s.name)}">${escHtml(s.name)}</option>`).join('');

    if (_subjectList.length === 0) {
      warn.style.display = 'block';
    }
  } catch (err) {
    toast('Could not load subjects: ' + err.message, 'error');
  }
}

function onSubjectChange() {
  // Nothing special needed; name is taken from selected option
}

function onDragOver(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.add('drag-over');
}

function onDragLeave() {
  document.getElementById('drop-zone').classList.remove('drag-over');
}

function onDrop(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.remove('drag-over');
  const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'));
  addFiles(files);
}

function onFileSelect(e) {
  const files = Array.from(e.target.files);
  addFiles(files);
  // Reset input so same file can be re-selected after removal
  e.target.value = '';
}

function addFiles(files) {
  const errEl = document.getElementById('upload-error');
  errEl.style.display = 'none';

  const remaining = 4 - _uploadedFiles.length;
  if (remaining <= 0) {
    errEl.textContent = 'Maximum 4 images already selected.';
    errEl.style.display = 'block';
    return;
  }

  const toAdd = files.slice(0, remaining);
  _uploadedFiles.push(...toAdd);
  renderPreviews();
}

function removeFile(index) {
  _uploadedFiles.splice(index, 1);
  renderPreviews();
}

function renderPreviews() {
  const grid = document.getElementById('preview-grid');
  const countMsg = document.getElementById('upload-count-msg');

  if (_uploadedFiles.length === 0) {
    grid.style.display = 'none';
    countMsg.style.display = 'none';
    return;
  }

  grid.style.display = 'grid';
  grid.innerHTML = _uploadedFiles.map((file, i) => {
    const url = URL.createObjectURL(file);
    return `
      <div class="preview-item">
        <img src="${url}" alt="Image ${i+1}" />
        <button class="preview-remove" onclick="removeFile(${i})" title="Remove">✕</button>
        <div class="preview-label">Photo ${i+1}</div>
      </div>`;
  }).join('');

  countMsg.style.display = 'block';
  const color = _uploadedFiles.length >= 2 ? 'var(--present-fg)' : 'var(--absent-fg)';
  countMsg.innerHTML = `<span style="color:${color}; font-weight:600;">${_uploadedFiles.length}</span> / 4 images selected
    ${_uploadedFiles.length < 2 ? ' <span style="color:var(--absent-fg);">(minimum 2 required)</span>' : ''}`;
}

async function processAttendance() {
  const errEl = document.getElementById('process-error');
  errEl.style.display = 'none';

  // Validate
  const subjectSelect = document.getElementById('subject-select');
  const lecture = document.getElementById('lecture-input').value.trim();
  const date = document.getElementById('date-input').value;

  if (!subjectSelect.value) {
    errEl.textContent = 'Please select a subject.';
    errEl.style.display = 'block';
    return;
  }
  if (!lecture) {
    errEl.textContent = 'Please enter a lecture name/number.';
    errEl.style.display = 'block';
    return;
  }
  if (!date) {
    errEl.textContent = 'Please select a date.';
    errEl.style.display = 'block';
    return;
  }
  if (_uploadedFiles.length < 2) {
    errEl.textContent = 'Please upload at least 2 classroom images.';
    errEl.style.display = 'block';
    return;
  }

  const subjectId   = parseInt(subjectSelect.value);
  const subjectName = subjectSelect.options[subjectSelect.selectedIndex].dataset.name;

  // Save metadata to state
  State.pendingMeta = {
    subject_id:   subjectId,
    subject_name: subjectName,
    lecture:      lecture,
    date:         date,
    time:         currentTime()
  };

  // Animate progress steps
  const btn = document.getElementById('process-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Processing…';

  // Step 0 → done immediately
  setStep(0, 'done');

  // Build form data
  const formData = new FormData();
  _uploadedFiles.forEach(file => formData.append('images', file));

  try {
    // Step 1 active
    setStep(1, 'active');
    await sleep(400);

    // Step 2
    setStep(1, 'done');
    setStep(2, 'active');

    const res = await fetch('/api/attendance/process', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();

    if (!data.ok) throw new Error(data.error);

    setStep(2, 'done');
    setStep(3, 'active');
    await sleep(300);
    setStep(3, 'done');
    setStep(4, 'active');
    await sleep(300);
    setStep(4, 'done');

    // Store results
    State.pendingRecords = data.data.records;

    toast(`Processed ${data.data.images_processed} images — ${data.data.total_faces_detected} faces detected.`, 'success');

    // Navigate to preview
    setTimeout(() => navigate('preview'), 600);

  } catch (err) {
    errEl.textContent = 'Processing failed: ' + err.message;
    errEl.style.display = 'block';
    // Reset steps
    [0,1,2,3,4].forEach(i => setStep(i, ''));
    btn.disabled = false;
    btn.innerHTML = '▶ Process Attendance';
  }
}

function setStep(index, state) {
  const el = document.getElementById(`step-${index}`);
  if (!el) return;
  el.classList.remove('active', 'done');
  if (state) el.classList.add(state);
  const icon = el.querySelector('.step-icon');
  if (icon) icon.textContent = state === 'done' ? '✓' : index + 1;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
