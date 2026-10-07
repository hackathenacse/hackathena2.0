/**
 * Authentica Extension — Offscreen Media Capture & Monitoring Engine
 *
 * Capabilities:
 * 1. Consumes tab capture stream ID via getUserMedia()
 * 2. Preserves tab audio playback via AudioContext -> destination
 * 3. Dynamically selects supported MediaRecorder WebM MIME type
 * 4. Supports both single 8-second quick scans and continuous tab monitoring
 * 5. Handles tab reload / track termination gracefully
 * 6. Dispatches forensic scan results to background service worker
 */

import { CAPTURE_DURATION_MS, MESSAGE_TYPES, POPUP_STATES } from '../shared/constants.js';
import { uploadClipForAnalysis } from '../shared/api.js';

let currentMediaStream = null;
let currentMediaRecorder = null;
let currentAudioContext = null;
let currentAudioSource = null;
let recordingChunks = [];
let recordingTimer = null;
let tickInterval = null;

let isSingleScanActive = false;
let isMonitoringActive = false;
let currentTabMeta = { tabId: null, tabTitle: '', tabUrl: '' };

// Listen for messages from service worker
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) return;

  if (message.type === MESSAGE_TYPES.START_RECORDING) {
    handleStartSingleScan(message.payload);
    sendResponse({ received: true });
    return true;
  }

  if (message.type === MESSAGE_TYPES.START_MONITORING) {
    handleStartMonitoring(message.payload);
    sendResponse({ received: true });
    return true;
  }

  if (message.type === MESSAGE_TYPES.STOP_MONITORING || message.type === MESSAGE_TYPES.CANCEL_SCAN) {
    handleStopCapture();
    sendResponse({ stopped: true });
    return true;
  }
});

/**
 * Initiates a one-off 8-second manual tab scan.
 */
async function handleStartSingleScan({ streamId, tabId, tabTitle, tabUrl }) {
  cleanupResources();
  isSingleScanActive = true;
  isMonitoringActive = false;
  currentTabMeta = { tabId, tabTitle, tabUrl };

  try {
    currentMediaStream = await acquireMediaStream(streamId);
    preserveTabAudio(currentMediaStream);

    const hasVideo = currentMediaStream.getVideoTracks().length > 0;
    const hasAudio = currentMediaStream.getAudioTracks().length > 0;
    const mimeType = selectSupportedMimeType(hasVideo, hasAudio);
    startSingleRecorder(mimeType, hasVideo);
  } catch (err) {
    console.error('[Offscreen] Single scan capture failed:', err);
    cleanupResources();
    notifyError(formatErrorMessage(err));
  }
}

/**
 * Initiates continuous monitoring for the active tab.
 */
async function handleStartMonitoring({ streamId, tabId, tabTitle, tabUrl }) {
  cleanupResources();
  isMonitoringActive = true;
  isSingleScanActive = false;
  currentTabMeta = { tabId, tabTitle, tabUrl };

  try {
    currentMediaStream = await acquireMediaStream(streamId);
    preserveTabAudio(currentMediaStream);

    // Listen for tab reload / track termination
    if (currentMediaStream.getVideoTracks().length > 0) {
      currentMediaStream.getVideoTracks()[0].onended = () => {
        console.info('[Offscreen] Monitored tab track ended (page reloaded or navigated).');
        chrome.runtime.sendMessage({
          type: 'TAB_TRACK_ENDED',
          payload: { tabId: currentTabMeta.tabId },
        });
      };
    }

    const hasVideo = currentMediaStream.getVideoTracks().length > 0;
    const hasAudio = currentMediaStream.getAudioTracks().length > 0;
    const mimeType = selectSupportedMimeType(hasVideo, hasAudio);
    startContinuousMonitoringLoop(mimeType, hasVideo);
  } catch (err) {
    console.error('[Offscreen] Continuous monitoring failed:', err);
    cleanupResources();
    chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.SCAN_ERROR,
      payload: { error: formatErrorMessage(err) },
    });
  }
}

/**
 * Acquires tab stream with audio + video, falling back to video-only or audio-only if needed.
 */
async function acquireMediaStream(streamId) {
  if (!streamId) {
    throw new Error('Capture stream ID is missing or invalid.');
  }

  // 1. Attempt full combined Audio + Video capture
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId,
        },
      },
      video: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId,
          maxFrameRate: 30,
        },
      },
    });
    console.info('[Offscreen] Successfully acquired tab Audio + Video stream.');
    return stream;
  } catch (audioVideoErr) {
    console.warn('[Offscreen] Combined video+audio capture failed, trying video only:', audioVideoErr);
  }

  // 2. Fallback: Video only
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId,
          maxFrameRate: 30,
        },
      },
    });
    console.info('[Offscreen] Successfully acquired tab Video-only stream.');
    return stream;
  } catch (videoErr) {
    console.warn('[Offscreen] Video-only capture failed, trying audio only:', videoErr);
  }

  // 3. Fallback: Audio only
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId,
        },
      },
    });
    console.info('[Offscreen] Successfully acquired tab Audio-only stream.');
    return stream;
  } catch (audioErr) {
    console.error('[Offscreen] All tab capture modes failed:', audioErr);
    throw new Error('Unable to capture tab media stream. Please ensure video or audio is playing on the tab.');
  }
}

/**
 * Loops tab audio through AudioContext to destination so audio remains audible.
 */
function preserveTabAudio(stream) {
  try {
    const audioTracks = stream.getAudioTracks();
    if (audioTracks && audioTracks.length > 0) {
      currentAudioContext = new AudioContext();
      currentAudioSource = currentAudioContext.createMediaStreamSource(stream);
      currentAudioSource.connect(currentAudioContext.destination);
      console.info('[Offscreen] Tab audio successfully routed to AudioContext destination.');
    }
  } catch (err) {
    console.warn('[Offscreen] AudioContext route error:', err);
  }
}

/**
 * Detects supported WebM MIME type based on available tracks.
 */
function selectSupportedMimeType(hasVideo = true, hasAudio = true) {
  if (hasVideo) {
    const videoCandidates = [
      'video/webm;codecs=vp8,opus',
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp8',
      'video/webm',
    ];

    for (const candidate of videoCandidates) {
      if (MediaRecorder.isTypeSupported(candidate)) {
        return candidate;
      }
    }
    return 'video/webm';
  } else {
    const audioCandidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
    ];
    for (const candidate of audioCandidates) {
      if (MediaRecorder.isTypeSupported(candidate)) {
        return candidate;
      }
    }
    return 'audio/webm';
  }
}

/**
 * Sets up and runs a single scan.
 */
function startSingleRecorder(mimeType, hasVideo = true) {
  recordingChunks = [];
  const options = { mimeType, audioBitsPerSecond: 128000 };
  if (hasVideo) {
    options.videoBitsPerSecond = 2500000;
  }

  currentMediaRecorder = new MediaRecorder(currentMediaStream, options);

  currentMediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      recordingChunks.push(event.data);
    }
  };

  notifyState(POPUP_STATES.CAPTURING, {
    secondsRemaining: Math.ceil(CAPTURE_DURATION_MS / 1000),
    tabTitle: currentTabMeta.tabTitle,
    tabUrl: currentTabMeta.tabUrl,
  });

  currentMediaRecorder.start(1000);

  const startTime = Date.now();
  const endTime = startTime + CAPTURE_DURATION_MS;

  tickInterval = setInterval(() => {
    const remainingMs = Math.max(0, endTime - Date.now());
    const secondsRemaining = Math.ceil(remainingMs / 1000);
    notifyProgress(secondsRemaining);
    if (remainingMs <= 0) {
      clearInterval(tickInterval);
      tickInterval = null;
    }
  }, 1000);

  recordingTimer = setTimeout(async () => {
    await finishSingleScan({ mimeType });
  }, CAPTURE_DURATION_MS);
}

async function finishSingleScan({ mimeType }) {
  if (recordingTimer) clearTimeout(recordingTimer);
  if (tickInterval) clearInterval(tickInterval);

  if (!currentMediaRecorder || currentMediaRecorder.state === 'inactive') return;

  const stopped = new Promise((resolve) => {
    currentMediaRecorder.onstop = resolve;
  });
  currentMediaRecorder.stop();
  await stopped;

  const recordedBlob = new Blob(recordingChunks, { type: mimeType });
  cleanupResources();

  if (recordedBlob.size === 0) {
    notifyError('Captured recording is empty. Please verify media is actively playing on the tab.');
    return;
  }

  notifyState(POPUP_STATES.UPLOADING, {
    message: 'Uploading clip to Authentica...',
    tabTitle: currentTabMeta.tabTitle,
    tabUrl: currentTabMeta.tabUrl,
  });

  try {
    setTimeout(() => {
      notifyState(POPUP_STATES.ANALYZING, {
        message: 'Analyzing media forensics...',
        tabTitle: currentTabMeta.tabTitle,
        tabUrl: currentTabMeta.tabUrl,
      });
    }, 600);

    const filename = `single_scan_${Date.now()}.webm`;
    const { summary, raw } = await uploadClipForAnalysis(recordedBlob, filename, currentTabMeta);

    chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.SCAN_COMPLETE,
      payload: { summary, raw },
    });
  } catch (err) {
    notifyError(err.message || 'Analysis failed. Please check server status.');
  } finally {
    isSingleScanActive = false;
  }
}

/**
 * Continuous monitoring loop: records consecutive chunks and streams to backend.
 */
function startContinuousMonitoringLoop(mimeType, hasVideo = true) {
  if (!isMonitoringActive || !currentMediaStream) return;

  recordingChunks = [];
  try {
    const options = { mimeType, audioBitsPerSecond: 128000 };
    if (hasVideo) {
      options.videoBitsPerSecond = 2000000;
    }
    currentMediaRecorder = new MediaRecorder(currentMediaStream, options);
  } catch (e) {
    console.error('[Offscreen] Failed to create MediaRecorder:', e);
    return;
  }

  currentMediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      recordingChunks.push(event.data);
    }
  };

  currentMediaRecorder.start(1000);
  console.info('[Offscreen] Continuous monitoring chunk started...');

  recordingTimer = setTimeout(async () => {
    if (!isMonitoringActive) return;

    if (currentMediaRecorder && currentMediaRecorder.state !== 'inactive') {
      const stopped = new Promise((resolve) => {
        currentMediaRecorder.onstop = resolve;
      });
      currentMediaRecorder.stop();
      await stopped;
    }

    const chunkBlob = new Blob(recordingChunks, { type: mimeType });
    recordingChunks = [];

    // Process completed chunk and AWAIT backend response BEFORE starting next 10-second capture.
    // This strictly prevents backend overload by ensuring only 1 analysis is in-flight at a time.
    if (chunkBlob.size > 0) {
      console.info('[Offscreen] 10s chunk recorded. Uploading to backend and awaiting response...');
      try {
        await processMonitoringChunk(chunkBlob);
      } catch (err) {
        console.warn('[Offscreen] Chunk processing error:', err);
      }
    }

    // ONLY after the backend forensic result arrives, start recording the next 10-second chunk!
    if (isMonitoringActive && currentMediaStream && currentMediaStream.active) {
      console.info('[Offscreen] Backend result received. Starting next 10s capture cycle...');
      startContinuousMonitoringLoop(mimeType, hasVideo);
    }
  }, CAPTURE_DURATION_MS);
}

/**
 * Uploads a monitoring chunk and sends the verdict to the service worker.
 */
async function processMonitoringChunk(chunkBlob) {
  try {
    const filename = `monitor_chunk_${Date.now()}.webm`;
    const { summary, raw } = await uploadClipForAnalysis(chunkBlob, filename, currentTabMeta);

    chrome.runtime.sendMessage({
      type: 'MONITORING_CHUNK_RESULT',
      payload: { summary, raw },
    });
  } catch (err) {
    console.warn('[Offscreen] Monitoring chunk analysis error:', err);
    // Silent fail in monitoring mode so transient network blips don't crash the loop
  }
}

/**
 * Cleanly cancels all recording and streams.
 */
function handleStopCapture() {
  isMonitoringActive = false;
  isSingleScanActive = false;
  cleanupResources();
}

function cleanupResources() {
  if (recordingTimer) {
    clearTimeout(recordingTimer);
    recordingTimer = null;
  }
  if (tickInterval) {
    clearInterval(tickInterval);
    tickInterval = null;
  }

  if (currentMediaRecorder && currentMediaRecorder.state !== 'inactive') {
    try { currentMediaRecorder.stop(); } catch {}
  }
  currentMediaRecorder = null;
  recordingChunks = [];

  try {
    if (currentAudioSource) {
      currentAudioSource.disconnect();
      currentAudioSource = null;
    }
    if (currentAudioContext && currentAudioContext.state !== 'closed') {
      currentAudioContext.close();
      currentAudioContext = null;
    }
  } catch {}

  try {
    if (currentMediaStream) {
      currentMediaStream.getTracks().forEach((track) => track.stop());
      currentMediaStream = null;
    }
  } catch {}
}

function notifyState(state, extra = {}) {
  chrome.runtime.sendMessage({
    type: MESSAGE_TYPES.STATUS_UPDATE,
    payload: { state, ...extra },
  });
}

function notifyProgress(secondsRemaining) {
  chrome.runtime.sendMessage({
    type: MESSAGE_TYPES.RECORDING_TICK,
    payload: { secondsRemaining },
  });
}

function notifyError(errorMessage) {
  chrome.runtime.sendMessage({
    type: MESSAGE_TYPES.SCAN_ERROR,
    payload: { error: errorMessage },
  });
}

function formatErrorMessage(err) {
  const msg = err?.message || String(err);
  if (msg.includes('Permission denied') || msg.includes('NotAllowedError')) {
    return 'Tab capture permission was denied by Chrome or user.';
  }
  if (msg.includes('NotReadableError') || msg.includes('TrackStartError')) {
    return 'This type of protected content or DRM media cannot be captured.';
  }
  return msg || 'Authenitca could not capture this tab.';
}
