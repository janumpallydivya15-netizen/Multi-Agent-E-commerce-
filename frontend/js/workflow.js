/**
 * workflow.js — Multi-Agent Workflow Execution
 */

async function runWorkflow() {
  const query = document.getElementById('workflowInput').value.trim();
  if (!query) { toast('Please enter a shopping request.', 'warning'); return; }

  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner spinner-sm"></span> Running Workflow…';
  
  document.getElementById('workflow-steps').style.display = 'block';
  const stepsContainer = document.getElementById('steps-container');
  
  stepsContainer.innerHTML = `
    <div class="workflow-step active" id="step-req">
      <div class="step-icon"><div class="step-spinner"></div></div>
      <div class="step-content">
        <div class="step-title">Analyzing requirements</div>
        <div class="step-desc">Requirement Agent is extracting budget, category, and features.</div>
      </div>
    </div>
    <div class="workflow-step" id="step-prod">
      <div class="step-icon">🔎</div>
      <div class="step-content">
        <div class="step-title">Searching products</div>
        <div class="step-desc">Product Search Agent is finding matches.</div>
      </div>
    </div>
    <div class="workflow-step" id="step-rev">
      <div class="step-icon">⭐</div>
      <div class="step-content">
        <div class="step-title">Analyzing reviews</div>
        <div class="step-desc">Review Agent is processing sentiment and feedback.</div>
      </div>
    </div>
    <div class="workflow-step" id="step-comp">
      <div class="step-icon">⚖️</div>
      <div class="step-content">
        <div class="step-title">Comparing prices and specifications</div>
        <div class="step-desc">Price & Specs Agent is calculating scores.</div>
      </div>
    </div>
    <div class="workflow-step" id="step-rec">
      <div class="step-icon">🎯</div>
      <div class="step-content">
        <div class="step-title">Generating recommendations</div>
        <div class="step-desc">Recommendation Agent is finalizing picks.</div>
      </div>
    </div>
  `;
  
  document.getElementById('workflow-result').innerHTML = '';

  try {
    const res = await apiPost('/api/shopping', { request: query });
    
    if (!res.success) {
      markStepError('step-req', res.error);
      throw new Error(res.error);
    }
    
    const state = res.data;
    
    await animateStep('step-req', '✅ Requirements analyzed', `Extracted category: ${state.requirements?.category || 'Any'}`);
    if (state.error && !state.products) { markStepError('step-prod', state.error); return; }
    
    await animateStep('step-prod', '✅ Products searched', `Found ${state.products?.length || 0} candidate products`);
    if (state.error && !state.reviews) { markStepError('step-rev', state.error); return; }
    
    await animateStep('step-rev', '✅ Reviews analyzed', `Processed reviews for ${Object.keys(state.reviews || {}).length} products`);
    if (state.error && !state.comparison) { markStepError('step-comp', state.error); return; }
    
    await animateStep('step-comp', '✅ Comparison completed', `Scored products against requirements`);
    if (state.error && !state.recommendations) { markStepError('step-rec', state.error); return; }
    
    await animateStep('step-rec', '✅ Recommendations generated', 'Ready.');
    
    Session.clearAll();
    Session.set(Keys.REQUEST, query);
    if (state.requirements) Session.set(Keys.REQUIREMENTS, state.requirements);
    if (state.products) Session.set(Keys.PRODUCTS, state.products);
    if (state.reviews) Session.set(Keys.REVIEWS, state.reviews);
    if (state.comparison) Session.set(Keys.COMPARISON, state.comparison);
    if (state.recommendations) Session.set(Keys.RECOMMENDATIONS, state.recommendations);
    
    renderWorkflowResult(state);
    
  } catch (e) {
    toast('Workflow failed.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '🤖 Run Full Workflow';
  }
}

async function animateStep(id, title, resultText) {
  const el = document.getElementById(id);
  if (!el) return;
  
  el.className = 'workflow-step active';
  el.querySelector('.step-icon').innerHTML = '<div class="step-spinner"></div>';
  
  await new Promise(r => setTimeout(r, 400));
  
  el.className = 'workflow-step done';
  el.querySelector('.step-icon').innerHTML = '✓';
  el.querySelector('.step-title').textContent = title;
  
  let resEl = el.querySelector('.step-result');
  if (!resEl) {
    resEl = document.createElement('div');
    resEl.className = 'step-result';
    el.querySelector('.step-content').appendChild(resEl);
  }
  resEl.textContent = resultText;
  
  const next = el.nextElementSibling;
  if (next) {
    next.className = 'workflow-step active';
    next.querySelector('.step-icon').innerHTML = '<div class="step-spinner"></div>';
  }
}

function markStepError(id, errorText) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'workflow-step error';
  el.querySelector('.step-icon').innerHTML = '❌';
  
  let resEl = el.querySelector('.step-result');
  if (!resEl) {
    resEl = document.createElement('div');
    resEl.className = 'step-result error';
    el.querySelector('.step-content').appendChild(resEl);
  }
  resEl.textContent = errorText;
}

function renderWorkflowResult(state) {
  const area = document.getElementById('workflow-result');
  const recs = state.recommendations;
  
  if (!recs || !recs.best_overall) {
    area.innerHTML = `
      <div class="card" style="border-left:4px solid var(--warning)">
        <div style="font-weight:700;font-size:1.1rem;margin-bottom:8px">⚠️ No products meet your budget</div>
        <p style="color:var(--text-muted);font-size:.9rem">${recs ? recs.decision_summary : (state.error || 'No recommendations generated.')}</p>
        <button class="btn btn-primary" style="margin-top:16px" onclick="window.location.href='/pages/recommendations.html'">View Over-Budget Alternatives</button>
      </div>
    `;
    return;
  }
  
  const best = recs.best_overall;
  const matchTitle = recs.match_case === 'partial_match' ? 'Best Available Match' : 'Final Recommendation';
  area.innerHTML = `
    <div class="card" style="border:2px solid var(--primary)">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px">
        <div>
          <div style="font-size:.8rem;font-weight:700;color:var(--primary);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">${matchTitle}</div>
          <div style="font-size:1.4rem;font-weight:800;color:var(--text)">${escHtml(best.product_name)}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:1.2rem;font-weight:800;color:var(--text)">${escHtml(best.price_summary)}</div>
          <div class="badge badge-success" style="margin-top:4px">Score: ${best.overall_score}</div>
        </div>
      </div>
      
      <div style="background:var(--bg);padding:12px;border-radius:var(--radius-sm);font-size:.9rem;color:var(--text-muted);margin-bottom:16px">
        ${escHtml(recs.decision_summary)}
      </div>
      
      <button class="btn btn-primary btn-block" onclick="window.location.href='/pages/recommendations.html'">View Full Analysis</button>
    </div>
  `;
}

function loadFromSession() {
  const req = Session.get(Keys.REQUEST);
  if (req) {
    document.getElementById('workflowInput').value = req;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadFromSession();
});
