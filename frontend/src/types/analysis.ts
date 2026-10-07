export interface VideoInfo {
  filename: string;
  sha256: string;
  duration_s: number;
  fps: number;
  width: number;
  height: number;
  frames_sampled: number;
  audio_available: boolean;
}

export interface VisualFrameResult {
  timestamp_s: number;
  face_detected: boolean | null;
  real_score: number | null;
  fake_score: number | null;
}

export interface VisualResult {
  available: boolean;
  model: string | null;
  status: string;
  frames_analyzed: number;
  faces_found: number;
  face_detection_rate: number | null;
  results: VisualFrameResult[];
}

export interface AudioWindowResult {
  start_s: number;
  end_s: number;
  spoof_score: number | null;
}

export interface AudioResult {
  available: boolean;
  model: string | null;
  status: string;
  windows_analyzed: number | null;
  processing_time_s: number | null;
  results: AudioWindowResult[];
}

export interface SpeechSegment {
  start_s: number;
  end_s: number;
  text: string;
}

export interface SpeechResult {
  available: boolean;
  model: string | null;
  status: string;
  language: string | null;
  processing_time_s: number | null;
  segments: SpeechSegment[];
}

export interface ReliabilityResult {
  level: 'OK' | 'LOW';
  reasons: string[];
}

export interface ModelEvidenceItem {
  name: string;
  score: number;
}

export interface EvidenceModalityResult {
  level: 'HIGH' | 'MEDIUM' | 'LOW' | 'N/A';
  models: ModelEvidenceItem[];
}

export interface ProvenanceResult {
  state: 'FOUND' | 'NONE_FOUND' | 'UNAVAILABLE' | 'ERROR';
  valid: boolean | null;
  trusted: boolean | null;
  signer: string | null;
  note: string;
}

export interface InputInfo {
  media_type: 'VIDEO' | 'AUDIO';
}

export interface AudioMetadata {
  filename: string;
  sha256: string;
  duration_s: number;
  sample_rate_hz?: number | null;
  channels?: number | null;
  codec?: string | null;
  bitrate_kbps?: number | null;
  mime_type?: string | null;
}

export interface EvidenceMetadata {
  media_type?: 'VIDEO' | 'AUDIO';
  width?: number | null;
  height?: number | null;
  duration_s: number;
  fps?: number | null;
  frames_sampled?: number | null;
  audio_available: boolean;
}

export interface EvidenceMatrix {
  visual: EvidenceModalityResult;
  audio: EvidenceModalityResult;
  provenance: ProvenanceResult;
  metadata: EvidenceMetadata;
  reliability: ReliabilityResult;
}

export interface TimelineEvent {
  start_s: number;
  end_s: number;
  kind: 'visual' | 'audio' | 'speech' | 'fraud';
  level: 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  evidence_source: string;
  score: number | null;
}

export interface MediaAssessment {
  media: 'LIKELY_MANIPULATED' | 'SUSPICIOUS' | 'NO_STRONG_EVIDENCE' | 'UNCERTAIN';
  fraud?: 'HIGH' | 'MEDIUM' | 'LOW' | 'NOT_ASSESSABLE' | null;
  action?: 'STOP_AND_VERIFY' | 'VERIFY' | 'CAUTION' | 'NO_ACTION_FLAGGED' | null;
}

export interface FraudEvidenceItem {
  phrase: string;
  start_s: number;
  end_s: number;
}

export interface FraudCategoryEvidence {
  category: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  evidence: FraudEvidenceItem[];
}

export interface FraudRequestedAction {
  action: string;
  phrase: string;
  start_s: number;
  end_s: number;
}

export interface FraudResult {
  level: 'HIGH' | 'MEDIUM' | 'LOW' | 'NOT_ASSESSABLE';
  categories: FraudCategoryEvidence[];
  requested_actions: FraudRequestedAction[];
  news_context_downgrade: boolean;
}

export interface AnalysisResponse {
  id: string;
  status: 'completed' | 'partial' | 'error';
  created_at: string;
  input?: InputInfo;
  video?: VideoInfo | null;
  audio_metadata?: AudioMetadata | null;
  visual: VisualResult;
  audio: AudioResult;
  speech: SpeechResult;
  reliability: ReliabilityResult | null;
  evidence: EvidenceMatrix | null;
  timeline: TimelineEvent[];
  assessment: MediaAssessment | null;
  explanation: string[];
  limitations: string[];
  fraud: FraudResult | null;
  cached?: boolean;
  reanalysis_speedup_ms?: number;
}

export interface HistoryItem {
  id: string;
  created_at: string;
  filename: string;
  media_type: 'VIDEO' | 'AUDIO';
  duration_s: number;
  sha256: string;
  media_verdict: string;
  fraud_level: string;
  action: string;
  analysis: AnalysisResponse;
}
