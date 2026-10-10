// FinTwin Financial Decision Simulator Frontend Logic
(function () {
    let activeScenarioId = null;
    let savedScenarios = [];
    let cashFlowChartInstance = null;
    let revExpChartInstance = null;
    let compareChartInstance = null;

    function getActiveCompanyId() {
        return window.currentCompanyId || (window.currentUser ? window.currentUser.company_id : 1);
    }

    function formatCurrency(val) {
        if (val === undefined || val === null || isNaN(val)) return '$0';
        return '$' + Number(val).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    }

    function formatNumber(val, decimals = 1) {
        if (val === undefined || val === null || isNaN(val)) return '0';
        return Number(val).toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    }

    // Initialize UI and Event Listeners
    function initFinTwin() {
        // Setup slider to text value sync
        setupSliderSync('fintwin-rev-growth', 'fintwin-rev-growth-val', '%');
        setupSliderSync('fintwin-duration', 'fintwin-duration-val', ' mos');
        setupSliderSync('fintwin-delay-days', 'fintwin-delay-days-val', ' days');

        // Form buttons
        const form = document.getElementById('fintwin-builder-form');
        if (form) {
            form.addEventListener('submit', handleSaveScenario);
        }

        const btnSimulateNow = document.getElementById('btn-fintwin-simulate-now');
        if (btnSimulateNow) {
            btnSimulateNow.addEventListener('click', handleSimulateForm);
        }

        const btnReset = document.getElementById('btn-fintwin-reset');
        if (btnReset) {
            btnReset.addEventListener('click', resetForm);
        }

        const btnCompare = document.getElementById('btn-fintwin-compare-selected');
        if (btnCompare) {
            btnCompare.addEventListener('click', handleCompareSelected);
        }

        const btnCloseModal = document.getElementById('btn-fintwin-close-compare');
        if (btnCloseModal) {
            btnCloseModal.addEventListener('click', closeCompareModal);
        }

        // Tab click hook
        const fintwinNavBtn = document.querySelector('.nav-item[data-tab="fintwin"]');
        if (fintwinNavBtn) {
            fintwinNavBtn.addEventListener('click', () => {
                const heading = document.getElementById('tab-heading');
                const subheading = document.getElementById('tab-subheading');
                if (heading) heading.innerText = 'FinTwin — AI Financial Decision Simulator';
                if (subheading) subheading.innerText = 'Simulate hypothetical growth, hiring, Capex, and vendor decisions against your baseline';
                loadSavedScenarios();
            });
        }
    }

    function setupSliderSync(sliderId, labelId, suffix = '') {
        const slider = document.getElementById(sliderId);
        const label = document.getElementById(labelId);
        if (slider && label) {
            slider.addEventListener('input', () => {
                const prefix = (sliderId === 'fintwin-rev-growth' && slider.value > 0) ? '+' : '';
                label.innerText = `${prefix}${slider.value}${suffix}`;
            });
        }
    }

    function getFormParameters() {
        return {
            revenue_growth_pct: parseFloat(document.getElementById('fintwin-rev-growth')?.value || 0),
            payroll_expense_change: parseFloat(document.getElementById('fintwin-payroll')?.value || 0),
            marketing_expense_change: parseFloat(document.getElementById('fintwin-marketing')?.value || 0),
            opex_change: parseFloat(document.getElementById('fintwin-opex')?.value || 0),
            vendor_payment_delay_days: parseInt(document.getElementById('fintwin-delay-days')?.value || 0),
            capex_one_time: parseFloat(document.getElementById('fintwin-capex')?.value || 0),
            duration_months: parseInt(document.getElementById('fintwin-duration')?.value || 12)
        };
    }

    function setFormParameters(params, name = '', desc = '') {
        if (document.getElementById('fintwin-scenario-name')) {
            document.getElementById('fintwin-scenario-name').value = name;
        }
        if (document.getElementById('fintwin-scenario-desc')) {
            document.getElementById('fintwin-scenario-desc').value = desc || '';
        }

        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.value = val;
        };

        setVal('fintwin-rev-growth', params.revenue_growth_pct || 0);
        setVal('fintwin-payroll', params.payroll_expense_change || 0);
        setVal('fintwin-marketing', params.marketing_expense_change || 0);
        setVal('fintwin-opex', params.opex_change || 0);
        setVal('fintwin-delay-days', params.vendor_payment_delay_days || 0);
        setVal('fintwin-capex', params.capex_one_time || 0);
        setVal('fintwin-duration', params.duration_months || 12);

        // Update labels
        const revLabel = document.getElementById('fintwin-rev-growth-val');
        if (revLabel) {
            const p = (params.revenue_growth_pct > 0 ? '+' : '') + (params.revenue_growth_pct || 0);
            revLabel.innerText = `${p}%`;
        }

        const durLabel = document.getElementById('fintwin-duration-val');
        if (durLabel) durLabel.innerText = `${params.duration_months || 12} mos`;

        const delayLabel = document.getElementById('fintwin-delay-days-val');
        if (delayLabel) delayLabel.innerText = `${params.vendor_payment_delay_days || 0} days`;
    }

    function resetForm() {
        activeScenarioId = null;
        setFormParameters({
            revenue_growth_pct: 0,
            payroll_expense_change: 0,
            marketing_expense_change: 0,
            opex_change: 0,
            vendor_payment_delay_days: 0,
            capex_one_time: 0,
            duration_months: 12
        }, '', '');

        const statusLabel = document.getElementById('fintwin-active-scenario-badge');
        if (statusLabel) statusLabel.innerText = 'Unsaved Scenario';
    }

    // Load saved scenarios list
    async function loadSavedScenarios() {
        try {
            const compId = getActiveCompanyId();
            const res = await fetch(`/api/fintwin/scenarios?company_id=${compId}`);
            if (!res.ok) return;

            savedScenarios = await res.json();
            renderSavedScenariosList();

            // If we have scenarios and none is currently active, simulate the first one or auto-load
            if (savedScenarios.length > 0 && !activeScenarioId) {
                loadScenarioIntoForm(savedScenarios[0].id);
            } else if (savedScenarios.length === 0) {
                // If brand new, trigger a baseline run preview
                handleSimulateForm();
            }
        } catch (err) {
            console.error("Error loading FinTwin scenarios:", err);
        }
    }

    function renderSavedScenariosList() {
        const listEl = document.getElementById('fintwin-saved-list');
        if (!listEl) return;

        if (savedScenarios.length === 0) {
            listEl.innerHTML = `<p class="text-muted text-sm" style="padding:10px;">No saved scenarios yet. Create and save a hypothetical scenario above.</p>`;
            return;
        }

        listEl.innerHTML = savedScenarios.map(sc => `
            <div class="fintwin-scenario-item ${activeScenarioId === sc.id ? 'active' : ''}">
                <input type="checkbox" class="fintwin-compare-checkbox" data-id="${sc.id}" title="Select for scenario comparison">
                <div class="fintwin-scenario-info" onclick="window.FinTwin.loadScenario(${sc.id})">
                    <i class="fa-solid fa-code-branch" style="color:var(--accent-purple);"></i>
                    <div style="min-width:0;">
                        <div class="fintwin-scenario-name">${sc.scenario_name}</div>
                        <div class="fintwin-scenario-meta">${sc.duration_months} mos • ${sc.created_at || 'Saved'}</div>
                    </div>
                </div>
                <div class="fintwin-scenario-actions">
                    <button type="button" class="btn btn-outline" style="padding:4px 8px; font-size:11px;" onclick="window.FinTwin.runSimulation(${sc.id})" title="Run Simulation">
                        <i class="fa-solid fa-play"></i>
                    </button>
                    <button type="button" class="btn btn-outline danger-hover" style="padding:4px 8px; font-size:11px;" onclick="window.FinTwin.deleteScenario(${sc.id})" title="Delete Scenario">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }

    async function loadScenarioIntoForm(scenarioId) {
        const sc = savedScenarios.find(s => s.id === scenarioId);
        if (!sc) return;

        activeScenarioId = sc.id;
        setFormParameters(sc.input_parameters, sc.scenario_name, sc.description);

        const statusLabel = document.getElementById('fintwin-active-scenario-badge');
        if (statusLabel) statusLabel.innerText = `Active: ${sc.scenario_name}`;

        renderSavedScenariosList();
        await runSimulationForScenario(scenarioId);
    }

    async function handleSaveScenario(e) {
        e.preventDefault();
        const compId = getActiveCompanyId();
        const nameInput = document.getElementById('fintwin-scenario-name');
        const descInput = document.getElementById('fintwin-scenario-desc');
        const name = nameInput ? nameInput.value.trim() : '';
        const desc = descInput ? descInput.value.trim() : '';

        if (!name) {
            alert('Please enter a name for the scenario.');
            return;
        }

        const params = getFormParameters();
        const saveBtn = document.getElementById('btn-fintwin-save');
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Saving...`;
        }

        try {
            let res;
            if (activeScenarioId) {
                // Update existing
                res = await fetch(`/api/fintwin/scenarios/${activeScenarioId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        company_id: compId,
                        scenario_name: name,
                        description: desc,
                        input_parameters: params
                    })
                });
            } else {
                // Create new
                res = await fetch('/api/fintwin/scenarios', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        company_id: compId,
                        scenario_name: name,
                        description: desc,
                        input_parameters: params
                    })
                });
            }

            const data = await res.json();
            if (res.ok && data.status === 'success') {
                activeScenarioId = data.scenario.id;
                await loadSavedScenarios();
                await runSimulationForScenario(activeScenarioId);
            } else {
                alert(data.detail || 'Failed to save scenario.');
            }
        } catch (err) {
            alert('Error saving scenario: ' + err.message);
        } finally {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Save Scenario`;
            }
        }
    }

    async function handleSimulateForm() {
        const compId = getActiveCompanyId();
        const params = getFormParameters();
        const btnSim = document.getElementById('btn-fintwin-simulate-now');
        if (btnSim) {
            btnSim.disabled = true;
            btnSim.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Simulating...`;
        }

        try {
            if (activeScenarioId) {
                await runSimulationForScenario(activeScenarioId);
            } else {
                // Ephemeral simulation via compare or saving
                const nameInput = document.getElementById('fintwin-scenario-name');
                const name = (nameInput && nameInput.value.trim()) ? nameInput.value.trim() : 'Simulation Draft';

                // Save draft scenario
                const res = await fetch('/api/fintwin/scenarios', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        company_id: compId,
                        scenario_name: name,
                        description: 'Simulated from configuration builder',
                        input_parameters: params
                    })
                });
                const data = await res.json();
                if (res.ok && data.scenario) {
                    activeScenarioId = data.scenario.id;
                    await loadSavedScenarios();
                    await runSimulationForScenario(activeScenarioId);
                }
            }
        } catch (err) {
            alert('Error running simulation: ' + err.message);
        } finally {
            if (btnSim) {
                btnSim.disabled = false;
                btnSim.innerHTML = `<i class="fa-solid fa-bolt"></i> Run Simulation`;
            }
        }
    }

    async function runSimulationForScenario(scenarioId) {
        const compId = getActiveCompanyId();
        try {
            const res = await fetch(`/api/fintwin/scenarios/${scenarioId}/simulate?company_id=${compId}`, {
                method: 'POST'
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                renderSimulationDashboard(data.simulation_results);
            } else {
                alert(data.detail || 'Simulation execution failed.');
            }
        } catch (err) {
            console.error("Simulation error:", err);
        }
    }

    async function deleteScenario(scenarioId) {
        if (!confirm('Are you sure you want to delete this scenario?')) return;
        const compId = getActiveCompanyId();
        try {
            const res = await fetch(`/api/fintwin/scenarios/${scenarioId}?company_id=${compId}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                if (activeScenarioId === scenarioId) {
                    resetForm();
                }
                await loadSavedScenarios();
            }
        } catch (err) {
            alert('Failed to delete scenario: ' + err.message);
        }
    }

    // Render Full Simulation Results
    function renderSimulationDashboard(results) {
        const proj = results.projected_results;
        const baseline = results.baseline;
        const risk = results.risk_assessment;
        const deltas = proj.deltas || {};

        // 1. KPI Cards
        const runwayEl = document.getElementById('fintwin-kpi-runway');
        const runwayDeltaEl = document.getElementById('fintwin-kpi-runway-delta');
        if (runwayEl) runwayEl.innerText = `${proj.cash_runway_months} mos`;
        if (runwayDeltaEl) {
            const d = deltas.runway_months_delta || 0;
            const sign = d > 0 ? '+' : '';
            runwayDeltaEl.className = `fintwin-kpi-delta ${d >= 0 ? 'positive' : 'negative'}`;
            runwayDeltaEl.innerHTML = `<i class="fa-solid ${d >= 0 ? 'fa-arrow-up' : 'fa-arrow-down'}"></i> ${sign}${d} mos vs baseline (${baseline.cash_runway_months} mos)`;
        }

        const cashEl = document.getElementById('fintwin-kpi-cash');
        const cashDeltaEl = document.getElementById('fintwin-kpi-cash-delta');
        if (cashEl) cashEl.innerText = formatCurrency(proj.ending_cash);
        if (cashDeltaEl) {
            const d = deltas.ending_cash_delta || 0;
            const sign = d > 0 ? '+' : '';
            cashDeltaEl.className = `fintwin-kpi-delta ${d >= 0 ? 'positive' : 'negative'}`;
            cashDeltaEl.innerHTML = `<i class="fa-solid ${d >= 0 ? 'fa-arrow-up' : 'fa-arrow-down'}"></i> ${sign}${formatCurrency(d)} vs start (${formatCurrency(baseline.estimated_cash)})`;
        }

        const netFlowEl = document.getElementById('fintwin-kpi-netflow');
        const netFlowDeltaEl = document.getElementById('fintwin-kpi-netflow-delta');
        if (netFlowEl) netFlowEl.innerText = formatCurrency(proj.net_cash_flow);
        if (netFlowDeltaEl) {
            const isPos = proj.net_cash_flow >= 0;
            netFlowDeltaEl.className = `fintwin-kpi-delta ${isPos ? 'positive' : 'negative'}`;
            netFlowDeltaEl.innerText = isPos ? 'Net Cash Surplus' : 'Net Cash Burn Deficit';
        }

        const marginEl = document.getElementById('fintwin-kpi-margin');
        const marginDeltaEl = document.getElementById('fintwin-kpi-margin-delta');
        if (marginEl) marginEl.innerText = `${proj.profit_margin_pct}%`;
        if (marginDeltaEl) {
            marginDeltaEl.className = `fintwin-kpi-delta ${proj.profit_margin_pct >= 20 ? 'positive' : 'neutral'}`;
            marginDeltaEl.innerText = `Total Revenue: ${formatCurrency(proj.total_revenue)}`;
        }

        // 2. Risk Score & Indicators
        const riskBadge = document.getElementById('fintwin-risk-level-badge');
        if (riskBadge) {
            riskBadge.className = `fintwin-risk-badge ${risk.overall_risk_level}`;
            riskBadge.innerText = `${risk.overall_risk_level} RISK (${risk.risk_score}/100)`;
        }

        const flagsContainer = document.getElementById('fintwin-risk-flags-list');
        if (flagsContainer) {
            if (risk.risk_flags.length === 0) {
                flagsContainer.innerHTML = `<p class="text-muted" style="font-size:12px;">No high-priority financial risks detected for this scenario.</p>`;
            } else {
                flagsContainer.innerHTML = risk.risk_flags.map(f => `
                    <div class="fintwin-flag-item">
                        <i class="fa-solid fa-triangle-exclamation fintwin-flag-icon ${f.severity}"></i>
                        <div class="fintwin-flag-content">
                            <h5>${f.title}</h5>
                            <p>${f.description}</p>
                        </div>
                    </div>
                `).join('');
            }
        }

        // 3. ChromaDB Policy RAG Evidence
        const policyContainer = document.getElementById('fintwin-policy-evidence-list');
        if (policyContainer) {
            const ev = risk.policy_evidence || [];
            if (ev.length === 0) {
                policyContainer.innerHTML = `<p class="text-muted" style="font-size:12px;">No policy conflicts retrieved from Vector Store.</p>`;
            } else {
                policyContainer.innerHTML = ev.map(p => `
                    <div class="fintwin-policy-item">
                        <div class="fintwin-policy-source"><i class="fa-solid fa-book-bookmark"></i> ${p.source}</div>
                        <div>"${p.content}"</div>
                    </div>
                `).join('');
            }
        }

        // 4. Actionable Recommendations & Assumptions
        const recsList = document.getElementById('fintwin-recommendations-list');
        if (recsList) {
            recsList.innerHTML = (risk.recommendations || []).map(r => `
                <li><i class="fa-solid fa-circle-check"></i> <span>${r}</span></li>
            `).join('');
        }

        const assumptionsList = document.getElementById('fintwin-assumptions-list');
        if (assumptionsList) {
            assumptionsList.innerHTML = (results.assumptions || []).map(a => `
                <li><i class="fa-solid fa-info-circle"></i> <span>${a}</span></li>
            `).join('');
        }

        // 5. Render Chart.js Visualizations
        renderSimulationCharts(proj.monthly_breakdown);
    }

    function renderSimulationCharts(breakdown) {
        if (!breakdown || breakdown.length === 0) return;
        const labels = breakdown.map(b => `M${b.month}`);
        const cashData = breakdown.map(b => b.ending_cash);
        const netFlowData = breakdown.map(b => b.net_cash_flow);
        const revData = breakdown.map(b => b.revenue);
        const expData = breakdown.map(b => b.expense);

        // Chart 1: Cash Balance & Net Flow
        const cashCtx = document.getElementById('fintwin-cash-chart')?.getContext('2d');
        if (cashCtx) {
            if (cashFlowChartInstance) cashFlowChartInstance.destroy();
            cashFlowChartInstance = new Chart(cashCtx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Ending Cash Balance ($)',
                            data: cashData,
                            borderColor: '#2563eb',
                            backgroundColor: 'rgba(37, 99, 235, 0.1)',
                            fill: true,
                            tension: 0.3,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Monthly Net Cash Flow ($)',
                            data: netFlowData,
                            borderColor: '#059669',
                            backgroundColor: 'rgba(5, 150, 105, 0.7)',
                            type: 'bar',
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            ticks: { callback: v => '$' + (v / 1000).toFixed(0) + 'k' }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: { drawOnChartArea: false },
                            ticks: { callback: v => '$' + (v / 1000).toFixed(0) + 'k' }
                        }
                    }
                }
            });
        }

        // Chart 2: Revenue vs Expenses
        const revExpCtx = document.getElementById('fintwin-revexp-chart')?.getContext('2d');
        if (revExpCtx) {
            if (revExpChartInstance) revExpChartInstance.destroy();
            revExpChartInstance = new Chart(revExpCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Projected Revenue ($)',
                            data: revData,
                            backgroundColor: '#059669',
                            borderRadius: 4
                        },
                        {
                            label: 'Projected Expenses ($)',
                            data: expData,
                            backgroundColor: '#dc2626',
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            ticks: { callback: v => '$' + (v / 1000).toFixed(0) + 'k' }
                        }
                    }
                }
            });
        }
    }

    // Compare Selected Scenarios
    async function handleCompareSelected() {
        const checkboxes = document.querySelectorAll('.fintwin-compare-checkbox:checked');
        const selectedIds = Array.from(checkboxes).map(cb => parseInt(cb.getAttribute('data-id')));

        if (selectedIds.length === 0) {
            alert('Please check at least one scenario checkbox from the saved list to compare against baseline.');
            return;
        }

        const compId = getActiveCompanyId();
        try {
            const res = await fetch('/api/fintwin/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    company_id: compId,
                    scenario_ids: selectedIds
                })
            });

            const data = await res.json();
            if (res.ok && data.status === 'success') {
                renderCompareModal(data);
            } else {
                alert(data.detail || 'Failed to compare scenarios.');
            }
        } catch (err) {
            alert('Comparison error: ' + err.message);
        }
    }

    function renderCompareModal(data) {
        const modal = document.getElementById('fintwin-compare-modal');
        const tbody = document.getElementById('fintwin-compare-tbody');
        if (!modal || !tbody) return;

        const base = data.baseline;
        const matrix = data.comparison || [];

        let rows = `
            <tr style="background: rgba(37, 99, 235, 0.05); font-weight:600;">
                <td><strong>Baseline (Actuals)</strong></td>
                <td>Current Data</td>
                <td>${base.cash_runway_months} mos</td>
                <td>${formatCurrency(base.estimated_cash)}</td>
                <td>${formatCurrency(base.net_cash_flow)}</td>
                <td>${formatCurrency(base.net_burn_rate)}/mo</td>
                <td><span class="fintwin-risk-badge LOW">BASELINE</span></td>
            </tr>
        `;

        matrix.forEach(m => {
            const rDelta = m.deltas?.runway_months_delta || 0;
            const rSign = rDelta > 0 ? '+' : '';
            rows += `
                <tr>
                    <td><strong>${m.scenario_name}</strong></td>
                    <td>${m.duration_months} Months</td>
                    <td>
                        <strong>${m.cash_runway_months} mos</strong>
                        <span style="font-size:11px; margin-left:4px; color:${rDelta >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'};">
                            (${rSign}${rDelta} mos)
                        </span>
                    </td>
                    <td>${formatCurrency(m.ending_cash)}</td>
                    <td>${formatCurrency(m.net_cash_flow)}</td>
                    <td>${formatCurrency(m.total_expense / m.duration_months)}/mo</td>
                    <td><span class="fintwin-risk-badge ${m.overall_risk_level}">${m.overall_risk_level} (${m.risk_score})</span></td>
                </tr>
            `;
        });

        tbody.innerHTML = rows;

        // Render Comparison Bar Chart
        const compareCtx = document.getElementById('fintwin-compare-chart')?.getContext('2d');
        if (compareCtx) {
            if (compareChartInstance) compareChartInstance.destroy();

            const chartLabels = ['Baseline', ...matrix.map(m => m.scenario_name)];
            const runwayValues = [base.cash_runway_months, ...matrix.map(m => m.cash_runway_months)];
            const endingCashValues = [base.estimated_cash, ...matrix.map(m => m.ending_cash)];

            compareChartInstance = new Chart(compareCtx, {
                type: 'bar',
                data: {
                    labels: chartLabels,
                    datasets: [
                        {
                            label: 'Runway (Months)',
                            data: runwayValues,
                            backgroundColor: '#2563eb',
                            yAxisID: 'y'
                        },
                        {
                            label: 'Ending Cash ($)',
                            data: endingCashValues,
                            backgroundColor: '#7c3aed',
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            type: 'linear',
                            position: 'left',
                            title: { display: true, text: 'Runway (Months)' }
                        },
                        y1: {
                            type: 'linear',
                            position: 'right',
                            grid: { drawOnChartArea: false },
                            ticks: { callback: v => '$' + (v / 1000).toFixed(0) + 'k' },
                            title: { display: true, text: 'Ending Cash ($)' }
                        }
                    }
                }
            });
        }

        modal.style.display = 'flex';
    }

    function closeCompareModal() {
        const modal = document.getElementById('fintwin-compare-modal');
        if (modal) modal.style.display = 'none';
    }

    // Expose methods to window.FinTwin
    window.FinTwin = {
        init: initFinTwin,
        loadScenario: loadScenarioIntoForm,
        runSimulation: runSimulationForScenario,
        deleteScenario: deleteScenario,
        loadSavedScenarios: loadSavedScenarios
    };

    // Initialize on DOM load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFinTwin);
    } else {
        initFinTwin();
    }
})();
