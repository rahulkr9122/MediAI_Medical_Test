const tabs = document.querySelectorAll('nav button');
const panels = document.querySelectorAll('.tab-panel');
const reportCity = document.getElementById('reportCity');
const reportText = document.getElementById('reportText');
const reportFile = document.getElementById('reportFile');
const analysisLanguage = document.getElementById('analysisLanguage');
const analyzeButton = document.getElementById('analyzeButton');
const analysisResult = document.getElementById('analysisResult');
const sampleButton = document.getElementById('sampleButton');
const historyList = document.getElementById('historyList');

const sampleReport = `Patient Name: Rahul
Age: 47
Test: Lipid profile, fasting blood sugar, kidney function

Results:
- Total cholesterol: 265 mg/dL (high)
- LDL cholesterol: 170 mg/dL (high)
- HDL cholesterol: 38 mg/dL (low)
- Triglycerides: 210 mg/dL (high)
- Fasting glucose: 140 mg/dL (elevated)
- Creatinine: 1.5 mg/dL (slightly elevated)
- eGFR: 58 mL/min/1.73m2 (mildly reduced)

Interpretation: Findings suggest dyslipidemia, prediabetes/diabetes risk, and early kidney stress. Recommend lifestyle changes, medication review, and specialist consultation.`;

function switchTab(tabName) {
  tabs.forEach((button) => {
    button.classList.toggle('active', button.dataset.tab === tabName);
  });
  panels.forEach((panel) => {
    panel.classList.toggle('active', panel.id === 'tab-' + tabName);
  });
}

tabs.forEach((button) => {
  button.addEventListener('click', () => switchTab(button.dataset.tab));
});

sampleButton.addEventListener('click', () => {
  reportText.value = sampleReport;
});

analyzeButton.addEventListener('click', async () => {
  const text = reportText.value.trim();
  const city = reportCity.value.trim();
  const file = reportFile.files[0];
  const language = analysisLanguage.value;
  
  if (!text && !file) {
    analysisResult.textContent = 'Please paste a report or upload a text file.';
    return;
  }
  
  if (!city) {
    analysisResult.textContent = 'Please enter a city to find doctors and hospitals.';
    return;
  }

  analysisResult.innerHTML = `
    <div class="scanner-container">
      <div class="scanner-document">
        <div class="scanner-line"></div>
        <div class="scanner-text">Scanning...</div>
      </div>
    </div>
  `;
  const formData = new FormData();
  formData.append('reportText', text);
  formData.append('city', city);
  formData.append('language', language);
  if (file) {
    formData.append('reportFile', file);
  }

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      body: formData,
    });

    let result;
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      result = await response.json();
    } else {
      const text = await response.text();
      console.error("Non-JSON response from server:", text);
      throw new Error(`Server returned ${response.status} (Not JSON). This usually means a timeout or server crash. Check Render logs!`);
    }

    if (!response.ok) {
      analysisResult.textContent = result.error || 'Analysis failed.';
      return;
    }
    
    const escapedAnalysis = result.analysis
      .replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/\[HIGHLIGHT\]/gi, '<div class="highlight-doctors">')
      .replace(/\[\/HIGHLIGHT\]/gi, '</div>');

    let html = `
      <div class="analysis-summary">
        <strong>Specialist Recommended:</strong> ${result.specialist}<br />
        <strong>Severity:</strong> ${result.severity}
      </div>
      <div class="analysis-text">
        <pre>${escapedAnalysis}</pre>
      </div>
      <button id="resetButton" class="primary" style="margin-top: 20px; width: 100%;">Upload Another Document</button>
    `;
    
    analysisResult.innerHTML = html;

    document.getElementById('resetButton').addEventListener('click', () => {
      reportText.value = '';
      reportFile.value = '';
      analysisResult.innerHTML = 'Fill in all fields and click "Analyze with AI" to get analysis and doctor recommendations.';
    });
  } catch (error) {
    console.error("Frontend caught an error:", error);
    analysisResult.textContent = error.message || 'Error: The server failed to respond properly. Check your Render logs or the browser console for more details.';
  }
});

async function loadHistory() {
  try {
    const response = await fetch('/api/history');
    const result = await response.json();
    if (!response.ok) {
      historyList.textContent = 'Failed to load history.';
      return;
    }
    if (!result.history.length) {
      historyList.textContent = 'No past analyses yet.';
      return;
    }
    historyList.innerHTML = result.history
      .map(
        (item) => `
        <div class="history-card">
          <div class="history-top">
            <strong>${new Date(item.timestamp).toLocaleString()}</strong>
            <span class="tag">${item.severity}</span>
          </div>
          <div><strong>Suggested specialist:</strong> ${item.specialist}</div>
          <div>${item.report_excerpt}</div>
        </div>`
      )
      .join('');
  } catch (error) {
    historyList.textContent = 'Unable to load history.';
  }
}

loadHistory();

// Add custom branding and identification for Rahul
const developerBadge = document.createElement('div');
developerBadge.innerHTML = '✨ Engineered by <strong>Rahul</strong>';
developerBadge.style.cssText = 'text-align: center; margin-top: 2rem; padding: 1.5rem 0; color: #b8c1d4; font-size: 0.95rem; border-top: 1px solid #24304f; font-weight: 500; letter-spacing: 0.5px;';
const appShell = document.querySelector('.app-shell');
if (appShell) {
  appShell.appendChild(developerBadge);
} else {
  document.body.appendChild(developerBadge);
}
