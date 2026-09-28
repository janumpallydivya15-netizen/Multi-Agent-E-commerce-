/**
 * compare.js — Price & Specification Agent page logic
 */

async function runComparison() {
  const reqs = Session.get(Keys.REQUIREMENTS);
  const ids = Session.get(Keys.COMPARE_IDS) || [];
  
  if (!reqs) { toast('Missing requirements. Go back to start.', 'error'); return; }
  if (ids.length < 1) { toast('Select at least one product to compare.', 'warning'); return; }

  const btn = document.getElementById('compareBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner spinner-sm"></span> Comparing…';
  
  showLoading('compare-area', '⚖️ Comparing price and specifications…');

  try {
    const res = await apiPost('/api/compare', { requirements: reqs, product_ids: ids });
    if (!res.success) throw new Error(res.error);

    const comp = res.data;
    Session.set(Keys.COMPARISON, comp);
    
    renderComparison(comp);
    toast('Comparison complete!', 'success');
  } catch (e) {
    showError('compare-area', e.message || 'Comparison failed. Please try again.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '⚖️ Run Comparison';
  }
}

function renderComparison(data) {
  const area = document.getElementById('compare-area');
  const prods = data.products || [];
  
  if (!prods.length) {
    showEmpty('compare-area', { title: 'No products', desc: 'Could not compare the selected products.' });
    return;
  }

  // Get all unique specs keys
  const specKeys = new Set();
  prods.forEach(p => {
    if (p.specification_comparison) {
      Object.keys(p.specification_comparison).forEach(k => specKeys.add(k));
    }
  });

  const bestOverallId = data.best_overall_product;
  const bestValueId = data.best_value_product;

  let html = `
    <div style="background:var(--bg);border-radius:var(--radius-sm);padding:16px;margin-bottom:20px">
      <div style="font-weight:700;margin-bottom:6px">💡 Comparison Summary</div>
      <p style="color:var(--text-muted);font-size:.9rem;line-height:1.5">${escHtml(data.summary)}</p>
    </div>
    
    <div class="compare-table-wrap">
      <table class="compare-table">
        <thead>
          <tr>
            <th style="min-width:180px">Feature</th>
            ${prods.map(p => `
              <th class="${p.product_id === bestOverallId ? 'highlight-col' : ''}">
                <div style="color:var(--text);font-size:.95rem;margin-bottom:4px">${escHtml(p.product_name)}</div>
                ${p.product_id === bestOverallId ? '<span class="badge badge-primary" style="font-size:.7rem;padding:2px 8px">Best Match</span>' : ''}
                ${p.product_id === bestValueId ? '<span class="badge badge-success" style="font-size:.7rem;padding:2px 8px">Best Value</span>' : ''}
              </th>
            `).join('')}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Price</td>
            ${prods.map(p => `
              <td class="${p.product_id === bestOverallId ? 'highlight-col' : ''}">
                <div style="font-weight:700;color:var(--primary);font-size:1.1rem">${formatINR(p.price)}</div>
              </td>
            `).join('')}
          </tr>
          <tr>
            <td>Budget Status</td>
            ${prods.map(p => `
              <td class="${p.product_id === bestOverallId ? 'highlight-col' : ''}">
                ${budgetBadge(p.within_budget)}
              </td>
            `).join('')}
          </tr>
          <tr>
            <td>Score</td>
            ${prods.map(p => `
              <td class="${p.product_id === bestOverallId ? 'highlight-col' : ''}">
                <div style="font-weight:800;font-size:1.1rem">${p.score} <span style="font-size:.8rem;color:var(--text-muted)">/ 100</span></div>
              </td>
            `).join('')}
          </tr>
          <tr>
            <td>Req. Match</td>
            ${prods.map(p => `
              <td class="${p.product_id === bestOverallId ? 'highlight-col' : ''}">
                ${p.required_matches} of ${p.required_total}
              </td>
            `).join('')}
          </tr>
          
          <tr><td colspan="${prods.length + 1}" style="background:var(--bg);color:var(--text-muted);font-size:.8rem;text-transform:uppercase;letter-spacing:.05em">Specifications</td></tr>
          
          ${Array.from(specKeys).map(k => `
            <tr>
              <td style="color:var(--text-muted);font-weight:500">${escHtml(k)}</td>
              ${prods.map(p => `
                <td class="${p.product_id === bestOverallId ? 'highlight-col' : ''}">
                  ${escHtml(p.specification_comparison?.[k] || '—')}
                </td>
              `).join('')}
            </tr>
          `).join('')}
          
          <tr><td colspan="${prods.length + 1}" style="background:var(--bg);color:var(--text-muted);font-size:.8rem;text-transform:uppercase;letter-spacing:.05em">Analysis</td></tr>
          
          <tr>
            <td style="color:var(--text-muted);font-weight:500">Strengths</td>
            ${prods.map(p => `
              <td class="${p.product_id === bestOverallId ? 'highlight-col' : ''}" style="vertical-align:top">
                ${p.strengths && p.strengths.length 
                  ? `<ul style="list-style:disc;padding-left:16px;font-size:.85rem;color:var(--success)">
                      ${p.strengths.map(s => `<li>${escHtml(s)}</li>`).join('')}
                     </ul>`
                  : '<span style="color:var(--text-muted);font-size:.85rem">None</span>'}
              </td>
            `).join('')}
          </tr>
          <tr>
            <td style="color:var(--text-muted);font-weight:500">Weaknesses</td>
            ${prods.map(p => `
              <td class="${p.product_id === bestOverallId ? 'highlight-col' : ''}" style="vertical-align:top">
                ${p.weaknesses && p.weaknesses.length 
                  ? `<ul style="list-style:disc;padding-left:16px;font-size:.85rem;color:var(--danger)">
                      ${p.weaknesses.map(w => `<li>${escHtml(w)}</li>`).join('')}
                     </ul>`
                  : '<span style="color:var(--text-muted);font-size:.85rem">None</span>'}
              </td>
            `).join('')}
          </tr>
        </tbody>
      </table>
    </div>
  `;
  
  area.innerHTML = html;
}

function renderCheckboxes() {
  const allProds = Session.get(Keys.PRODUCTS) || [];
  const compIds = Session.get(Keys.COMPARE_IDS) || [];
  const list = document.getElementById('product-checkboxes');
  
  if (!allProds.length) {
    list.innerHTML = '<div style="color:var(--text-muted);font-size:.9rem">No products available. Please search first.</div>';
    return;
  }
  
  list.innerHTML = allProds.map(p => `
    <label class="checkbox-item">
      <input type="checkbox" value="${escHtml(p.product_id)}" ${compIds.includes(p.product_id) ? 'checked' : ''} onchange="updateSelection()">
      <span>${escHtml(p.name)}</span>
      <span style="color:var(--text-muted);margin-left:auto;font-size:.85rem">${formatINR(p.price_inr)}</span>
    </label>
  `).join('');
  
  updateSelection();
}

function updateSelection() {
  const checks = document.querySelectorAll('#product-checkboxes input[type="checkbox"]:checked');
  const ids = Array.from(checks).map(c => c.value);
  Session.set(Keys.COMPARE_IDS, ids);
  
  const btn = document.getElementById('compareBtn');
  if (btn) btn.disabled = ids.length < 1;
}

document.addEventListener('DOMContentLoaded', () => {
  renderContextBar('context-bar-wrap');
  renderCheckboxes();
  
  const comp = Session.get(Keys.COMPARISON);
  if (comp) {
    renderComparison(comp);
  }
});
