/**
 * Authentica Extension — Streamlined Popup Controller
 */

import {
  DEFAULT_API_URL,
  DEFAULT_WEB_APP_URL,
  MESSAGE_TYPES,
  MONITORING_STATES,
  POPUP_STATES,
  STORAGE_KEYS,
} from '../shared/constants.js';

import { checkBackendHealth, getApiUrl, getWebAppUrl } from '../shared/api.js';

// DOM Elements
const elements = {
  // Brand & Settings
  btnSettingsToggle: document.getElementById('btnSettingsToggle'),
  settingsDrawer: document.getElementById('settingsDrawer'),
  btnCloseSettings: document.getElementById('btnCloseSettings'),
  inputApiUrl: document.getElementById('inputApiUrl'),
  inputWebAppUrl: document.getElementById('inputWebAppUrl'),
  btnSaveSettings: document.getElementById('btnSaveSettings'),
  settingsFeedback: document.getElementById('settingsFeedback'),

  // Context
  tabHost: document.getElementById('tabHost'),

  // Views
  viewIdle: document.getElementById('viewIdle'),
  viewMonitoringSafe: document.getElementById('viewMonitoringSafe'),
  viewThreatAlert: document.getElementById('viewThreatAlert'),
  viewScanClean: document.getElementById('viewScanClean'),
  viewScanning: document.getElementById('viewScanning'),
  viewError: document.getElementById('viewError'),

  // Idle controls
  btnEnableProtection: document.getElementById('btnEnableProtection'),
  btnQuickScan: document.getElementById('btnQuickScan'),

  // Monitoring Safe controls
  statCycles: document.getElementById('statCycles'),
  btnStopProtection: document.getElementById('btnStopProtection'),

  // Threat Alert controls
  threatBadgeHeader: document.getElementById('threatBadgeHeader'),
  threatActionBanner: document.getElementById('threatActionBanner'),
  badgeAiStatus: document.getElementById('badgeAiStatus'),
  descAiStatus: document.getElementById('descAiStatus'),
  badgeHarmStatus: document.getElementById('badgeHarmStatus'),
  descHarmStatus: document.getElementById('descHarmStatus'),
  rowAudioRisk: document.getElementById('rowAudioRisk'),
  textAudioRisk: document.getElementById('textAudioRisk'),
  rowVideoRisk: document.getElementById('rowVideoRisk'),
  textVideoRisk: document.getElementById('textVideoRisk'),
  rowFraudRisk: document.getElementById('rowFraudRisk'),
  textFraudRisk: document.getElementById('textFraudRisk'),
  btnOpenThreatReport: document.getElementById('btnOpenThreatReport'),
  btnDismissThreat: document.getElementById('btnDismissThreat'),

  // Clean Scan controls
  cleanBadgeText: document.getElementById('cleanBadgeText'),
  cleanActionBanner: document.getElementById('cleanActionBanner'),
  cleanDescText: document.getElementById('cleanDescText'),
  btnOpenCleanReport: document.getElementById('btnOpenCleanReport'),
  btnCleanScanAgain: document.getElementById('btnCleanScanAgain'),

  // Quick Scan controls
  countdownVal: document.getElementById('countdownVal'),
  scanningTitle: document.getElementById('scanningTitle'),
  scanningDesc: document.getElementById('scanningDesc'),
  btnCancelScan: document.getElementById('btnCancelScan'),

  // Error controls
  errorMsgText: document.getElementById('errorMsgText'),
  btnResetView: document.getElementById('btnResetView'),

  // Footer
  backendStatusLabel: document.getElementById('backendStatusLabel'),
  btnOpenWeb: document.getElementById('btnOpenWeb'),
};

let currentTab = null;
let activeThreatSummary = null;
let healthCheckInterval = null;

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  await detectActiveTab();
  await loadSettings();
  await checkHealth();
  await syncStateWithServiceWorker();

  // Periodically check backend health while popup is active
  healthCheckInterval = setInterval(checkHealth, 3500);
});

window.addEventListener('unload', () => {
  if (healthCheckInterval) clearInterval(healthCheckInterval);
});

// Broadcast listener from background service worker
chrome.runtime.onMessage.addListener((message) => {
  if (!message) return;

  if (message.type === MESSAGE_TYPES.STATUS_UPDATE && message.payload) {
    applyGlobalState(message.payload);
  } else if (message.type === MESSAGE_TYPES.RECORDING_TICK && message.payload) {
    if (elements.countdownVal) {
      elements.countdownVal.textContent = Math.max(0, message.payload.secondsRemaining);
    }
  }
});

function setupEventListeners() {
  // Protection toggles
  elements.btnEnableProtection.addEventListener('click', handleEnableProtectionClick);
  elements.btnStopProtection.addEventListener('click', handleStopProtectionClick);

  // Quick scan
  elements.btnQuickScan.addEventListener('click', handleStartQuickScanClick);
  elements.btnCancelScan.addEventListener('click', handleCancelQuickScanClick);

  // Threat actions
  elements.btnOpenThreatReport.addEventListener('click', handleOpenThreatReportClick);
  elements.btnDismissThreat.addEventListener('click', handleDismissThreatClick);

  // Clean scan actions
  elements.btnOpenCleanReport?.addEventListener('click', handleOpenThreatReportClick);
  elements.btnCleanScanAgain?.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: MESSAGE_TYPES.RESET_STATE });
    showView(elements.viewIdle);
  });

  // Error
  elements.btnResetView.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: MESSAGE_TYPES.RESET_STATE });
    showView(elements.viewIdle);
  });

  // Settings
  elements.btnSettingsToggle.addEventListener('click', () => {
    elements.settingsDrawer.classList.toggle('hidden');
  });
  elements.btnCloseSettings.addEventListener('click', () => {
    elements.settingsDrawer.classList.add('hidden');
  });
  elements.btnSaveSettings.addEventListener('click', handleSaveSettingsClick);

  // Footer Web App Link
  elements.btnOpenWeb.addEventListener('click', async () => {
    const webAppUrl = await getWebAppUrl();
    chrome.tabs.create({ url: webAppUrl });
  });
}

/**
 * Detects current active tab in Chrome.
 */
async function detectActiveTab() {
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs || tabs.length === 0) {
      elements.tabHost.textContent = 'No tab focused';
      disableActionButtons('No tab focused');
      return;
    }

    currentTab = tabs[0];
    if (currentTab.url) {
      try {
        const u = new URL(currentTab.url);
        elements.tabHost.textContent = u.hostname || currentTab.title || 'Active Tab';
      } catch {
        elements.tabHost.textContent = currentTab.title || 'Active Tab';
      }

      if (isRestrictedUrl(currentTab.url)) {
        elements.tabHost.textContent = 'Browser Internal Page (Restricted)';
        disableActionButtons('Capture not available on internal pages');
      }
    }
  } catch (err) {
    console.warn('[Popup] Error querying tabs:', err);
  }
}

function isRestrictedUrl(url) {
  if (!url) return true;
  const restricted = ['chrome://', 'chrome-extension://', 'devtools://', 'edge://', 'about:', 'view-source:'];
  return restricted.some((prefix) => url.startsWith(prefix));
}

function disableActionButtons(reason) {
  elements.btnEnableProtection.disabled = true;
  elements.btnQuickScan.disabled = true;
  elements.btnEnableProtection.title = reason;
  elements.btnQuickScan.title = reason;
}

/**
 * Syncs UI with background service worker state.
 */
async function syncStateWithServiceWorker() {
  try {
    chrome.runtime.sendMessage({ type: MESSAGE_TYPES.GET_STATE }, (response) => {
      if (chrome.runtime.lastError || !response) {
        showView(elements.viewIdle);
        return;
      }
      applyGlobalState(response);
    });
  } catch {
    showView(elements.viewIdle);
  }
}

/**
 * Applies global service worker state to the popup views.
 */
function applyGlobalState(state) {
  if (!state) return;

  // 1. If a threat is actively flagged:
  if (state.monitoringStatus === MONITORING_STATES.THREAT_ALERT || state.activeThreat) {
    renderThreatAlert(state.activeThreat);
    return;
  }

  // 2. If quick scan is actively running:
  if (state.quickScan && state.quickScan.state === POPUP_STATES.CAPTURING) {
    elements.scanningTitle.textContent = 'Capturing Tab Media';
    elements.scanningDesc.textContent = 'Audio playback remains audible while capturing...';
    if (elements.countdownVal) {
      elements.countdownVal.textContent = state.quickScan.secondsRemaining || 10;
    }
    showView(elements.viewScanning);
    return;
  }

  if (state.quickScan && (state.quickScan.state === POPUP_STATES.UPLOADING || state.quickScan.state === POPUP_STATES.ANALYZING)) {
    elements.scanningTitle.textContent = 'Analyzing Forensic Models';
    elements.scanningDesc.textContent = 'Running EfficientNet, AASIST & Fraud Engine...';
    showView(elements.viewScanning);
    return;
  }

  if (state.quickScan && state.quickScan.state === POPUP_STATES.COMPLETED && state.quickScan.summary) {
    const summary = state.quickScan.summary;
    const isThreat = summary.fraudLevel === 'HIGH' || summary.fraudLevel === 'CRITICAL' || summary.action === 'STOP_AND_VERIFY' || Boolean(summary.requestedAction);
    if (isThreat) {
      renderThreatAlert(summary);
    } else {
      renderScanClean(summary);
    }
    return;
  }

  if (state.quickScan && state.quickScan.state === POPUP_STATES.ERROR) {
    renderError(state.quickScan.errorDetail);
    return;
  }

  // 3. If continuous monitoring is ON and safe:
  if (state.monitoringActive && state.monitoringStatus === MONITORING_STATES.MONITORING_SAFE) {
    elements.statCycles.textContent = state.cyclesCompleted || 0;
    showView(elements.viewMonitoringSafe);
    return;
  }

  // 4. Default: Idle
  showView(elements.viewIdle);
}

/**
 * Displays the appropriate single view card.
 */
function showView(targetView) {
  [
    elements.viewIdle,
    elements.viewMonitoringSafe,
    elements.viewThreatAlert,
    elements.viewScanClean,
    elements.viewScanning,
    elements.viewError,
  ].forEach((v) => {
    if (v) v.classList.add('hidden');
  });

  if (targetView) {
    targetView.classList.remove('hidden');
  }
}

/**
 * Handles "Turn On Protection" click.
 */
async function handleEnableProtectionClick() {
  if (!currentTab) return;

  chrome.runtime.sendMessage({
    type: MESSAGE_TYPES.START_MONITORING,
    payload: {
      tabId: currentTab.id,
      tabTitle: currentTab.title,
      tabUrl: currentTab.url,
    },
  }, (response) => {
    if (chrome.runtime.lastError || (response && !response.ok)) {
      renderError(response?.error || 'Could not start live protection on this tab.');
    } else {
      showView(elements.viewMonitoringSafe);
    }
  });
}

/**
 * Handles "Stop Protection" click.
 */
function handleStopProtectionClick() {
  chrome.runtime.sendMessage({ type: MESSAGE_TYPES.STOP_MONITORING });
  showView(elements.viewIdle);
}

/**
 * Handles single quick scan.
 */
async function handleStartQuickScanClick() {
  if (!currentTab) return;

  showView(elements.viewScanning);

  chrome.runtime.sendMessage({
    type: MESSAGE_TYPES.START_SCAN,
    payload: {
      tabId: currentTab.id,
      tabTitle: currentTab.title,
      tabUrl: currentTab.url,
    },
  }, (response) => {
    if (chrome.runtime.lastError || (response && !response.ok)) {
      renderError(response?.error || 'Could not capture current tab.');
    }
  });
}

function handleCancelQuickScanClick() {
  chrome.runtime.sendMessage({ type: MESSAGE_TYPES.CANCEL_SCAN });
  showView(elements.viewIdle);
}

/**
 * Renders prominent Threat Detected warning card with explicit AI-made & Harmful breakdown.
 */
function renderThreatAlert(summary) {
  if (!summary) return;
  activeThreatSummary = summary;

  const action = summary.action || 'STOP AND VERIFY';
  elements.threatActionBanner.textContent = action.replace(/_/g, ' ');

  const isDeepfake = summary.visualIsDeepfake || summary.audioIsSpoof || summary.mediaVerdict === 'LIKELY_MANIPULATED';
  const isSuspicious = !isDeepfake && (summary.visualIsSuspicious || summary.audioIsSuspicious || summary.mediaVerdict === 'SUSPICIOUS');
  const isHarmful = summary.fraudLevel === 'HIGH' || summary.fraudLevel === 'CRITICAL' || Boolean(summary.requestedAction);
  const isSuspiciousHarm = !isHarmful && summary.fraudLevel === 'MEDIUM';

  // 1. AI Deepfake Dimension
  if (isDeepfake) {
    if (elements.badgeAiStatus) {
      elements.badgeAiStatus.textContent = '🤖 AI DETECTED';
      elements.badgeAiStatus.className = 'dimension-status status-fake';
    }
    if (elements.descAiStatus) {
      if (summary.visualIsDeepfake && summary.audioIsSpoof) {
        elements.descAiStatus.textContent = 'Multi-modal: Synthetic face and cloned voice detected.';
      } else if (summary.visualIsDeepfake) {
        elements.descAiStatus.textContent = 'Facial deepfake / manipulation artifacts detected in video frames.';
      } else {
        elements.descAiStatus.textContent = 'Synthetic neural voice cloner characteristics detected.';
      }
    }
  } else if (isSuspicious) {
    if (elements.badgeAiStatus) {
      elements.badgeAiStatus.textContent = '🔍 SUSPICIOUS';
      elements.badgeAiStatus.className = 'dimension-status status-warn';
    }
    if (elements.descAiStatus) {
      elements.descAiStatus.textContent = 'Moderate anomalies observed; verification advised.';
    }
  } else {
    if (elements.badgeAiStatus) {
      elements.badgeAiStatus.textContent = '📷 AUTHENTIC';
      elements.badgeAiStatus.className = 'dimension-status status-clean';
    }
    if (elements.descAiStatus) {
      elements.descAiStatus.textContent = 'No strong synthetic alteration or face manipulation detected.';
    }
  }

  // 2. Harm & Fraud Intent Dimension
  if (isHarmful) {
    if (elements.badgeHarmStatus) {
      elements.badgeHarmStatus.textContent = '🚨 HARMFUL SCAM';
      elements.badgeHarmStatus.className = 'dimension-status status-harm';
    }
    if (elements.descHarmStatus) {
      if (summary.requestedAction) {
        elements.descHarmStatus.textContent = `Coercive action directive flagged: ${summary.requestedAction.replace(/_/g, ' ')}`;
      } else {
        elements.descHarmStatus.textContent = 'Social engineering patterns (urgency, secrecy, authority claim) flagged.';
      }
    }
  } else if (isSuspiciousHarm) {
    if (elements.badgeHarmStatus) {
      elements.badgeHarmStatus.textContent = '⚠️ SUSPICIOUS';
      elements.badgeHarmStatus.className = 'dimension-status status-warn';
    }
    if (elements.descHarmStatus) {
      elements.descHarmStatus.textContent = 'Mild urgency or financial keywords observed in transcript.';
    }
  } else {
    if (elements.badgeHarmStatus) {
      elements.badgeHarmStatus.textContent = '🛡️ HARMLESS';
      elements.badgeHarmStatus.className = 'dimension-status status-clean';
    }
    if (elements.descHarmStatus) {
      elements.descHarmStatus.textContent = 'No extortion, phishing, or financial extraction patterns found.';
    }
  }

  // Header badge text
  if (elements.threatBadgeHeader) {
    if (action === 'STOP_AND_VERIFY' || action === 'STOP') {
      elements.threatBadgeHeader.textContent = '🚨 CRITICAL RISK';
    } else if (action === 'CAUTION') {
      elements.threatBadgeHeader.textContent = '⚠️ CAUTION';
    } else {
      elements.threatBadgeHeader.textContent = '🔍 VERIFY SOURCE';
    }
  }

  // Modality rows
  const hasAudioRisk = summary.audioIsSpoof || (summary.audioLevel === 'HIGH' && summary.audioSpoofProb >= 0.70);
  if (hasAudioRisk) {
    elements.rowAudioRisk.classList.remove('hidden');
    elements.textAudioRisk.textContent = `Audio voice spoof flagged (${Math.round((summary.audioSpoofProb || 0.85) * 100)}%)`;
  } else {
    elements.rowAudioRisk.classList.add('hidden');
  }

  const hasVideoRisk = summary.visualIsDeepfake || (summary.visualLevel === 'HIGH' && summary.visualManipulationProb >= 0.70) || summary.mediaVerdict === 'LIKELY_MANIPULATED';
  if (hasVideoRisk) {
    elements.rowVideoRisk.classList.remove('hidden');
    elements.textVideoRisk.textContent = `Manipulated visual frames flagged (${Math.round((summary.visualManipulationProb || 0.8) * 100)}%)`;
  } else {
    elements.rowVideoRisk.classList.add('hidden');
  }

  const hasFraudRisk = isHarmful;
  if (hasFraudRisk) {
    elements.rowFraudRisk.classList.remove('hidden');
    elements.textFraudRisk.textContent = summary.requestedAction 
      ? `Coercive action: ${summary.requestedAction.replace(/_/g, ' ')}`
      : `Social engineering tactics detected (${summary.fraudLevel})`;
  } else {
    elements.rowFraudRisk.classList.add('hidden');
  }

  showView(elements.viewThreatAlert);
}

/**
 * Renders Clean / Verified scan result.
 */
function renderScanClean(summary) {
  if (!summary) return;
  activeThreatSummary = summary;

  const isSuspiciousMedia = summary.mediaVerdict === 'SUSPICIOUS' || summary.visualIsSuspicious || summary.audioIsSuspicious;
  const isUncertain = summary.mediaVerdict === 'UNCERTAIN';

  if (elements.cleanBadgeText) {
    if (isSuspiciousMedia) {
      elements.cleanBadgeText.textContent = '🟡 NO FRAUD DETECTED';
      elements.cleanBadgeText.className = 'safe-badge text-amber-500';
    } else {
      elements.cleanBadgeText.textContent = '🟢 NO THREAT DETECTED';
      elements.cleanBadgeText.className = 'safe-badge';
    }
  }

  if (elements.cleanActionBanner) {
    if (isSuspiciousMedia) {
      elements.cleanActionBanner.textContent = 'NORMAL MEDIA / NO SCAM';
      elements.cleanActionBanner.className = 'action-banner-text text-amber-500';
    } else {
      elements.cleanActionBanner.textContent = 'NO ACTION FLAGGED';
      elements.cleanActionBanner.className = 'action-banner-text text-green';
    }
  }

  if (elements.cleanDescText) {
    if (isSuspiciousMedia || isUncertain) {
      elements.cleanDescText.textContent = 'Analyzed tab media. No financial extraction, OTP theft, or coercive fraud patterns were detected.';
    } else {
      elements.cleanDescText.textContent = 'Analyzed sampled frames and audio track. Media and intent are harmless.';
    }
  }

  showView(elements.viewScanClean);
}

/**
 * Opens full analysis report in web app.
 */
async function handleOpenThreatReportClick() {
  const rawWebAppUrl = await getWebAppUrl();
  let webAppUrl = rawWebAppUrl ? rawWebAppUrl.trim().replace(/\/+$/, '') : DEFAULT_WEB_APP_URL;
  if (webAppUrl.includes('localhost') || webAppUrl.includes('127.0.0.1')) {
    webAppUrl = DEFAULT_WEB_APP_URL;
  }

  if (activeThreatSummary && activeThreatSummary.id) {
    chrome.tabs.create({ url: `${webAppUrl}/results/${activeThreatSummary.id}` });
  } else if (activeThreatSummary && activeThreatSummary.fullReportUrl && !activeThreatSummary.fullReportUrl.includes('localhost')) {
    chrome.tabs.create({ url: activeThreatSummary.fullReportUrl });
  } else {
    chrome.tabs.create({ url: webAppUrl });
  }
}

/**
 * Dismisses threat and resumes silent monitoring.
 */
function handleDismissThreatClick() {
  activeThreatSummary = null;
  chrome.runtime.sendMessage({ type: MESSAGE_TYPES.DISMISS_THREAT });
  showView(elements.viewMonitoringSafe);
}

function renderError(msg) {
  elements.errorMsgText.textContent = msg || 'Could not capture this tab.';
  showView(elements.viewError);
}

/**
 * Settings
 */
async function loadSettings() {
  const apiUrl = await getApiUrl();
  const webAppUrl = await getWebAppUrl();
  elements.inputApiUrl.value = apiUrl;
  elements.inputWebAppUrl.value = webAppUrl;
}

async function handleSaveSettingsClick() {
  let apiUrl = elements.inputApiUrl.value.trim().replace(/\/+$/, '') || DEFAULT_API_URL;
  let webAppUrl = elements.inputWebAppUrl.value.trim().replace(/\/+$/, '') || DEFAULT_WEB_APP_URL;

  // Auto-prefix https:// if protocol was omitted
  if (webAppUrl && !/^https?:\/\//i.test(webAppUrl)) {
    webAppUrl = webAppUrl.startsWith('localhost') || webAppUrl.startsWith('127.0.0.1')
      ? `http://${webAppUrl}`
      : `https://${webAppUrl}`;
  }
  if (apiUrl && !/^https?:\/\//i.test(apiUrl)) {
    apiUrl = apiUrl.startsWith('localhost') || apiUrl.startsWith('127.0.0.1')
      ? `http://${apiUrl}`
      : `https://${apiUrl}`;
  }

  await chrome.storage.local.set({
    [STORAGE_KEYS.API_URL]: apiUrl,
    [STORAGE_KEYS.WEB_APP_URL]: webAppUrl,
  });

  elements.inputApiUrl.value = apiUrl;
  elements.inputWebAppUrl.value = webAppUrl;

  elements.settingsFeedback.textContent = 'Settings saved.';
  await checkHealth();
  setTimeout(() => {
    elements.settingsDrawer.classList.add('hidden');
    elements.settingsFeedback.textContent = '';
  }, 1000);
}

async function checkHealth() {
  const health = await checkBackendHealth();
  if (health.ok) {
    elements.backendStatusLabel.textContent = 'Backend Online';
    elements.backendStatusLabel.style.color = '#10b981';
  } else {
    elements.backendStatusLabel.textContent = 'Backend Offline';
    elements.backendStatusLabel.style.color = '#ef4444';
  }
}

