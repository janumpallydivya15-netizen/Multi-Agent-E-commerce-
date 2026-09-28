/**
 * requirements.js — Requirement Agent page logic
 */

const EXAMPLES = [
  'I want a smartphone under ₹100,000 with good battery life.',
  'I want a smartphone under ₹40,000.',
  'I want a laptop under ₹70,000 for programming with 16GB RAM and good battery life.',
  'I need wireless headphones with noise cancellation under ₹20,000.',
];

function setExample(idx) {
  document.getElementById('requestInput').value = EXAMPLES[idx];
}

async function analyzeRequirements() {
  const input = document.getElementById('requestInput');
  const query = input.value.trim();
  if (!query) { toast('Please enter your shopping request.', 'warning'); return; }

  const btn = document.getElementById('analyzeBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner spinner-sm"></span> Analyzing…';

  const area = document.getElementById('result-area');
  area.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p class="loading-text">🧠 Analyzing your requirements…</p>
    </div>`;

  try {
    const res = await apiPost('/api/requirements', { request: query });
    if (!res.success) throw new Error(res.error);

    const reqs = res.data;
    Session.set(Keys.REQUEST, query);
    Session.set(Keys.REQUIREMENTS, reqs);

    renderResult(reqs);
    document.getElementById('page-nav').style.display = 'flex';
    toast('Requirements analyzed!', 'success');
  } catch (e) {
    showError('result-area', e.message || 'Unable to analyze requirements. Please try again.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '🧠 Analyze Requirements';
  }
}

function renderResult(r) {
  const area = document.getElementById('result-area');
  const tag = (v) => v ? `<span class="badge badge-primary">${escHtml(v)}</span>` : '—';
  const tagList = (arr, cls = 'badge-gray') =>
    arr && arr.length ? arr.map(x => `<span class="badge ${cls}">${escHtml(x)}</span>`).join('') : '<span class="badge badge-gray">None</span>';

  area.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="card-title">📋 Extracted Requirements</div>
        <span class="badge badge-success">✓ Analyzed</span>
      </div>

      <div class="two-col" style="gap:32px">
        <div class="info-list">
          <div class="info-row">
            <span class="info-key">Category</span>
            <span class="info-val">${r.category ? `${categoryIcon(r.category)} ${r.category}` : '—'}</span>
          </div>
          <div class="info-row">
            <span class="info-key">Product Type</span>
            <span class="info-val">${escHtml(r.product_type || '—')}</span>
          </div>
          <div class="info-row">
            <span class="info-key">Budget</span>
            <span class="info-val" style="font-size:1.1rem;font-weight:800;color:var(--primary)">${r.budget ? formatINR(r.budget) : '—'}</span>
          </div>
          <div class="info-row">
            <span class="info-key">Currency</span>
            <span class="info-val">${escHtml(r.currency || 'INR')}</span>
          </div>
          <div class="info-row">
            <span class="info-key">Min Rating</span>
            <span class="info-val">${r.minimum_rating ? r.minimum_rating + ' ★' : '—'}</span>
          </div>
        </div>

        <div class="info-list">
          <div class="info-row" style="align-items:flex-start;flex-direction:column;gap:6px">
            <span class="info-key">Purpose</span>
            <div class="tags">${tagList(r.purpose, 'badge-info')}</div>
          </div>
          <div class="info-row" style="align-items:flex-start;flex-direction:column;gap:6px">
            <span class="info-key">Required Specs</span>
            <div class="tags">${tagList(r.important_specifications, 'badge-danger')}</div>
          </div>
          <div class="info-row" style="align-items:flex-start;flex-direction:column;gap:6px">
            <span class="info-key">Required Features</span>
            <div class="tags">${tagList(r.required_features, 'badge-warning')}</div>
          </div>
          <div class="info-row" style="align-items:flex-start;flex-direction:column;gap:6px">
            <span class="info-key">Preferred Features</span>
            <div class="tags">${tagList(r.preferred_features, 'badge-gray')}</div>
          </div>
          <div class="info-row" style="align-items:flex-start;flex-direction:column;gap:6px">
            <span class="info-key">Preferred Brands</span>
            <div class="tags">${tagList(r.preferred_brands, 'badge-primary')}</div>
          </div>
        </div>
      </div>
    </div>`;
}

// On page load — restore any existing session data
document.addEventListener('DOMContentLoaded', () => {
  const req = Session.get(Keys.REQUEST);
  const reqs = Session.get(Keys.REQUIREMENTS);
  if (req) document.getElementById('requestInput').value = req;
  if (reqs) {
    renderResult(reqs);
    document.getElementById('page-nav').style.display = 'flex';
  }
});
