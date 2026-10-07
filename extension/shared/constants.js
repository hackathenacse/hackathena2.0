/**
 * Authentica Extension — Shared Constants & Configuration Defaults
 */

export const DEFAULT_API_URL = 'https://anatomy-enemies-acoustic-grade.trycloudflare.com';
export const DEFAULT_WEB_APP_URL = 'https://authenticax-two.vercel.app';

// Fixed capture duration (10.0 seconds per cycle for balanced analysis and server throughput)
export const CAPTURE_DURATION_MS = 10000;

export const OFFSCREEN_DOCUMENT_PATH = 'offscreen/offscreen.html';

// Storage keys
export const STORAGE_KEYS = {
  API_URL: 'authentica_api_url',
  WEB_APP_URL: 'authentica_web_app_url',
  CURRENT_SCAN: 'authentica_current_scan',
  LAST_RESULT: 'authentica_last_result',
  MONITORING_STATE: 'authentica_monitoring_state',
  ACTIVE_THREAT: 'authentica_active_threat',
};

// Monitoring states
export const MONITORING_STATES = {
  OFF: 'OFF',
  MONITORING_SAFE: 'MONITORING_SAFE',
  MONITORING_CHECKING: 'MONITORING_CHECKING',
  THREAT_ALERT: 'THREAT_ALERT',
};

// Popup state machine
export const POPUP_STATES = {
  IDLE: 'IDLE',
  CAPTURING: 'CAPTURING',
  UPLOADING: 'UPLOADING',
  ANALYZING: 'ANALYZING',
  COMPLETED: 'COMPLETED',
  ERROR: 'ERROR',
};

// Backend action recommendations
export const ACTION_DIRECTIVES = {
  STOP_AND_VERIFY: 'STOP_AND_VERIFY',
  VERIFY: 'VERIFY',
  CAUTION: 'CAUTION',
  NO_ACTION_FLAGGED: 'NO_ACTION_FLAGGED',
};

// Internal message types
export const MESSAGE_TYPES = {
  START_SCAN: 'START_SCAN',
  CANCEL_SCAN: 'CANCEL_SCAN',
  START_RECORDING: 'START_RECORDING',
  RECORDING_STARTED: 'RECORDING_STARTED',
  RECORDING_TICK: 'RECORDING_TICK',
  RECORDING_COMPLETE: 'RECORDING_COMPLETE',
  STATUS_UPDATE: 'STATUS_UPDATE',
  SCAN_COMPLETE: 'SCAN_COMPLETE',
  SCAN_ERROR: 'SCAN_ERROR',
  GET_STATE: 'GET_STATE',
  RESET_STATE: 'RESET_STATE',
  // Live tab monitoring messages
  START_MONITORING: 'START_MONITORING',
  STOP_MONITORING: 'STOP_MONITORING',
  THREAT_DETECTED: 'THREAT_DETECTED',
  DISMISS_THREAT: 'DISMISS_THREAT',
};

