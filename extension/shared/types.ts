/**
 * Authentica Extension — Shared TypeScript Interfaces & Types
 */

export type PopupState = 'IDLE' | 'CAPTURING' | 'UPLOADING' | 'ANALYZING' | 'COMPLETED' | 'ERROR';

export type MediaVerdict = 'LIKELY_MANIPULATED' | 'SUSPICIOUS' | 'NO_STRONG_EVIDENCE' | 'UNCERTAIN';

export type FraudLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'NOT_ASSESSABLE';

export type ActionDirective = 'STOP_AND_VERIFY' | 'VERIFY' | 'CAUTION' | 'NO_ACTION_FLAGGED';

export interface AnalysisSummary {
  id: string;
  status: string;
  action: ActionDirective;
  mediaVerdict: MediaVerdict;
  fraudLevel: FraudLevel;
  requestedAction?: string;
  explanations: string[];
  fullReportUrl: string;
  timestamp: number;
  capturedTabTitle?: string;
  capturedTabUrl?: string;
}

export interface ScanState {
  state: PopupState;
  tabId?: number;
  tabTitle?: string;
  tabUrl?: string;
  secondsRemaining?: number;
  message?: string;
  errorDetail?: string;
  summary?: AnalysisSummary | null;
}

export interface ExtensionMessage {
  type: string;
  payload?: any;
}
