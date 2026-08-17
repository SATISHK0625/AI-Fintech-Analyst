// Global Application State & Helper Functions
window.currentCompanyId = parseInt(localStorage.getItem('activeCompanyId') || '1');
window.currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
let currentSessionId = null;
window._cachedReports = [];
window._activeReportId = null;

// Helper: Markdown parser with fallback
function parseMarkdownText(text) {
    if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
        return marked.parse(text || '');
    }
    return (text || '').replace(/\n/g, '<br>');
}

function updateCompanyHeaderUI(companyName, industry, userName) {
    const compEl = document.getElementById('current-company-name');
    if (compEl) compEl.innerText = companyName || 'Enterprise Workspace';

    const userBadge = document.getElementById('user-badge-name');
    if (userBadge) {
        if (userName) {
            userBadge.innerText = `${userName.split(' ')[0]} (Log Out)`;
        } else {
            userBadge.innerText = `Log Out`;
        }
    }
}

// Show / Hide Auth Screen vs Main Application Dashboard
function checkAuthViewState() {
    const authScreen = document.getElementById('auth-portal-screen');
    const mainLayout = document.getElementById('main-app-layout');

    if (window.currentUser && window.currentUser.id) {
        if (authScreen) authScreen.style.display = 'none';
        if (mainLayout) mainLayout.style.display = 'flex';

        updateCompanyHeaderUI(window.currentUser.company_name, window.currentUser.industry, window.currentUser.full_name);
        window.loadOverviewData();
        window.loadAuditData();
        window.loadChatSessions();
        window.loadSavedReports();
        window.updateTelemetryBadge();
    } else {
        if (authScreen) authScreen.style.display = 'flex';
        if (mainLayout) mainLayout.style.display = 'none';
    }
}

window.logoutUser = function () {
    localStorage.removeItem('currentUser');
    localStorage.removeItem('activeCompanyId');
    window.currentUser = null;
    window.currentCompanyId = 1;
    checkAuthViewState();
};

// 1. Overview & KPI Metrics Loader
window.loadOverviewData = async function () {
    if (!window.currentUser) return;
    try {
        const compId = window.currentCompanyId || window.currentUser.company_id || 1;
        const res = await fetch(`/api/financial/metrics?company_id=${compId}`);
        if (!res.ok) return;
        const data = await res.json();

        // Populate KPI Cards
        const runwayEl = document.getElementById('kpi-runway');
        const burnEl = document.getElementById('kpi-burn');
        const gmEl = document.getElementById('kpi-gross-margin');

        if (runwayEl) runwayEl.innerText = `${data.cash_runway_months || 0} mos`;
        if (burnEl) burnEl.innerText = `$${(data.net_burn_rate || 0).toLocaleString()}/mo`;
        if (gmEl) gmEl.innerText = `${data.gross_margin_pct || 0}%`;

        // Render Charts
        if (data.monthly_trend && window.renderTrendChart) {
            renderTrendChart(data.monthly_trend);
        }
        if (data.category_expenses && window.renderCategoryChart) {
            renderCategoryChart(data.category_expenses);
        }
    } catch (e) {
        console.error("Error loading overview metrics:", e);
    }
};

// 2. Audit Center Anomalies Loader
window.loadAuditData = async function () {
    if (!window.currentUser) return;
    try {
        const compId = window.currentCompanyId || window.currentUser.company_id || 1;
        const res = await fetch(`/api/financial/anomalies?company_id=${compId}`);
        if (!res.ok) return;
        const flags = await res.json();

        const tbody = document.getElementById('anomalies-table-body');
        const sidebarBadge = document.getElementById('sidebar-anomaly-count');
        const riskKpi = document.getElementById('kpi-risk-score');
        const highRiskNum = document.getElementById('high-risk-num');
        const medRiskNum = document.getElementById('med-risk-num');

        const openFlags = flags.filter(f => f.status === 'OPEN');
        if (sidebarBadge) sidebarBadge.innerText = openFlags.length;
        if (riskKpi) riskKpi.innerText = openFlags.length > 0 ? `${openFlags.length} Flags` : '0 (Low Risk)';

        const highCount = openFlags.filter(f => f.severity === 'HIGH').length;
        const medCount = openFlags.filter(f => f.severity === 'MEDIUM').length;
        if (highRiskNum) highRiskNum.innerText = highCount;
        if (medRiskNum) medRiskNum.innerText = medCount;

        if (!tbody) return;

        if (flags.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No audit anomalies detected. Ledger is clean!</td></tr>`;
            return;
        }

        tbody.innerHTML = flags.map(f => `
            <tr>
                <td><span class="badge-sev ${f.severity}">${f.severity}</span></td>
                <td><strong>${f.flag_type}</strong></td>
                <td>
                    <div class="font-weight-bold">${f.title}</div>
                    <div class="text-muted" style="font-size:12px;">${f.description}</div>
                </td>
                <td><span class="status-pill ${f.status.toLowerCase()}">${f.status}</span></td>
                <td>
                    ${f.status === 'OPEN' ? `
                        <button class="btn btn-outline" style="padding:4px 10px; font-size:12px;" onclick="window.resolveFlag(${f.id})">
                            <i class="fa-solid fa-check"></i> Resolve
                        </button>
                    ` : '<span class="text-muted" style="font-size:12px;">Resolved</span>'}
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error("Error loading audit flags:", e);
    }
};

window.resolveFlag = async function (flagId) {
    try {
        const res = await fetch(`/api/financial/anomalies/${flagId}/resolve`, { method: 'POST' });
        if (res.ok) {
            window.loadAuditData();
            window.loadOverviewData();
        }
    } catch (e) {
        alert("Failed to resolve anomaly: " + e.message);
    }
};

// 3. Saved Reports Loader
window.loadSavedReports = async function () {
    if (!window.currentUser) return;
    try {
        const compId = window.currentCompanyId || window.currentUser.company_id || 1;
        const res = await fetch(`/api/agent/reports?company_id=${compId}`);
        if (!res.ok) return;
        const reports = await res.json();
        window._cachedReports = reports;

        const listContainer = document.getElementById('saved-reports-list');
        if (!listContainer) return;

        if (reports.length === 0) {
            listContainer.innerHTML = `<p class="text-muted">No executive reports generated yet.</p>`;
            return;
        }

        listContainer.innerHTML = reports.map(r => `
            <div class="report-history-item ${window._activeReportId === r.id ? 'active' : ''}" onclick="window.viewReport(${r.id})">
                <div class="report-title">${r.title}</div>
                <div class="report-meta">
                    <span><i class="fa-solid fa-calendar-day"></i> ${r.created_at}</span>
                    <span class="badge-pill danger">${r.anomalies_count} Risks</span>
                </div>
            </div>
        `).join('');

        if (!window._activeReportId && reports.length > 0) {
            window.viewReport(reports[0].id);
        }
    } catch (e) {
        console.error("Error loading reports:", e);
    }
};

window.viewReport = function (reportId) {
    window._activeReportId = reportId;
    const report = window._cachedReports.find(r => r.id === reportId);
    const viewContainer = document.getElementById('report-view-container');

    if (!viewContainer || !report) return;

    viewContainer.innerHTML = `
        <div class="report-header">
            <div>
                <h2>${report.title}</h2>
                <span class="text-muted"><i class="fa-solid fa-clock"></i> Generated ${report.created_at}</span>
            </div>
            <button class="btn btn-outline" onclick="window.printReport()"><i class="fa-solid fa-print"></i> Print</button>
        </div>
        <div class="report-body markdown-content">
            ${parseMarkdownText(report.markdown_report)}
        </div>
    `;

    window.loadSavedReports();
};

window.printReport = function () {
    const content = document.getElementById('report-view-container');
    if (!content) return;
    const win = window.open('', '', 'width=900,height=700');
    win.document.write(`<html><head><title>Executive Financial Report</title><link rel="stylesheet" href="/static/css/styles.css"></head><body style="padding:30px;">${content.innerHTML}</body></html>`);
    win.document.close();
    win.focus();
    setTimeout(() => win.print(), 500);
};

// 4. Chat Sessions & Conversational Assistant
window.loadChatSessions = async function () {
    if (!window.currentUser) return;
    try {
        const compId = window.currentCompanyId || window.currentUser.company_id || 1;
        const res = await fetch(`/api/agent/sessions?company_id=${compId}`);
        if (!res.ok) return;
        const sessions = await res.json();

        const listEl = document.getElementById('chat-sessions-list');
        if (!listEl) return;

        if (sessions.length === 0) {
            listEl.innerHTML = `<p class="text-muted">No chat history.</p>`;
            return;
        }

        listEl.innerHTML = sessions.map(s => `
            <div class="session-item ${currentSessionId === s.session_id ? 'active' : ''}" onclick="window.switchChatSession('${s.session_id}')">
                <i class="fa-regular fa-comments"></i>
                <div class="session-title">${s.title}</div>
            </div>
        `).join('');
    } catch (e) {
        console.error("Error loading chat sessions:", e);
    }
};

window.switchChatSession = async function (sessionId) {
    currentSessionId = sessionId;
    const compId = window.currentCompanyId || window.currentUser.company_id || 1;
    const res = await fetch(`/api/agent/sessions/${sessionId}?company_id=${compId}`);
    if (!res.ok) return;
    const messages = await res.json();

    const chatContainer = document.getElementById('chat-messages-container');
    if (!chatContainer) return;

    chatContainer.innerHTML = messages.map(m => {
        const isUser = m.sender === 'user';
        return `
            <div class="chat-message-row ${isUser ? 'user' : 'assistant'}">
                <div class="chat-avatar ${isUser ? 'user' : 'assistant'}">
                    <i class="fa-solid ${isUser ? 'fa-user' : 'fa-robot'}"></i>
                </div>
                <div class="chat-bubble ${isUser ? 'user' : 'assistant'}">
                    <div class="message-sender">${isUser ? 'You' : (m.agent_name || 'FinAuditor AI')}</div>
                    <div class="message-text ${isUser ? '' : 'markdown-content'}">${isUser ? m.message : parseMarkdownText(m.message)}</div>
                    <div class="chat-time">${m.created_at || 'Just now'}</div>
                </div>
            </div>
        `;
    }).join('');

    chatContainer.scrollTop = chatContainer.scrollHeight;
    window.loadChatSessions();
};

// Telemetry Badge
window.updateTelemetryBadge = async function () {
    try {
        const res = await fetch('/api/agent/telemetry');
        if (!res.ok) return;
        const data = await res.json();
        const last = data.last || {};

        const tokenEl = document.getElementById('telemetry-tokens');
        const latencyEl = document.getElementById('telemetry-latency');

        if (tokenEl) tokenEl.innerText = `${last.total_tokens || 0} tokens`;
        if (latencyEl) latencyEl.innerText = `${last.duration_ms || 0} ms`;
    } catch (e) {
        console.error("Telemetry update error:", e);
    }
};

// Workflow Animation Visualizer
async function runWorkflowAnimation(queryText) {
    const logBox = document.getElementById('agent-logs-box');
    const nodes = ['planner', 'retrieval', 'analysis', 'audit', 'recommendation', 'report'];

    if (logBox) logBox.innerHTML = `<div class="text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Executing Agentic Workflow...</div>`;

    const logEntries = [
        "Planner Agent: Formulating query execution strategy...",
        "Retrieval Agent: Fetching ledger & RAG vector chunks...",
        "Analysis Agent: Computing financial metrics & cash runway...",
        "Audit Agent: Auditing transactions for risk anomalies...",
        "Recommendation Agent: Formulating executive recommendations...",
        "Report Agent: Compiling executive report artifact..."
    ];

    for (let i = 0; i < nodes.length; i++) {
        const el = document.getElementById(`node-${nodes[i]}`);
        if (el) el.classList.add('active-node');

        if (logBox) {
            logBox.innerHTML += `<div><strong>[${nodes[i].toUpperCase()}]</strong> ${logEntries[i]}</div>`;
            logBox.scrollTop = logBox.scrollHeight;
        }

        await new Promise(r => setTimeout(r, 400));

        if (el) {
            el.classList.remove('active-node');
            el.classList.add('completed-node');
        }
    }
}

// App Initialization & Event Listeners
function initApp() {
    // Navigation Tabs Handler
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            const tabName = item.getAttribute('data-tab');
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

            const targetTab = document.getElementById(`tab-${tabName}`);
            if (targetTab) targetTab.classList.add('active');

            const heading = document.getElementById('tab-heading');
            const subheading = document.getElementById('tab-subheading');

            const titles = {
                'overview': ['Executive Financial Overview', 'Real-time SME cash health, gross margin, and burn analytics'],
                'audit': ['Automated Audit & Anomaly Center', 'Rule-based and AI anomaly detection for financial risk control'],
                'agent-console': ['Multi-Agent AI Execution Console', 'Live LangGraph node visualization and interactive prompt testing'],
                'data-ingest': ['Data & Policy Ingestion Engine', 'Upload CSV bank ledgers or PDF enterprise policy handbooks'],
                'reports': ['Executive Report History', 'Permanent audit trail of past AI-generated financial reviews']
            };

            if (titles[tabName]) {
                if (heading) heading.innerText = titles[tabName][0];
                if (subheading) subheading.innerText = titles[tabName][1];
            }
        });
    });

    // Chat Form & Keypress Handler
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const btnNewChat = document.getElementById('btn-new-chat');

    if (btnNewChat) {
        btnNewChat.addEventListener('click', () => {
            currentSessionId = null;
            const container = document.getElementById('chat-messages-container');
            if (container) {
                container.innerHTML = `
                    <div class="chat-welcome-box">
                        <div class="welcome-icon"><i class="fa-solid fa-sparkles"></i></div>
                        <h2>How can I help with your financial data today?</h2>
                        <p>Ask questions in plain human language about cash flow, burn rate, vendor expenses, or audit rules.</p>
                        <div class="preset-buttons">
                            <button type="button" class="btn-chip" onclick="window.sendPresetMessage('What is our current cash runway and net burn rate?')">Cash Runway & Burn</button>
                            <button type="button" class="btn-chip" onclick="window.sendPresetMessage('Are there any duplicate invoice payments in the ledger?')">Check Duplicates</button>
                            <button type="button" class="btn-chip" onclick="window.sendPresetMessage('What is our gross margin percentage?')">Gross Margin Target</button>
                        </div>
                    </div>
                `;
            }
            const label = document.getElementById('current-session-label');
            if (label) label.innerText = 'Session: New';
        });
    }

    window.sendPresetMessage = function (presetText) {
        const input = document.getElementById('chat-input');
        const form = document.getElementById('chat-form');
        if (input && form) {
            input.value = presetText;
            form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        }
    };

    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (chatForm) {
                    chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                }
            }
        });
    }

    if (chatForm && chatInput) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = chatInput.value.trim();
            if (!text) return;

            chatInput.value = '';

            const chatContainer = document.getElementById('chat-messages-container');
            if (chatContainer) {
                chatContainer.innerHTML += `
                    <div class="chat-message-row user">
                        <div class="chat-avatar user"><i class="fa-solid fa-user"></i></div>
                        <div class="chat-bubble user">
                            <div class="message-sender">You</div>
                            <div class="message-text">${text}</div>
                            <div class="chat-time">Just now</div>
                        </div>
                    </div>
                `;

                // Add Typing Indicator
                const typingId = `typing-${Date.now()}`;
                chatContainer.innerHTML += `
                    <div class="chat-message-row assistant" id="${typingId}">
                        <div class="chat-avatar assistant"><i class="fa-solid fa-robot"></i></div>
                        <div class="chat-bubble assistant">
                            <div class="message-sender">FinAuditor AI</div>
                            <div class="message-text text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Analyzing financial ledgers & policies...</div>
                        </div>
                    </div>
                `;
                chatContainer.scrollTop = chatContainer.scrollHeight;

                try {
                    const compId = window.currentCompanyId || (window.currentUser ? window.currentUser.company_id : 1);
                    const animPromise = runWorkflowAnimation(text);

                    const res = await fetch('/api/agent/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            query: text,
                            session_id: currentSessionId,
                            company_id: compId
                        })
                    });

                    const data = await res.json();
                    await animPromise;

                    if (data.session_id) currentSessionId = data.session_id;

                    const typingEl = document.getElementById(typingId);
                    if (typingEl) typingEl.remove();

                    if (chatContainer && data.response) {
                        chatContainer.innerHTML += `
                            <div class="chat-message-row assistant">
                                <div class="chat-avatar assistant"><i class="fa-solid fa-robot"></i></div>
                                <div class="chat-bubble assistant">
                                    <div class="message-sender">FinAuditor AI</div>
                                    <div class="message-text markdown-content">${parseMarkdownText(data.response)}</div>
                                    <div class="chat-time">Just now</div>
                                </div>
                            </div>
                        `;
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }

                    window.loadChatSessions();
                    window.updateTelemetryBadge();
                } catch (err) {
                    console.error("Chat error:", err);
                    const typingEl = document.getElementById(typingId);
                    if (typingEl) {
                        typingEl.querySelector('.message-text').innerHTML = `<span class="text-danger"><i class="fa-solid fa-triangle-exclamation"></i> Error sending message. Please try again.</span>`;
                    }
                }
            }
        });
    }

    // Quick Audit Action Header Button
    const btnQuickAudit = document.getElementById('btn-quick-audit');
    if (btnQuickAudit) {
        btnQuickAudit.addEventListener('click', async () => {
            btnQuickAudit.disabled = true;
            btnQuickAudit.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Auditing...`;

            try {
                const compId = window.currentCompanyId || (window.currentUser ? window.currentUser.company_id : 1);
                const animPromise = runWorkflowAnimation("Executive Financial & Anomaly Scan");

                const res = await fetch('/api/agent/generate-report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: "Audit transaction ledger for duplicate invoice payments and policy violations", company_id: compId })
                });

                const data = await res.json();
                await animPromise;

                if (data.status === 'success') {
                    window.loadOverviewData();
                    window.loadAuditData();
                    window.loadSavedReports();

                    const reportsTabBtn = document.querySelector('.nav-item[data-tab="reports"]');
                    if (reportsTabBtn) reportsTabBtn.click();
                    if (data.report_id) window.viewReport(data.report_id);
                }
            } catch (e) {
                alert(`Audit Scan Error: ${e.message}`);
            } finally {
                btnQuickAudit.disabled = false;
                btnQuickAudit.innerHTML = `<i class="fa-solid fa-magnifying-glass-dollar"></i> Run Audit`;
            }
        });
    }

    // Executive Report Generation Action Button
    const btnGenerateReport = document.getElementById('btn-generate-report-tab');
    if (btnGenerateReport) {
        btnGenerateReport.addEventListener('click', async () => {
            btnGenerateReport.disabled = true;
            btnGenerateReport.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Generating Report...`;

            try {
                const compId = window.currentCompanyId || (window.currentUser ? window.currentUser.company_id : 1);
                const animPromise = runWorkflowAnimation("Multi-Agent Executive Report Synthesis");

                const res = await fetch('/api/agent/generate-report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: "Executive Financial & Audit Performance Report", company_id: compId })
                });

                const data = await res.json();
                await animPromise;

                if (data.status === 'success') {
                    await window.loadSavedReports();
                    if (data.report_id) {
                        window.viewReport(data.report_id);
                    }
                }
            } catch (e) {
                alert(`Report Generation Error: ${e.message}`);
            } finally {
                btnGenerateReport.disabled = false;
                btnGenerateReport.innerHTML = `<i class="fa-solid fa-file-contract"></i> Generate Report`;
            }
        });
    }

    // Initialize Auth Handlers & Check View State
    initEnterpriseAuthPortal();
    checkAuthViewState();
}

// Enterprise Authentication Portal Logic
function initEnterpriseAuthPortal() {
    const btnTabSignIn = document.getElementById('auth-tab-signin-btn');
    const btnTabRegister = document.getElementById('auth-tab-register-btn');
    const formSignInContainer = document.getElementById('form-signin-container');
    const formRegisterContainer = document.getElementById('form-register-container');
    const alertBox = document.getElementById('auth-alert');

    function showAlert(msg, isError = true) {
        if (!alertBox) return;
        alertBox.style.display = 'flex';
        alertBox.className = `auth-alert ${isError ? 'error' : 'success'}`;
        alertBox.innerHTML = isError ? `<i class="fa-solid fa-circle-exclamation"></i> ${msg}` : `<i class="fa-solid fa-circle-check"></i> ${msg}`;
    }

    function hideAlert() {
        if (alertBox) alertBox.style.display = 'none';
    }

    if (btnTabSignIn && btnTabRegister) {
        btnTabSignIn.addEventListener('click', () => {
            btnTabSignIn.classList.add('active');
            btnTabRegister.classList.remove('active');
            if (formSignInContainer) formSignInContainer.style.display = 'block';
            if (formRegisterContainer) formRegisterContainer.style.display = 'none';
            hideAlert();
        });

        btnTabRegister.addEventListener('click', () => {
            btnTabRegister.classList.add('active');
            btnTabSignIn.classList.remove('active');
            if (formRegisterContainer) formRegisterContainer.style.display = 'block';
            if (formSignInContainer) formSignInContainer.style.display = 'none';
            hideAlert();
        });
    }

    // 1. LOGIN SUBMIT HANDLER
    const portalLoginForm = document.getElementById('portal-login-form');
    if (portalLoginForm) {
        portalLoginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideAlert();

            const email = document.getElementById('login-email-input').value.trim();
            const password = document.getElementById('login-password-input').value.trim();

            const submitBtn = document.getElementById('login-submit-btn');
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Authenticating...`;

            try {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                const data = await res.json();

                if (res.ok && data.status === 'success') {
                    window.currentUser = data.user;
                    window.currentCompanyId = data.user.company_id;
                    localStorage.setItem('currentUser', JSON.stringify(data.user));
                    localStorage.setItem('activeCompanyId', data.user.company_id.toString());

                    showAlert(`Welcome back, ${data.user.full_name}! Connected to ${data.user.company_name}.`, false);
                    setTimeout(() => {
                        checkAuthViewState();
                    }, 400);
                } else {
                    showAlert(data.detail || 'Invalid email or password. If you do not have an account, click Register Enterprise above.');
                }
            } catch (err) {
                showAlert('Server connection error: ' + err.message);
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<i class="fa-solid fa-arrow-right-to-bracket"></i> Sign In to Financial Dashboard`;
            }
        });
    }

    // 2. REGISTER SUBMIT HANDLER
    const portalRegisterForm = document.getElementById('portal-register-form');
    if (portalRegisterForm) {
        portalRegisterForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideAlert();

            const fullName = document.getElementById('reg-fullname').value.trim();
            const email = document.getElementById('reg-useremail').value.trim();
            const password = document.getElementById('reg-userpass').value.trim();
            const companyName = document.getElementById('reg-companyname').value.trim();
            const industry = document.getElementById('reg-industrysector').value;

            const csvInput = document.getElementById('reg-csvfile');
            const policyInput = document.getElementById('reg-policyfile');

            const submitBtn = document.getElementById('register-submit-btn');
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Initializing Workspace & Ingesting Files...`;

            const formData = new FormData();
            formData.append('full_name', fullName);
            formData.append('email', email);
            formData.append('password', password);
            formData.append('company_name', companyName);
            formData.append('industry', industry);

            if (csvInput && csvInput.files.length > 0) {
                formData.append('csv_file', csvInput.files[0]);
            }
            if (policyInput && policyInput.files.length > 0) {
                formData.append('policy_file', policyInput.files[0]);
            }

            try {
                const res = await fetch('/api/auth/register', {
                    method: 'POST',
                    body: formData
                });

                const data = await res.json();

                if (res.ok && data.status === 'success') {
                    window.currentUser = data.user;
                    window.currentCompanyId = data.user.company_id;
                    localStorage.setItem('currentUser', JSON.stringify(data.user));
                    localStorage.setItem('activeCompanyId', data.user.company_id.toString());

                    showAlert(`Registration Successful! Connected to ${data.user.company_name}. CSV: ${data.csv_summary} | RAG: ${data.policy_summary}`, false);
                    setTimeout(() => {
                        checkAuthViewState();
                    }, 600);
                } else {
                    showAlert(data.detail || 'Registration failed. Please check form fields.');
                }
            } catch (err) {
                showAlert('Registration error: ' + err.message);
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<i class="fa-solid fa-rocket"></i> Register Workspace & Initialize AI Dashboard`;
            }
        });
    }
}

// Fail-safe DOM Ready Execution
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
