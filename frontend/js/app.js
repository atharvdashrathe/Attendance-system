/* ================================================
   app.js — Router, global state, and utilities
   ================================================ */

const API = '';   // same-origin; Flask serves the frontend

// ---- Global state ----
const State = {
  pendingRecords: null,   // attendance records from /process
  pendingMeta: null,      // {subject_id, subject_name, lecture, date, time}
};

// ---- Navigation ----
const PAGE_TITLES = {
  dashboard: 'Dashboard',
  take:      'Take Attendance',
  preview:   'Attendance Preview',
  subjects:  'Manage Subjects',
  history:   'Attendance History',
  session:   'Session Detail',
  excel:     'Excel Downloads',
};

function navigate(page, params) {
  // Highlight active nav item
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const navEl = document.getElementById(`nav-${page}`);
  if (navEl) navEl.classList.add('active');

  // Update topbar title
  const titleEl = document.getElementById('topbar-title');
  if (titleEl) titleEl.textContent = PAGE_TITLES[page] || page;

  // Close sidebar on mobile
  document.getElementById('sidebar').classList.remove('open');

  // Render page
  const root = document.getElementById('app-root');

  switch (page) {
    case 'dashboard': renderDashboard(root); break;
    case 'take':      renderTakeAttendance(root); break;
    case 'preview':   renderPreview(root); break;
    case 'history':   renderHistory(root); break;
    case 'session':   renderSessionDetail(root, params); break;
    case 'subjects':  renderSubjects(root); break;
    case 'excel':     renderExcelDownloads(root); break;
    default:          root.innerHTML = '<div class="empty-state"><span class="empty-icon">❓</span><div class="empty-title">Page not found</div></div>';
  }
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ---- Live clock ----
function startClock() {
  const el = document.getElementById('topbar-clock');
  function tick() {
    const now = new Date();
    el.textContent = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  tick();
  setInterval(tick, 1000);
}

// ---- Toast ----
function toast(message, type = 'info') {
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.style.animation = 'slide-out 0.3s ease forwards';
    setTimeout(() => el.remove(), 320);
  }, 3500);
}

// ---- Modal ----
function showModal({ title, body, confirmText = 'Confirm', cancelText = 'Cancel', onConfirm, danger = false }) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-title">${title}</div>
      <div class="modal-body">${body}</div>
      <div class="modal-actions">
        <button class="btn btn-ghost" id="modal-cancel">${cancelText}</button>
        <button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" id="modal-confirm">${confirmText}</button>
      </div>
    </div>`;

  document.body.appendChild(overlay);

  overlay.querySelector('#modal-cancel').onclick = () => overlay.remove();
  overlay.querySelector('#modal-confirm').onclick = () => {
    overlay.remove();
    if (onConfirm) onConfirm();
  };

  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.remove();
  });
}

// ---- API helpers ----
async function apiGet(endpoint) {
  const res = await fetch(API + endpoint);
  return res.json();
}

async function apiPost(endpoint, data) {
  const res = await fetch(API + endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return res.json();
}

async function apiDelete(endpoint) {
  const res = await fetch(API + endpoint, { method: 'DELETE' });
  return res.json();
}

// ---- Date helpers ----
function todayISO() {
  const now = new Date();
  return now.toISOString().slice(0, 10);
}

function currentTime() {
  const now = new Date();
  return now.toTimeString().slice(0, 8);
}

function formatDate(d) {
  if (!d) return '—';
  const parts = d.split('-');
  if (parts.length !== 3) return d;
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${parseInt(parts[2])} ${months[parseInt(parts[1])-1]} ${parts[0]}`;
}

function formatTime(t) {
  if (!t) return '—';
  return t.slice(0, 5);
}

// ---- Bootstrap ----
window.addEventListener('DOMContentLoaded', () => {
  startClock();
  navigate('dashboard');
});
