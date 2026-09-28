/**
 * products.js — Product Search Agent page logic
 */

let allProducts = [];
let strictProducts = [];
let overBudgetProducts = [];

async function searchProducts(relaxed = false) {
  const reqs = Session.get(Keys.REQUIREMENTS);
  if (!reqs) {
    toast('Please analyze your requirements first.', 'warning');
    window.location.href = '/pages/requirements.html';
    return;
  }

  const btn = document.getElementById('searchBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner spinner-sm"></span> Searching…';

  showLoading('products-area', '🔎 Searching products…');
  document.getElementById('compare-bar').style.display = 'none';

  try {
    const res = await apiPost('/api/products/search', { requirements: reqs, relaxed_budget: relaxed });
    if (!res.success) throw new Error(res.error);

    allProducts = res.data.products || [];
    strictProducts = res.data.strict_matches || allProducts.filter(p => !reqs.budget || p.price_inr <= reqs.budget);
    overBudgetProducts = res.data.over_budget_candidates || allProducts.filter(p => reqs.budget && p.price_inr > reqs.budget);

    Session.set(Keys.PRODUCTS, allProducts);

    if (strictProducts.length === 0 && !relaxed) {
      // No strict matches — show option to search relaxed or auto-retry
      renderNoStrict();
    } else {
      renderProductsData(strictProducts, overBudgetProducts, reqs.budget, relaxed);
      renderCompareBar();
    }
  } catch (e) {
    showError('products-area', e.message || 'Product search failed. Please try again.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '🔎 Search Products';
  }
}

function renderNoStrict() {
  const area = document.getElementById('products-area');
  area.innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <div style="display:flex;align-items:flex-start;gap:12px">
        <div style="font-size:1.8rem">⚠️</div>
        <div>
          <div style="font-weight:700;font-size:1rem;margin-bottom:6px">No products meet your exact budget</div>
          <p style="color:var(--text-muted);font-size:.9rem">No products fit strictly within your budget and category. We can show over-budget alternatives — or try adjusting your requirements.</p>
        </div>
      </div>
      <div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn btn-primary" onclick="searchProducts(true)">Show Over-Budget Alternatives</button>
        <button class="btn btn-ghost" onclick="window.location.href='/pages/requirements.html'">← Change Requirements</button>
      </div>
    </div>`;
}

function renderProductsData(stricts, overBudgets, budget, relaxed) {
  const area = document.getElementById('products-area');

  if (!stricts.length && !overBudgets.length) {
    showEmpty('products-area', {
      icon: '📭',
      title: 'No products found',
      desc: 'Try adjusting your requirements or budget.'
    });
    return;
  }

  let html = '';

  if (stricts.length > 0) {
    html += `<div class="success-banner" style="margin-bottom:16px">✓ Found ${stricts.length} matching product${stricts.length !== 1 ? 's' : ''}</div>`;
    html += `<div class="card-grid">${stricts.map(p => productCardHtml(p, budget)).join('')}</div>`;

    if (overBudgets.length > 0) {
      html += `
        <div style="margin-top:32px;margin-bottom:16px">
          <div style="font-weight:700;font-size:1.1rem;color:var(--text);margin-bottom:6px">Closest Alternatives — Over Budget</div>
          <div class="card-grid">${overBudgets.map(p => productCardHtml(p, budget)).join('')}</div>
        </div>`;
    }
  } else {
    // Zero strict matches, but overBudget products exist
    html += `<div class="card" style="margin-bottom:20px;border-left:4px solid var(--warning)">
      <div style="font-weight:700;font-size:1.05rem;color:var(--warning-dark);margin-bottom:4px">⚠️ No products meet your budget</div>
      <p style="color:var(--text-muted);font-size:.9rem">Showing closest alternatives that exceed your requested budget.</p>
    </div>`;
    html += `<div style="font-weight:700;font-size:1.1rem;color:var(--text);margin-bottom:16px">Closest Alternatives — Over Budget</div>`;
    html += `<div class="card-grid">${overBudgets.map(p => productCardHtml(p, budget)).join('')}</div>`;
  }

  area.innerHTML = html;
}

function productCardHtml(p, budget) {
  const overBudget = budget && p.price_inr > budget;
  const priceBadge = overBudget
    ? `<span class="badge badge-danger">⚠ Over Budget</span>`
    : (budget ? `<span class="badge badge-success">✓ Within Budget</span>` : '');
  const overAmt = overBudget ? `<div style="font-size:.78rem;color:var(--danger);margin-top:2px">Over by ${formatINR(p.price_inr - budget)}</div>` : '';

  return `
  <div class="product-card">
    <div class="product-card-img">${categoryIcon(p.category)}</div>
    <div class="product-card-body">
      <div class="product-card-brand">${escHtml(p.brand)}</div>
      <div class="product-card-name">${escHtml(p.name)}</div>
      <div class="product-card-meta">
        ${priceBadge}
        <span class="badge badge-gray">${escHtml(p.category)}</span>
      </div>
      <div style="display:flex;align-items:baseline;gap:8px;margin-top:4px">
        <div class="product-card-price">${formatINR(p.price_inr)}</div>
        ${overAmt}
      </div>
      <div class="rating-row">
        ${starsHtml(p.rating)}
        <span class="rating-num">${p.rating}</span>
        <span class="rating-count">(${p.review_count} reviews)</span>
      </div>
      <div class="product-card-specs">
        ${renderSpecList(p.specifications, 3)}
      </div>
      ${p.match_reason ? `<div style="font-size:.78rem;color:var(--text-muted);margin-top:4px;font-style:italic">${escHtml(p.match_reason)}</div>` : ''}
    </div>
    <div class="product-card-actions">
      <button class="btn btn-secondary btn-sm" onclick="viewReviews('${escHtml(p.product_id)}')">⭐ Reviews</button>
      <button class="btn btn-ghost btn-sm" onclick="addToCompare('${escHtml(p.product_id)}')">⚖️ Compare</button>
    </div>
  </div>`;
}

function renderCompareBar() {
  const bar = document.getElementById('compare-bar');
  const list = document.getElementById('compare-checkboxes');
  if (!allProducts.length) return;

  const reqs = Session.get(Keys.REQUIREMENTS);
  const budget = reqs && reqs.budget;

  bar.style.display = 'block';
  const savedIds = Session.get(Keys.COMPARE_IDS) || [];

  list.innerHTML = allProducts.map(p => {
    const overBudget = budget && p.price_inr > budget;
    const checked = savedIds.includes(p.product_id) ? 'checked' : '';
    return `
      <label class="checkbox-item">
        <input type="checkbox" value="${escHtml(p.product_id)}" ${checked}
          onchange="updateCompareSelection()">
        <span>${escHtml(p.name)}</span>
        <span style="margin-left:auto;color:var(--text-muted);font-size:.85rem">${formatINR(p.price_inr)}</span>
        ${overBudget ? '<span class="badge badge-danger">Over Budget</span>' : ''}
      </label>`;
  }).join('');

  updateCompareSelection();
}

function updateCompareSelection() {
  const checks = document.querySelectorAll('#compare-checkboxes input[type="checkbox"]:checked');
  const ids = Array.from(checks).map(c => c.value);
  Session.set(Keys.COMPARE_IDS, ids);

  const countEl = document.getElementById('compare-count');
  const btn = document.getElementById('goCompareBtn');
  if (countEl) countEl.textContent = `${ids.length} selected`;
  if (btn) btn.disabled = ids.length < 1;
}

function goToCompare() {
  const ids = Session.get(Keys.COMPARE_IDS) || [];
  if (!ids.length) { toast('Select at least one product to compare.', 'warning'); return; }
  window.location.href = '/pages/compare.html';
}

function viewReviews(productId) {
  Session.set(Keys.SELECTED_PID, productId);
  window.location.href = '/pages/reviews.html';
}

function addToCompare(productId) {
  const ids = Session.get(Keys.COMPARE_IDS) || [];
  if (!ids.includes(productId)) ids.push(productId);
  Session.set(Keys.COMPARE_IDS, ids);
  const cb = document.querySelector(`#compare-checkboxes input[value="${productId}"]`);
  if (cb) { cb.checked = true; updateCompareSelection(); }
  toast('Added to comparison.', 'success');
  document.getElementById('compare-bar').scrollIntoView({ behavior: 'smooth' });
}

function renderReqsSummary(reqs) {
  if (!reqs) return;
  const el = document.getElementById('reqs-summary');
  if (!el) return;
  const parts = [];
  if (reqs.category) parts.push(`<span class="badge badge-primary">${categoryIcon(reqs.category)} ${reqs.category}</span>`);
  if (reqs.budget)   parts.push(`<span class="badge badge-gray">Budget: ${formatINR(reqs.budget)}</span>`);
  if (reqs.purpose && reqs.purpose.length) parts.push(`<span class="badge badge-info">${reqs.purpose.join(', ')}</span>`);
  if (reqs.important_specifications && reqs.important_specifications.length)
    reqs.important_specifications.forEach(s => parts.push(`<span class="badge badge-warning">${escHtml(s)}</span>`));

  el.innerHTML = `
    <div style="font-weight:700;margin-bottom:10px">Your Requirements</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">${parts.join('')}</div>`;
}

document.addEventListener('DOMContentLoaded', () => {
  const reqs = Session.get(Keys.REQUIREMENTS);
  if (!reqs) {
    document.getElementById('products-area').innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🧠</div>
        <div class="empty-title">No requirements yet</div>
        <p class="empty-desc">Please analyze your requirements first before searching for products.</p>
        <a href="/pages/requirements.html" class="btn btn-primary" style="margin-top:12px">Go to Requirements</a>
      </div>`;
    return;
  }
  renderReqsSummary(reqs);

  // Restore saved products
  const saved = Session.get(Keys.PRODUCTS);
  if (saved && saved.length) {
    allProducts = saved;
    strictProducts = saved.filter(p => !reqs.budget || p.price_inr <= reqs.budget);
    overBudgetProducts = saved.filter(p => reqs.budget && p.price_inr > reqs.budget);
    renderProductsData(strictProducts, overBudgetProducts, reqs.budget, false);
    renderCompareBar();
  }
});
