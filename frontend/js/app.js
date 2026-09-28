/**
 * app.js — Shared utilities, navigation, sessionStorage helpers, API client
 */

// ── Navigation Config ──────────────────────────────────────────────────────
const NAV_ITEMS = [
  { icon: '🏠', label: 'Home',            href: '/' },
  { icon: '🧠', label: 'Requirements',   href: '/pages/requirements.html' },
  { icon: '🔎', label: 'Products',        href: '/pages/products.html' },
  { icon: '⭐', label: 'Reviews',         href: '/pages/reviews.html' },
  { icon: '⚖️', label: 'Compare',        href: '/pages/compare.html' },
  { icon: '🎯', label: 'Recommendations', href: '/pages/recommendations.html' },
  { icon: '🤖', label: 'AI Workflow',     href: '/pages/workflow.html' },
];

// ── Render Navigation ──────────────────────────────────────────────────────
function renderNav() {
  const currentPath = window.location.pathname;

  const html = `
  <nav class="nav">
    <div class="nav-inner">
      <a href="/" class="nav-brand">
        <span>🛍️</span> Multi-Agent E-Commerce
      </a>
      <div class="nav-links" id="navLinks">
        ${NAV_ITEMS.map(item => {
          const isActive = (item.href === '/' && (currentPath === '/' || currentPath === '/index.html'))
            || (item.href !== '/' && currentPath.endsWith(item.href.replace(/^\/pages\//, '')));
          return `<a href="${item.href}" class="nav-link ${isActive ? 'active' : ''}">
            <span class="icon">${item.icon}</span>${item.label}
          </a>`;
        }).join('')}
      </div>
      <button class="nav-hamburger" id="hamburger" aria-label="Menu" onclick="toggleMobileNav()">☰</button>
    </div>
  </nav>
  <div class="nav-mobile" id="mobileNav">
    ${NAV_ITEMS.map(item => {
      const isActive = (item.href === '/' && (currentPath === '/' || currentPath === '/index.html'))
        || (item.href !== '/' && currentPath.endsWith(item.href.replace(/^\/pages\//, '')));
      return `<a href="${item.href}" class="nav-link ${isActive ? 'active' : ''}">
        <span class="icon">${item.icon}</span>${item.label}
      </a>`;
    }).join('')}
  </div>`;

  const container = document.getElementById('nav-container');
  if (container) container.innerHTML = html;
}

function toggleMobileNav() {
  const nav = document.getElementById('mobileNav');
  if (nav) nav.classList.toggle('open');
}

// ── API Client ─────────────────────────────────────────────────────────────
const API_BASE = '';  // same origin

async function apiFetch(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const json = await res.json();
  return json;
}

async function apiPost(path, body) {
  return apiFetch(path, { method: 'POST', body: JSON.stringify(body) });
}

async function apiGet(path) {
  return apiFetch(path, { method: 'GET' });
}

// ── Session Storage Helpers ────────────────────────────────────────────────
const Session = {
  get: (key) => {
    try { return JSON.parse(sessionStorage.getItem(key)); }
    catch { return null; }
  },
  set: (key, val) => {
    try { sessionStorage.setItem(key, JSON.stringify(val)); }
    catch (e) { console.warn('sessionStorage write failed', e); }
  },
  clear: (key) => sessionStorage.removeItem(key),
  clearAll: () => sessionStorage.clear(),
};

const Keys = {
  REQUEST:        'shoppingRequest',
  REQUIREMENTS:   'requirements',
  PRODUCTS:       'products',
  SELECTED_PID:   'selectedProductId',
  REVIEWS:        'reviews',
  COMPARE_IDS:    'compareProductIds',
  COMPARISON:     'comparison',
  RECOMMENDATIONS:'recommendations',
};

// ── UI Helpers ─────────────────────────────────────────────────────────────
function showLoading(containerId, text = 'Loading...') {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p class="loading-text">${text}</p>
    </div>`;
}

function showError(containerId, message) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `
    <div class="error-state">
      <div class="error-icon">❌</div>
      <div class="error-body">
        <div class="error-title">Something went wrong</div>
        <div class="error-msg">${escHtml(message)}</div>
      </div>
    </div>`;
}

function showEmpty(containerId, { icon = '📭', title = 'No results', desc = '' } = {}) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">${icon}</div>
      <div class="empty-title">${title}</div>
      <p class="empty-desc">${desc}</p>
    </div>`;
}

// ── Toast Notifications ────────────────────────────────────────────────────
(function setupToast() {
  const container = document.createElement('div');
  container.className = 'toast-container';
  container.id = 'toast-container';
  document.body.appendChild(container);
})();

function toast(message, type = '', duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = message;
  container.appendChild(t);
  requestAnimationFrame(() => { requestAnimationFrame(() => { t.classList.add('show'); }); });
  setTimeout(() => {
    t.classList.remove('show');
    setTimeout(() => t.remove(), 300);
  }, duration);
}

// ── Formatters ─────────────────────────────────────────────────────────────
function formatINR(amount) {
  if (amount == null) return '—';
  return '₹' + Number(amount).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function starsHtml(rating, maxStars = 5) {
  let html = '<span class="stars">';
  for (let i = 1; i <= maxStars; i++) {
    if (rating >= i) html += '<span class="star filled">★</span>';
    else if (rating >= i - 0.5) html += '<span class="star half">★</span>';
    else html += '<span class="star">★</span>';
  }
  html += '</span>';
  return html;
}

function categoryIcon(cat) {
  const map = { Smartphones: '📱', Laptops: '💻', Headphones: '🎧', Smartwatches: '⌚' };
  return map[cat] || '📦';
}

function budgetBadge(withinBudget) {
  return withinBudget
    ? `<span class="badge badge-success">✓ Within Budget</span>`
    : `<span class="badge badge-danger">⚠ Over Budget</span>`;
}

function renderSpecList(specs, limit = 4) {
  if (!specs || typeof specs !== 'object') return '';
  const entries = Object.entries(specs).slice(0, limit);
  return entries.map(([k, v]) => `
    <div class="spec-row">
      <span class="spec-key">${escHtml(k)}</span>
      <span class="spec-val">${escHtml(String(v))}</span>
    </div>`).join('');
}

// ── Context Bar (show current requirements) ────────────────────────────────
function renderContextBar(containerId) {
  const reqs = Session.get(Keys.REQUIREMENTS);
  const el = document.getElementById(containerId);
  if (!el || !reqs) return;
  const parts = [];
  if (reqs.category) parts.push(`<span class="badge badge-primary">${reqs.category}</span>`);
  if (reqs.budget)   parts.push(`<span class="badge badge-gray">Budget: ${formatINR(reqs.budget)}</span>`);
  if (reqs.purpose && reqs.purpose.length) parts.push(`<span class="badge badge-info">Purpose: ${reqs.purpose.join(', ')}</span>`);
  el.innerHTML = `
    <div class="context-bar">
      <span class="context-label">Current Search:</span>
      <div style="display:flex;gap:8px;flex-wrap:wrap">${parts.join('')}</div>
    </div>`;
}

// ── Initialize ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  renderNav();
});
