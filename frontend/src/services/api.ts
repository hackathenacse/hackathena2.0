import { AnalysisResponse, HistoryItem } from '../types/analysis';

const rawBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
const API_BASE = rawBase ? (rawBase.endsWith('/api') ? rawBase : `${rawBase}/api`) : '/api';
const STORAGE_KEY = 'authentica_analysis_history';

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export async function checkHealth(): Promise<{ status: string; ffmpeg_available: boolean; ffprobe_available: boolean; version: string }> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Health check failed');
    return await res.json();
  } catch (err) {
    return { status: 'offline', ffmpeg_available: false, ffprobe_available: false, version: '2.0.0' };
  }
}

export async function analyzeVideo(file: File): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/analyses`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = 'Analysis request failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // fallback
    }
    throw new ApiError(response.status, errorDetail);
  }

  const data: AnalysisResponse = await response.json();

  // Save to local history
  saveToHistory(data);

  return data;
}

export function saveToHistory(analysis: AnalysisResponse): void {
  try {
    const history = getHistory();
    const isAudio = analysis.input?.media_type === 'AUDIO' || !analysis.video;
    const filename = analysis.video?.filename || analysis.audio_metadata?.filename || 'Uploaded Audio';
    const duration_s = analysis.video?.duration_s ?? analysis.audio_metadata?.duration_s ?? 0;
    const sha256 = analysis.video?.sha256 || analysis.audio_metadata?.sha256 || 'N/A';

    const item: HistoryItem = {
      id: analysis.id,
      created_at: analysis.created_at,
      filename,
      media_type: isAudio ? 'AUDIO' : 'VIDEO',
      duration_s,
      sha256,
      media_verdict: analysis.assessment?.media || 'UNCERTAIN',
      fraud_level: analysis.assessment?.fraud || analysis.fraud?.level || 'LOW',
      action: analysis.assessment?.action || 'VERIFY',
      analysis,
    };

    // Prepend and keep latest 30 analyses
    const updated = [item, ...history.filter(h => h.id !== item.id)].slice(0, 30);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (e) {
    console.error('Failed to save to local history:', e);
  }
}

export function getHistory(): HistoryItem[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

export function getAnalysisById(id: string): AnalysisResponse | null {
  const history = getHistory();
  const found = history.find(h => h.id === id);
  return found ? found.analysis : null;
}

export async function fetchAnalysisById(id: string): Promise<AnalysisResponse | null> {
  // First attempt via configured API base
  try {
    const res = await fetch(`${API_BASE}/analyses/${id}`);
    if (res.ok) {
      const data: AnalysisResponse = await res.json();
      saveToHistory(data);
      return data;
    }
  } catch (e) {
    console.warn(`API fetch for analysis ${id} failed:`, e);
  }

  // Fallback direct backend call to port 8000 if not using custom base URL
  if (!import.meta.env.VITE_API_BASE_URL) {
    try {
      const directRes = await fetch(`http://localhost:8000/api/analyses/${id}`);
      if (directRes.ok) {
        const data: AnalysisResponse = await directRes.json();
        saveToHistory(data);
        return data;
      }
    } catch (e) {
      console.warn(`Direct backend fetch for analysis ${id} failed:`, e);
    }
  }

  return null;
}

export async function fetchAnalysisHistory(search?: string): Promise<{ items: HistoryItem[]; mongodb_connected: boolean }> {
  try {
    const url = search ? `${API_BASE}/analyses?search=${encodeURIComponent(search)}` : `${API_BASE}/analyses`;
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      const serverItems: HistoryItem[] = (data.items || []).map((analysis: AnalysisResponse) => {
        const isAudio = analysis.input?.media_type === 'AUDIO' || !analysis.video;
        const filename = analysis.video?.filename || analysis.audio_metadata?.filename || 'Media';
        const duration_s = analysis.video?.duration_s ?? analysis.audio_metadata?.duration_s ?? 0;
        const sha256 = analysis.video?.sha256 || analysis.audio_metadata?.sha256 || 'N/A';
        return {
          id: analysis.id,
          created_at: analysis.created_at,
          filename,
          media_type: isAudio ? 'AUDIO' : 'VIDEO',
          duration_s,
          sha256,
          media_verdict: analysis.assessment?.media || 'UNCERTAIN',
          fraud_level: analysis.assessment?.fraud || analysis.fraud?.level || 'LOW',
          action: analysis.assessment?.action || 'VERIFY',
          analysis,
        };
      });
      return { items: serverItems, mongodb_connected: Boolean(data.mongodb_connected) };
    }
  } catch (e) {
    console.warn('Failed to fetch history from server:', e);
  }

  // Fallback local storage
  return { items: getHistory(), mongodb_connected: false };
}

export interface FeedbackData {
  ground_truth_media: 'REAL' | 'FAKE' | 'UNVERIFIED';
  ground_truth_fraud: 'HARMLESS' | 'SCAM' | 'UNVERIFIED';
  is_false_positive?: boolean;
  is_false_negative?: boolean;
  notes?: string;
}

export async function submitAnalysisFeedback(analysisId: string, feedback: FeedbackData): Promise<{ ok: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/analyses/${analysisId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(feedback),
  });

  if (!res.ok) {
    throw new Error('Failed to record human verification feedback');
  }

  return await res.json();
}

export function clearHistory(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    console.error('Failed to clear history:', e);
  }
}
