/**
 * reviews.js — Review Analysis Agent page logic
 */

async function analyzeReviews() {
  const select = document.getElementById('productSelect');
  const productId = select.value;
  if (!productId) { toast('Please select a product.', 'warning'); return; }

  const btn = document.getElementById('analyzeBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner spinner-sm"></span> Analyzing…';

  showLoading('review-area', '⭐ Analyzing customer reviews…');

  try {
    const res = await apiGet(`/api/products/${productId}/reviews`);
    if (!res.success) throw new Error(res.error);

    const analysis = res.data;
    // Cache by product id
    const cached = Session.get(Keys.REVIEWS) || {};
    cached[productId] = analysis;
    Session.set(Keys.REVIEWS, cached);

    renderReview(analysis);
    toast('Review analysis complete!', 'success');
  } catch (e) {
    showError('review-area', e.message || 'Review analysis failed. Please try again.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '⭐ Analyse Reviews';
  }
}

function onProductSelected() {
  const select = document.getElementById('productSelect');
  document.getElementById('analyzeBtn').disabled = !select.value;

  // Show cached result if available
  const productId = select.value;
  const cached = Session.get(Keys.REVIEWS);
  if (cached && cached[productId]) {
    renderReview(cached[productId]);
  } else {
    document.getElementById('review-area').innerHTML = '';
  }
}

function renderReview(a) {
  const area = document.getElementById('review-area');
  const total = a.review_count || 0;

  const sentimentBadge = {
    Positive: 'badge-success', Negative: 'badge-danger', Mixed: 'badge-warning', Neutral: 'badge-gray'
  }[a.overall_sentiment] || 'badge-gray';

  const pct = (n) => total > 0 ? Math.round((n / total) * 100) : 0;

  const themeTag = (t, cls = 'badge-gray') => `<span class="badge ${cls}">${escHtml(t)}</span>`;

  area.innerHTML = `
    <div class="card" style="margin-bottom:20px">
      <div class="card-header">
        <div>
          <div class="card-title">${escHtml(a.product_name)}</div>
          <div style="margin-top:4px">${starsHtml(a.average_rating)} <span class="rating-num">${a.average_rating}</span></div>
        </div>
        <span class="badge ${sentimentBadge} badge-lg">${escHtml(a.overall_sentiment)}</span>
      </div>

      <!-- Stats Row -->
      <div class="stat-row">
        <div class="stat-box">
          <div class="stat-value">${total}</div>
          <div class="stat-label">Total Reviews</div>
        </div>
        <div class="stat-box">
          <div class="stat-value" style="color:var(--success)">${a.positive_count}</div>
          <div class="stat-label">Positive</div>
        </div>
        <div class="stat-box">
          <div class="stat-value" style="color:var(--text-muted)">${a.neutral_count}</div>
          <div class="stat-label">Neutral</div>
        </div>
        <div class="stat-box">
          <div class="stat-value" style="color:var(--danger)">${a.negative_count}</div>
          <div class="stat-label">Negative</div>
        </div>
      </div>

      <!-- Rating Distribution -->
      <div style="margin:8px 0 16px">
        <div style="display:flex;flex-direction:column;gap:8px">
          <div>
            <div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:4px">
              <span>😊 Positive</span><span style="color:var(--success)">${pct(a.positive_count)}%</span>
            </div>
            <div class="progress-bar"><div class="progress-fill success" style="width:${pct(a.positive_count)}%"></div></div>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:4px">
              <span>😐 Neutral</span><span style="color:var(--text-muted)">${pct(a.neutral_count)}%</span>
            </div>
            <div class="progress-bar"><div class="progress-fill" style="width:${pct(a.neutral_count)}%;background:var(--text-muted)"></div></div>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:4px">
              <span>😟 Negative</span><span style="color:var(--danger)">${pct(a.negative_count)}%</span>
            </div>
            <div class="progress-bar"><div class="progress-fill danger" style="width:${pct(a.negative_count)}%"></div></div>
          </div>
        </div>
      </div>

      <!-- Summary -->
      <div style="background:var(--bg);border-radius:var(--radius-sm);padding:16px;margin-bottom:16px">
        <div style="font-weight:700;margin-bottom:6px">💬 Review Summary</div>
        <p style="color:var(--text-muted);font-size:.9rem;line-height:1.6">${escHtml(a.summary)}</p>
      </div>

      <!-- Themes -->
      <div class="two-col">
        <div>
          <div style="font-weight:700;color:var(--success);margin-bottom:10px">😊 Customers Like</div>
          <div class="tags">
            ${a.positive_themes && a.positive_themes.length
              ? a.positive_themes.map(t => themeTag(t, 'badge-success')).join('')
              : '<span class="badge badge-gray">No data</span>'}
          </div>
          ${a.common_strengths && a.common_strengths.length ? `
            <div style="margin-top:12px">
              <div class="form-sublabel" style="margin-bottom:6px">Top Strengths</div>
              ${a.common_strengths.map(s => `<div class="rec-why-item">${escHtml(s)}</div>`).join('')}
            </div>` : ''}
        </div>
        <div>
          <div style="font-weight:700;color:var(--danger);margin-bottom:10px">⚠️ Common Concerns</div>
          <div class="tags">
            ${a.negative_themes && a.negative_themes.length
              ? a.negative_themes.map(t => themeTag(t, 'badge-danger')).join('')
              : '<span class="badge badge-success">No concerns reported</span>'}
          </div>
          ${a.common_complaints && a.common_complaints.length ? `
            <div style="margin-top:12px">
              <div class="form-sublabel" style="margin-bottom:6px">Common Complaints</div>
              ${a.common_complaints.map(c => `<div style="display:flex;gap:8px;font-size:.875rem;margin-bottom:6px"><span style="color:var(--warning)">⚠</span>${escHtml(c)}</div>`).join('')}
            </div>` : ''}
        </div>
      </div>
    </div>`;
}

function populateProductDropdown() {
  const products = Session.get(Keys.PRODUCTS) || [];
  const select = document.getElementById('productSelect');
  const selectedId = Session.get(Keys.SELECTED_PID);

  select.innerHTML = '<option value="">— Choose a product —</option>';
  products.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.product_id;
    opt.textContent = `${p.name} — ${formatINR(p.price_inr)}`;
    if (p.product_id === selectedId) opt.selected = true;
    select.appendChild(opt);
  });

  if (select.value) {
    document.getElementById('analyzeBtn').disabled = false;
    onProductSelected();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const products = Session.get(Keys.PRODUCTS);
  if (!products || !products.length) {
    document.getElementById('review-area').innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🔎</div>
        <div class="empty-title">No products yet</div>
        <p class="empty-desc">Please search for products first.</p>
        <a href="/pages/products.html" class="btn btn-primary" style="margin-top:12px">Go to Products</a>
      </div>`;
    return;
  }
  populateProductDropdown();
});
