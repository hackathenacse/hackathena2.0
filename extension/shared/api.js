/**
 * Authentica Extension — Backend API Integration Client
 */

import { DEFAULT_API_URL, DEFAULT_WEB_APP_URL, STORAGE_KEYS } from './constants.js';

/**
 * Retrieves configured Backend API URL with default fallback.
 */
export async function getApiUrl() {
  try {
    const data = await chrome.storage.local.get(STORAGE_KEYS.API_URL);
    const stored = data[STORAGE_KEYS.API_URL];
    if (stored && typeof stored === 'string' && !stored.includes('glory-rats') && stored.startsWith('http')) {
      return stored.replace(/\/+$/, '').replace(/\/api$/, '');
    }
    await chrome.storage.local.set({ [STORAGE_KEYS.API_URL]: DEFAULT_API_URL });
    return DEFAULT_API_URL;
  } catch {
    return DEFAULT_API_URL;
  }
}

/**
 * Retrieves configured Web Application URL with automatic Vercel tab detection and default fallback.
 */
export async function getWebAppUrl() {
  try {
    const data = await chrome.storage.local.get(STORAGE_KEYS.WEB_APP_URL);
    const stored = data[STORAGE_KEYS.WEB_APP_URL];
    if (stored && typeof stored === 'string' && stored.startsWith('http')) {
      return stored.replace(/\/+$/, '');
    }

    // Auto-detect open Authentica web app tabs (Vercel or custom hosted domain)
    if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.query) {
      const tabs = await chrome.tabs.query({});
      for (const tab of tabs) {
        if (tab.url && (tab.url.includes('.vercel.app') || (tab.title && tab.title.toUpperCase().includes('AUTHENTICA')))) {
          try {
            const parsed = new URL(tab.url);
            if (!parsed.protocol.startsWith('chrome') && !parsed.protocol.startsWith('about')) {
              const origin = parsed.origin;
              await chrome.storage.local.set({ [STORAGE_KEYS.WEB_APP_URL]: origin });
              return origin;
            }
          } catch {
            // skip invalid url
          }
        }
      }
    }

    await chrome.storage.local.set({ [STORAGE_KEYS.WEB_APP_URL]: DEFAULT_WEB_APP_URL });
    return DEFAULT_WEB_APP_URL;
  } catch {
    return DEFAULT_WEB_APP_URL;
  }
}

/**
 * Performs a fast health verification check against the backend with fallback.
 */
export async function checkBackendHealth(apiUrl) {
  let primary = (apiUrl || (await getApiUrl())).trim().replace(/\/+$/, '').replace(/\/api$/, '');
  const candidates = [primary];
  if (primary.includes('localhost')) {
    candidates.push(primary.replace('localhost', '127.0.0.1'));
  } else if (primary.includes('127.0.0.1')) {
    candidates.push(primary.replace('127.0.0.1', 'localhost'));
  }

  for (const target of candidates) {
    try {
      const res = await fetch(`${target}/api/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        signal: AbortSignal.timeout(6000),
      });
      if (res.ok) {
        const data = await res.json();
        return { ok: true, data, activeUrl: target };
      }
    } catch (err) {
      console.warn(`[Authentica] Health check failed for ${target}:`, err);
    }
  }
  return { ok: false, error: 'Cannot reach Authentica backend service.' };
}

/**
 * Uploads a captured media clip (WebM Blob) to the existing Authentica backend pipeline.
 * Reuses POST /api/analyses (Stage 1 -> Stage 2 -> Stage 3).
 *
 * @param {Blob} mediaBlob - Recorded WebM media clip
 * @param {string} [filename] - Upload filename
 * @param {object} [metadata] - Optional tab metadata
 */
export async function uploadClipForAnalysis(mediaBlob, filename, metadata = {}) {
  let apiUrl = (await getApiUrl()).trim().replace(/\/+$/, '').replace(/\/api$/, '');
  const webAppUrl = (await getWebAppUrl()).trim().replace(/\/+$/, '');

  if (!mediaBlob || mediaBlob.size === 0) {
    throw new Error('Recorded media clip is empty (0 bytes). Scan aborted.');
  }

  const uploadName = filename || `tab_capture_${Date.now()}.webm`;
  const formData = new FormData();
  formData.append('file', mediaBlob, uploadName);

  const candidates = [apiUrl];
  if (apiUrl.includes('localhost')) {
    candidates.push(apiUrl.replace('localhost', '127.0.0.1'));
  } else if (apiUrl.includes('127.0.0.1')) {
    candidates.push(apiUrl.replace('127.0.0.1', 'localhost'));
  }

  let response;
  let activeApiUrl = apiUrl;
  let lastErr = null;

  for (const target of candidates) {
    try {
      response = await fetch(`${target}/api/analyses`, {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json',
        },
      });
      if (response) {
        activeApiUrl = target;
        break;
      }
    } catch (err) {
      lastErr = err;
    }
  }

  if (!response) {
    throw new Error(`Analysis server unavailable at ${apiUrl}. Please verify the backend is running.`);
  }

  if (!response.ok) {
    let detail = `Server returned HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        detail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }

    if (response.status === 413) {
      throw new Error(`Captured clip exceeded maximum upload size limit: ${detail}`);
    } else if (response.status === 422 || response.status === 400) {
      throw new Error(`Media validation failed: ${detail}`);
    } else {
      throw new Error(`Analysis failed (${response.status}): ${detail}`);
    }
  }

  const data = await response.json();

  const visualLevel = data.evidence?.visual?.level || 'N/A';
  const audioLevel = data.evidence?.audio?.level || 'N/A';
  const visualMean = data.evidence?.visual?.statistics?.mean_score || 0;
  const audioMean = data.evidence?.audio?.statistics?.mean_score || 0;
  const fraudLevel = data.assessment?.fraud || data.fraud?.level || 'LOW';
  const action = data.assessment?.action || 'NO_ACTION_FLAGGED';
  const mediaVerdict = data.assessment?.media || 'NO_STRONG_EVIDENCE';

  const isVisualHigh = visualLevel === 'HIGH' || visualMean >= 0.72;
  const isAudioHigh = audioLevel === 'HIGH' || audioMean >= 0.72;
  const isVisualSuspect = visualLevel === 'MEDIUM' || (visualMean >= 0.50 && visualMean < 0.72);
  const isAudioSuspect = audioLevel === 'MEDIUM' || (audioMean >= 0.50 && audioMean < 0.72);

  // Extract compact warning summary without altering backend verdicts
  const summary = {
    id: data.id,
    status: data.status,
    action,
    mediaVerdict,
    fraudLevel,
    visualLevel,
    audioLevel,
    visualManipulationProb: visualMean,
    visualIsDeepfake: isVisualHigh,
    visualIsSuspicious: isVisualSuspect,
    audioSpoofProb: audioMean,
    audioIsSpoof: isAudioHigh,
    audioIsSuspicious: isAudioSuspect,
    fraudRiskScore: fraudLevel === 'HIGH' ? 0.9 : (fraudLevel === 'MEDIUM' ? 0.5 : 0.1),
    requestedAction: data.fraud?.requested_actions?.[0]?.action || null,
    explanations: Array.isArray(data.explanation) ? data.explanation.slice(0, 3) : [],
    fullReportUrl: `${(webAppUrl && !webAppUrl.includes('localhost') && !webAppUrl.includes('127.0.0.1')) ? webAppUrl : DEFAULT_WEB_APP_URL}/results/${data.id}`,
    timestamp: Date.now(),
    capturedTabTitle: metadata.tabTitle || 'Current Tab',
    capturedTabUrl: metadata.tabUrl || '',
  };

  return { raw: data, summary };
}
