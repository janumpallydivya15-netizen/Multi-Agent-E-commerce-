/**
 * recommendations.js — Recommendation Agent page logic
 */

async function loadRecommendations() {
  const reqs = Session.get(Keys.REQUIREMENTS);
  const ids = Session.get(Keys.COMPARE_IDS) || [];
  
  if (!reqs) { toast('Missing requirements. Go back to start.', 'error'); return; }
  let productIds = ids;
  if (!productIds.length) {
    const prods = Session.get(Keys.PRODUCTS) || [];
    productIds = prods.map(p => p.product_id);
  }
  
  if (productIds.length < 1) { toast('No products available to recommend from.', 'warning'); return; }

  const btn = document.getElementById('recBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner spinner-sm"></span> Generating…';
  
  showLoading('rec-area', '🎯 AI is generating personalized recommendations…');

  try {
    const res = await apiPost('/api/recommendations', { requirements: reqs, product_ids: productIds });
    if (!res.success) throw new Error(res.error);

    const recs = res.data;
    Session.set(Keys.RECOMMENDATIONS, recs);
    
    renderRecommendations(recs);
    toast('Recommendations ready!', 'success');
  } catch (e) {
    showError('rec-area', e.message || 'Failed to get recommendations.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '🎯 Get Recommendations';
  }
}

function renderRecommendations(data) {
  const area = document.getElementById('rec-area');
  const reqs = Session.get(Keys.REQUIREMENTS);
  const budget = reqs && reqs.budget;
  
  const matchCase = data.match_case || (data.has_valid_matches ? 'full_match' : (data.best_overall ? 'partial_match' : 'no_budget_match'));

  if (matchCase === 'no_budget_match') {
    renderOverBudgetCase(data, budget);
    return;
  }
  
  let bannerClass = matchCase === 'partial_match' ? 'border:1px solid var(--warning);background:rgba(245,158,11,.08)' : 'border:1px solid var(--border)';
  let headerTitle = matchCase === 'partial_match' ? '⚠️ No product fully matches all your requirements.' : '🧠 Agent Decision Summary';

  let html = `
    <div style="background:var(--bg);border-radius:var(--radius-sm);padding:20px;margin-bottom:32px;${bannerClass}">
      <div style="font-weight:700;font-size:1.1rem;margin-bottom:8px">${headerTitle}</div>
      <p style="color:var(--text-muted);font-size:.95rem;line-height:1.6">${escHtml(data.decision_summary)}</p>
    </div>
  `;
  
  if (data.best_overall) {
    const isPartial = matchCase === 'partial_match';
    const titleLabel = isPartial ? '🏆 Best Available Match' : '🏆 Best Overall';
    html += `
      <div class="rec-card-best" style="margin-bottom:24px">
        <div style="font-size:.8rem;font-weight:700;color:var(--primary);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">${titleLabel}</div>
        <div class="rec-name">${escHtml(data.best_overall.product_name)}</div>
        <div class="rec-price">${escHtml(data.best_overall.price_summary)}</div>
        <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">
          <div class="rec-score">Score: ${data.best_overall.overall_score}/100</div>
          <span class="badge badge-success">✓ Within Budget</span>
          <span class="badge badge-gray">${escHtml(data.best_overall.requirement_match_summary)}</span>
        </div>
        
        <div class="rec-why">
          <div class="rec-why-title">Why we recommend it</div>
          ${(data.best_overall.why_recommended || []).map(w => `<div class="rec-why-item">${escHtml(w)}</div>`).join('')}
        </div>
        
        <div style="margin-top:20px;padding-top:16px;border-top:1px solid rgba(99,102,241,.2);font-size:.85rem;color:var(--text-muted)">
          <strong>Review Summary:</strong> ${escHtml(data.best_overall.review_summary)}
        </div>
      </div>
    `;
  }
  
  if (data.best_value && (!data.best_overall || data.best_value.product_id !== data.best_overall.product_id)) {
    html += `
      <div class="rec-card-value" style="margin-bottom:24px">
        <div style="font-size:.8rem;font-weight:700;color:var(--success);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">💰 Best Value</div>
        <div class="rec-name">${escHtml(data.best_value.product_name)}</div>
        <div class="rec-price">${escHtml(data.best_value.price_summary)}</div>
        <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">
          <div class="rec-score" style="background:rgba(16,185,129,.1);color:var(--success)">Score: ${data.best_value.overall_score}/100</div>
          <span class="badge badge-success">✓ Within Budget</span>
          <span class="badge badge-gray">${escHtml(data.best_value.requirement_match_summary)}</span>
        </div>
        
        <div class="rec-why">
          <div class="rec-why-title">Why it's a great value</div>
          ${(data.best_value.why_recommended || []).map(w => `<div class="rec-why-item">${escHtml(w)}</div>`).join('')}
        </div>
      </div>
    `;
  }
  
  if (data.alternatives && data.alternatives.length > 0) {
    html += `
      <div class="section-title" style="margin-top:40px;margin-bottom:16px">🔄 Alternatives</div>
      <div class="two-col">
        ${data.alternatives.map(alt => `
          <div class="rec-card-alt">
            <div style="font-weight:700;font-size:1.1rem;margin-bottom:4px">${escHtml(alt.product_name)}</div>
            <div style="color:var(--primary);font-weight:700;margin-bottom:12px">${escHtml(alt.price_summary)}</div>
            <div class="rec-score" style="background:var(--bg);color:var(--text);font-size:.8rem;padding:4px 10px;margin-bottom:12px">Score: ${alt.overall_score}</div>
            
            <div class="rec-why-title">Notes</div>
            ${(alt.why_recommended || []).map(w => `<div style="font-size:.85rem;margin-bottom:4px;color:var(--text-muted)">• ${escHtml(w)}</div>`).join('')}
          </div>
        `).join('')}
      </div>
    `;
  }
  
  area.innerHTML = html;
}

function renderOverBudgetCase(data, budget) {
  const area = document.getElementById('rec-area');
  
  let html = `
    <div style="text-align:center;padding:40px 20px;background:var(--danger-light);border:1px solid #fca5a5;border-radius:var(--radius);margin-bottom:32px">
      <div style="font-size:2.5rem;margin-bottom:12px">⚠️</div>
      <h2 style="color:#991b1b;margin-bottom:8px">No products meet your budget</h2>
      <p style="color:#b91c1c;max-width:500px;margin:0 auto">${escHtml(data.decision_summary)}</p>
    </div>
  `;
  
  if (data.alternatives && data.alternatives.length > 0) {
    html += `
      <div class="section-title" style="margin-bottom:20px;text-align:center">Closest Alternatives — Over Budget</div>
      <div style="display:flex;flex-direction:column;gap:16px;max-width:600px;margin:0 auto">
        ${data.alternatives.map(alt => {
          return `
          <div class="card" style="border-left:4px solid var(--warning)">
            <div style="display:flex;justify-content:space-between;align-items:flex-start">
              <div>
                <div style="font-weight:800;font-size:1.1rem">${escHtml(alt.product_name)}</div>
                <div style="font-size:.85rem;color:var(--text-muted);margin-top:4px">${escHtml(alt.requirement_match_summary)}</div>
              </div>
              <span class="badge badge-warning">OVER BUDGET</span>
            </div>
            
            <div style="margin-top:16px;background:var(--bg);padding:12px;border-radius:var(--radius-sm);display:flex;justify-content:space-between;align-items:center">
              <div>
                <div style="font-size:.75rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em">Price vs Budget</div>
                <div style="font-weight:700;color:var(--text)">${escHtml(alt.price_summary)}</div>
              </div>
            </div>
            
            <div style="margin-top:16px;font-size:.85rem">
              ${(alt.why_recommended || []).map(w => `<div style="margin-bottom:4px;color:var(--text-muted)">• ${escHtml(w)}</div>`).join('')}
            </div>
          </div>
        `}).join('')}
      </div>
    `;
  }
  
  area.innerHTML = html;
}

document.addEventListener('DOMContentLoaded', () => {
  renderContextBar('context-bar-wrap');
  const recs = Session.get(Keys.RECOMMENDATIONS);
  if (recs) {
    renderRecommendations(recs);
  }
});
