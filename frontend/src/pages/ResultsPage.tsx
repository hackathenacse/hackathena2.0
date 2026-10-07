import React, { useState, useEffect } from 'react';
import { useParams, useLocation, Link } from 'react-router-dom';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  Download, 
  Copy, 
  Check, 
  FileVideo, 
  Clock, 
  Layers, 
  Mic, 
  Eye, 
  FileCheck2, 
  ArrowLeft,
  Flame,
  ShieldQuestion,
  Music,
  Lock,
  Database,
  ThumbsUp,
  ThumbsDown,
  Sparkles
} from 'lucide-react';
import { AnalysisResponse, TimelineEvent } from '../types/analysis';
import { getAnalysisById, fetchAnalysisById, submitAnalysisFeedback } from '../services/api';

export const ResultsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();

  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(() => {
    if (location.state && location.state.analysis) {
      return location.state.analysis;
    }
    if (id) {
      return getAnalysisById(id);
    }
    return null;
  });

  const [isLoading, setIsLoading] = useState<boolean>(() => {
    if (location.state && location.state.analysis) return false;
    if (id && getAnalysisById(id)) return false;
    return !!id;
  });
  const [loadError, setLoadError] = useState<string | null>(null);
  const [copiedHash, setCopiedHash] = useState<boolean>(false);
  const [selectedTimelineEvent, setSelectedTimelineEvent] = useState<TimelineEvent | null>(null);

  // Active Learning Human-in-the-loop state
  const [fbMedia, setFbMedia] = useState<'REAL' | 'FAKE' | null>(null);
  const [fbFraud, setFbFraud] = useState<'HARMLESS' | 'SCAM' | null>(null);
  const [fbNotes, setFbNotes] = useState<string>('');
  const [fbSubmitting, setFbSubmitting] = useState<boolean>(false);
  const [fbSuccess, setFbSuccess] = useState<string | null>(null);
  const [fbTrainingData, setFbTrainingData] = useState<any>(null);
  const [fbError, setFbError] = useState<string | null>(null);

  const handleSendFeedback = async () => {
    if (!analysis || !fbMedia || !fbFraud) return;
    try {
      setFbSubmitting(true);
      setFbError(null);
      const res: any = await submitAnalysisFeedback(analysis.id, {
        ground_truth_media: fbMedia,
        ground_truth_fraud: fbFraud,
        is_false_positive: fbMedia === 'REAL' && (analysis.assessment?.media === 'LIKELY_MANIPULATED' || analysis.assessment?.media === 'SUSPICIOUS'),
        is_false_negative: fbMedia === 'FAKE' && analysis.assessment?.media === 'NO_STRONG_EVIDENCE',
        notes: fbNotes,
      });
      if (res.ok) {
        setFbSuccess(res.message || 'Ground-truth feedback recorded and model adapter trained!');
        if (res.training) {
          setFbTrainingData(res.training);
        }
      } else {
        setFbError(res.message || 'Verification stored, but model adaptation FAILED.');
      }
    } catch (err: any) {
      setFbError(err.message || 'Failed to submit verification feedback');
    } finally {
      setFbSubmitting(false);
    }
  };

  useEffect(() => {
    if (!analysis && id) {
      const stored = getAnalysisById(id);
      if (stored) {
        setAnalysis(stored);
        setIsLoading(false);
      } else {
        setIsLoading(true);
        setLoadError(null);
        fetchAnalysisById(id)
          .then(fetched => {
            if (fetched) {
              setAnalysis(fetched);
            } else {
              setLoadError("The forensic analysis report was not found on the server or in local session cache.");
            }
          })
          .catch(err => {
            setLoadError(err?.message || "Failed to load forensic analysis.");
          })
          .finally(() => {
            setIsLoading(false);
          });
      }
    } else {
      setIsLoading(false);
    }
  }, [id, analysis]);

  if (isLoading) {
    return (
      <div className="min-h-[calc(100vh-160px)] flex flex-col items-center justify-center p-6 text-center max-w-[1200px] mx-auto">
        <div className="editorial-card-lg p-12 max-w-md w-full text-center space-y-4 bg-paper">
          <div className="w-12 h-12 mx-auto rounded-full bg-carbon text-paper flex items-center justify-center font-mono font-bold animate-pulse">
            ●
          </div>
          <h2 className="font-display text-3xl font-black uppercase tracking-tight text-carbon">
            RETRIEVING FORENSIC DATA
          </h2>
          <p className="text-xs font-mono text-slate">
            Querying local analysis session report...
          </p>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="min-h-[calc(100vh-160px)] flex flex-col items-center justify-center p-6 text-center max-w-[1200px] mx-auto">
        <div className="editorial-card-lg p-10 max-w-md w-full text-center space-y-4 bg-paper">
          <div className="w-12 h-12 mx-auto rounded-full bg-mist border border-ash flex items-center justify-center text-carbon">
            <ShieldQuestion className="w-6 h-6" />
          </div>
          <h2 className="font-display text-3xl font-black uppercase tracking-tight text-carbon">
            ANALYSIS NOT FOUND
          </h2>
          <p className="text-xs font-mono text-slate">
            {loadError || "The requested analysis session ID is not in local memory or was cleared."}
          </p>
          <div className="flex items-center justify-center gap-3 pt-4">
            <Link
              to="/"
              className="editorial-btn-primary inline-flex items-center space-x-2 font-mono text-xs uppercase"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Upload New Media</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const { video, audio_metadata, visual, audio, speech, reliability, evidence, timeline, assessment, explanation, limitations, fraud } = analysis;

  const isAudio = analysis.input?.media_type === 'AUDIO' || !video;
  const filename = video?.filename || audio_metadata?.filename || 'Uploaded Media';
  const sha256 = video?.sha256 || audio_metadata?.sha256 || 'N/A';
  const totalDuration = video?.duration_s || audio_metadata?.duration_s || 1.0;

  const mediaVerdict = assessment?.media || 'UNCERTAIN';
  const fraudLevel = assessment?.fraud || fraud?.level || 'NOT_ASSESSABLE';
  const finalAction = assessment?.action || 'VERIFY';

  const copySha256 = () => {
    navigator.clipboard.writeText(sha256);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const exportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(analysis, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `authentica_report_${filename}_${analysis.id.slice(0, 8)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const getMediaVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case 'LIKELY_MANIPULATED':
        return {
          label: 'LIKELY MANIPULATED',
          indicator: 'bg-rose-600',
          desc: 'High-confidence synthetic generation artifacts detected across visual and/or acoustic modalities.',
        };
      case 'SUSPICIOUS':
        return {
          label: 'SUSPICIOUS',
          indicator: 'bg-voltage',
          desc: 'Moderate artifacts or single-modality anomalies observed.',
        };
      case 'NO_STRONG_EVIDENCE':
        return {
          label: 'NO STRONG EVIDENCE',
          indicator: 'bg-mint',
          desc: 'No conclusive manipulation artifacts identified within tested detector boundaries.',
        };
      case 'UNCERTAIN':
      default:
        return {
          label: 'UNCERTAIN',
          indicator: 'bg-smoke',
          desc: 'Media quality or detector coverage was degraded, preventing reliable classification.',
        };
    }
  };

  const getFraudRiskBadge = (level: string) => {
    switch (level) {
      case 'HIGH':
        return {
          label: 'HIGH FRAUD RISK',
          indicator: 'bg-rose-600',
          desc: 'Direct extraction directives (OTP, wire transfer, remote software) detected with social engineering pressure.',
        };
      case 'MEDIUM':
        return {
          label: 'MEDIUM FRAUD RISK',
          indicator: 'bg-voltage',
          desc: 'Suspicious payment/authority references without direct extraction directives, or scam reporting context.',
        };
      case 'LOW':
        return {
          label: 'LOW FRAUD RISK',
          indicator: 'bg-mint',
          desc: 'Benign dialogue without social-engineering extortion indicators.',
        };
      case 'NOT_ASSESSABLE':
      default:
        return {
          label: 'NOT ASSESSABLE',
          indicator: 'bg-smoke',
          desc: 'No spoken speech segments were present to analyze.',
        };
    }
  };

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'STOP_AND_VERIFY':
        return {
          title: 'STOP AND VERIFY',
          indicator: 'bg-rose-600',
          subtitle: 'High-risk social engineering or direct credential/financial extraction detected.',
          callout: 'Do NOT transfer money, share OTPs, or install software until independently verified out-of-band.',
        };
      case 'VERIFY':
        return {
          title: 'VERIFY INDEPENDENTLY',
          indicator: 'bg-voltage',
          subtitle: 'Moderate risks, degraded evidence quality, or suspicious indicators detected.',
          callout: 'Perform secondary confirmation before trusting the content or acting on instructions.',
        };
      case 'CAUTION':
        return {
          title: 'EXERCISE CAUTION',
          indicator: 'bg-mint',
          subtitle: 'Media shows signs of AI manipulation or synthesis (e.g. creative or artistic deepfakes).',
          callout: 'Synthetic media detected. Ensure attribution and authenticity before sharing.',
        };
      case 'NO_ACTION_FLAGGED':
      default:
        return {
          title: 'NO ACTION FLAGGED',
          indicator: 'bg-mint',
          subtitle: 'No high-risk manipulation or fraud indicators identified.',
          callout: 'Standard security practices apply. Content shows no immediate red flags.',
        };
    }
  };

  const mediaBadge = getMediaVerdictBadge(mediaVerdict);
  const fraudBadge = getFraudRiskBadge(fraudLevel);
  const actionBadge = getActionBadge(finalAction);

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 space-y-8 sm:space-y-10">
      
      {/* 1. Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-ash/80">
        <div className="space-y-2">
          <div className="flex items-center space-x-3">
            <Link
              to="/"
              className="p-2 rounded-lg bg-paper border border-ash hover:border-carbon text-carbon transition-colors"
              title="Back to Upload"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <h1 className="font-display text-4xl sm:text-5xl font-black uppercase tracking-tight text-carbon">
              FORENSIC ANALYSIS REPORT
            </h1>
          </div>
          
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate">
            <span className="flex items-center space-x-1.5 font-bold text-carbon">
              {isAudio ? <Music className="w-3.5 h-3.5" /> : <FileVideo className="w-3.5 h-3.5" />}
              <span>{filename}</span>
            </span>
            <span>·</span>
            <span className="px-2 py-0.5 rounded-pill bg-mint text-carbon font-bold text-[10px] border border-carbon/20">
              {isAudio ? 'AUDIO' : 'VIDEO'}
            </span>
            <span>·</span>
            {isAudio ? (
              <span>{totalDuration.toFixed(1)}s ({audio_metadata?.codec || 'PCM'} · {audio_metadata?.sample_rate_hz || 16000}Hz)</span>
            ) : (
              <span>{video ? `${video.duration_s.toFixed(1)}s (${video.width}×${video.height} @ ${video.fps.toFixed(0)}fps)` : `${totalDuration.toFixed(1)}s`}</span>
            )}
            <span>·</span>
            <span className="text-smoke">ID: {analysis.id.slice(0, 8)}</span>
            {analysis.cached && (
              <>
                <span>·</span>
                <span className="px-2 py-0.5 rounded-pill bg-voltage text-carbon font-bold text-[10px] border border-carbon flex items-center gap-1 shadow-sm">
                  ⚡ FAST RE-ANALYSIS ({analysis.reanalysis_speedup_ms ? `${analysis.reanalysis_speedup_ms}ms` : '<50ms'})
                </span>
              </>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center space-x-2.5">
          <button
            type="button"
            onClick={copySha256}
            className="editorial-btn-secondary flex items-center space-x-2 font-mono text-xs uppercase"
            title="Copy SHA-256 Fingerprint"
          >
            {copiedHash ? <Check className="w-3.5 h-3.5 text-carbon" /> : <Copy className="w-3.5 h-3.5 text-slate" />}
            <span>SHA-256: {sha256.slice(0, 8)}...</span>
          </button>

          <button
            type="button"
            onClick={exportJson}
            className="editorial-btn-primary flex items-center space-x-2 font-mono text-xs uppercase"
          >
            <Download className="w-3.5 h-3.5" />
            <span>EXPORT JSON</span>
          </button>
        </div>
      </div>

      {/* 2. Asymmetric Primary Verdict Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        {/* Left Large Inverted Black Card: Media Risk + Action Callout */}
        <div className="lg:col-span-7 editorial-inverted-card p-8 sm:p-10 flex flex-col justify-between space-y-8">
          
          <div className="space-y-4">
            <div className="flex items-center justify-between font-mono text-xs">
              <span className="px-2.5 py-1 rounded-pill bg-graphite text-mint font-bold uppercase tracking-wider">
                ORTHOGONAL DIMENSION 01
              </span>
              <div className="flex items-center space-x-2">
                <span className={`w-2.5 h-2.5 rounded-full ${mediaBadge.indicator}`} />
                <span className="text-smoke uppercase font-bold text-[11px]">Media Synthesis</span>
              </div>
            </div>

            <div>
              <p className="font-mono text-xs uppercase tracking-wider text-smoke">MEDIA MANIPULATION RISK</p>
              <h2 className="font-display text-4xl sm:text-5xl lg:text-6xl font-black uppercase tracking-tight text-paper mt-1">
                {mediaBadge.label}
              </h2>
              <p className="text-xs sm:text-sm text-smoke mt-2 leading-relaxed font-sans max-w-xl">
                {mediaBadge.desc}
              </p>
            </div>
          </div>

          {/* Action Recommendation Banner inside Black Card */}
          <div className="p-6 rounded-[24px] bg-graphite/80 border border-graphite space-y-3">
            <div className="flex items-center space-x-2 font-mono text-xs">
              <span className={`w-2.5 h-2.5 rounded-full ${actionBadge.indicator}`} />
              <span className="font-bold text-mint uppercase tracking-wider">
                SAFETY PROTOCOL: {actionBadge.title}
              </span>
            </div>
            <p className="text-xs sm:text-sm text-paper font-sans leading-relaxed">
              {actionBadge.callout}
            </p>
            <div className="pt-2 flex flex-wrap items-center gap-2 font-mono text-[10px] text-smoke">
              <span>VISUAL: {evidence?.visual.level || 'N/A'}</span>
              <span>·</span>
              <span>AUDIO: {evidence?.audio.level || 'N/A'}</span>
              <span>·</span>
              <span>RELIABILITY: {evidence?.reliability.level || 'OK'}</span>
            </div>
          </div>

        </div>

        {/* Right White Card: Fraud Intent & Directives */}
        <div className="lg:col-span-5 editorial-card-lg p-8 sm:p-10 bg-paper flex flex-col justify-between space-y-6">
          
          <div className="space-y-4">
            <div className="flex items-center justify-between font-mono text-xs">
              <span className="px-2.5 py-1 rounded-pill bg-mist border border-ash text-carbon font-bold uppercase tracking-wider">
                ORTHOGONAL DIMENSION 02
              </span>
              <div className="flex items-center space-x-2">
                <span className={`w-2.5 h-2.5 rounded-full ${fraudBadge.indicator}`} />
                <span className="text-slate uppercase font-bold text-[11px]">Fraud Intent</span>
              </div>
            </div>

            <div>
              <p className="font-mono text-xs uppercase tracking-wider text-slate">FRAUD INTENT LEVEL</p>
              <h2 className="font-display text-4xl sm:text-5xl font-black uppercase tracking-tight text-carbon mt-1">
                {fraudBadge.label}
              </h2>
              <p className="text-xs sm:text-sm text-slate mt-2 leading-relaxed font-sans">
                {fraudBadge.desc}
              </p>
            </div>

            {fraud?.news_context_downgrade && (
              <div className="p-3 rounded-lg bg-mist border border-ash text-[11px] font-mono text-carbon">
                <strong>Scam Reporting Context Detected:</strong> Severity safely downgraded.
              </div>
            )}
          </div>

          {/* Extracted Categories */}
          <div className="space-y-2 pt-4 border-t border-ash/80">
            <p className="font-mono text-[11px] font-bold uppercase text-slate">DETECTED SOCIAL-ENGINEERING TACTICS</p>
            <div className="flex flex-wrap gap-1.5 font-mono text-xs">
              {fraud?.categories && fraud.categories.length > 0 ? (
                fraud.categories.map((cat, i) => (
                  <span key={i} className="editorial-pill-tag bg-mist border border-ash text-carbon">
                    {cat.category} ({cat.evidence.length})
                  </span>
                ))
              ) : (
                <span className="text-xs text-smoke font-mono">No extortion directives detected</span>
              )}
            </div>
          </div>

        </div>

      </div>

      {/* 3. Stage 2 Evidence Matrix */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="font-display text-2xl sm:text-3xl font-black uppercase tracking-tight text-carbon">
              MULTI-MODAL FORENSIC SENSORS (STAGE 2)
            </h2>
            <p className="text-xs font-mono text-slate">
              Multi-sensor evaluation parsed by the Reliability Gate.
            </p>
          </div>
          <span className="text-[11px] font-mono text-slate bg-paper px-3 py-1 rounded-pill border border-ash">
            MODEL SCORES ARE RAW BENCHMARK ACTIVATIONS, NOT PROBABILITIES
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          
          {/* Card 1: Visual Modality */}
          <div className="editorial-card p-5 bg-paper space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold uppercase text-slate flex items-center space-x-1.5">
                <Eye className="w-3.5 h-3.5 text-carbon" />
                <span>VISUAL FORENSICS</span>
              </span>
              <span className="editorial-pill-tag bg-mist border border-ash text-carbon">
                {isAudio ? 'N/A' : (evidence?.visual.level || 'N/A')}
              </span>
            </div>
            <div>
              {isAudio ? (
                <div>
                  <p className="text-xs font-bold text-carbon">Not Applicable</p>
                  <p className="text-[11px] text-slate font-mono mt-1">Bypassed for audio-only inputs.</p>
                </div>
              ) : (
                <div>
                  <p className="text-xs font-bold text-carbon font-mono">{visual.model || 'EfficientNet-B0'}</p>
                  <p className="text-[11px] text-slate font-mono mt-1">
                    Peak Score: {evidence?.visual.models[0]?.score?.toFixed(4) ?? visual.results[0]?.fake_score?.toFixed(4) ?? '0.0000'}
                  </p>
                  <p className="text-[10px] text-smoke font-mono mt-0.5">
                    Faces: {visual.faces_found}/{visual.frames_analyzed} frames
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Card 2: Audio Anti-Spoofing */}
          <div className="editorial-card p-5 bg-paper space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold uppercase text-slate flex items-center space-x-1.5">
                <Mic className="w-3.5 h-3.5 text-carbon" />
                <span>AUDIO ANTI-SPOOF</span>
              </span>
              <span className="editorial-pill-tag bg-mist border border-ash text-carbon">
                {evidence?.audio.level || 'N/A'}
              </span>
            </div>
            <div>
              <p className="text-xs font-bold text-carbon font-mono">{audio.model || 'AASIST-ASVspoof2019-LA'}</p>
              <p className="text-[11px] text-slate font-mono mt-1">
                Peak Score: {evidence?.audio.models[0]?.score.toFixed(4) ?? audio.results[0]?.spoof_score?.toFixed(4) ?? '0.0000'}
              </p>
              <p className="text-[10px] text-smoke font-mono mt-0.5">
                Windows: {audio.windows_analyzed ?? 0} ({audio.processing_time_s?.toFixed(2) ?? '0.00'}s)
              </p>
            </div>
          </div>

          {/* Card 3: C2PA Provenance */}
          <div className="editorial-card p-5 bg-paper space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold uppercase text-slate flex items-center space-x-1.5">
                <FileCheck2 className="w-3.5 h-3.5 text-carbon" />
                <span>C2PA PROVENANCE</span>
              </span>
              <span className="editorial-pill-tag bg-mist border border-ash text-carbon">
                {evidence?.provenance.state || 'NONE_FOUND'}
              </span>
            </div>
            <div>
              <p className="text-xs font-bold text-carbon font-mono">
                {evidence?.provenance.signer ? `Signer: ${evidence.provenance.signer}` : 'Content Credentials'}
              </p>
              <p className="text-[11px] text-slate font-mono mt-1 leading-snug">
                {evidence?.provenance.note || 'Absence of credentials does not imply manipulation.'}
              </p>
            </div>
          </div>

          {/* Card 4: Reliability Gate */}
          <div className="editorial-card p-5 bg-paper space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold uppercase text-slate flex items-center space-x-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-carbon" />
                <span>EVIDENCE QUALITY</span>
              </span>
              <span className="editorial-pill-tag bg-mist border border-ash text-carbon">
                {reliability?.level || 'OK'}
              </span>
            </div>
            <div>
              <p className="text-xs font-bold text-carbon font-mono">
                {reliability?.level === 'OK' ? 'Quality Criteria Met' : 'Degraded Quality'}
              </p>
              <div className="mt-1 text-[11px] font-mono text-slate">
                {reliability?.reasons && reliability.reasons.length > 0 ? (
                  <ul className="list-disc list-inside space-y-0.5 text-carbon">
                    {reliability.reasons.map((r, i) => (
                      <li key={i} className="truncate">{r}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-slate">Resolution &amp; duration pass thresholds.</p>
                )}
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* 4. Signature Multi-Modal Timeline */}
      <div className="editorial-card-lg p-6 sm:p-8 bg-paper space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-ash/80">
          <div>
            <h2 className="font-display text-2xl sm:text-3xl font-black uppercase tracking-tight text-carbon">
              EVIDENCE TIMELINE &amp; CHRONOLOGY
            </h2>
            <p className="text-xs font-mono text-slate">
              Aligned multi-sensor activations across duration. Click any event to inspect.
            </p>
          </div>
          <div className="flex items-center space-x-3 text-xs font-mono text-slate">
            <span className="flex items-center space-x-1"><span className="w-2 h-2 rounded bg-carbon inline-block"/><span>Anomaly</span></span>
            <span className="flex items-center space-x-1"><span className="w-2 h-2 rounded bg-mint border border-carbon/20 inline-block"/><span>Speech</span></span>
          </div>
        </div>

        {/* Timeline Tracks Box */}
        <div className="p-5 rounded-[20px] bg-mist border border-ash space-y-5">
          
          {/* Time axis */}
          <div className="flex justify-between text-[11px] font-mono text-smoke border-b border-ash/80 pb-2">
            <span>00:00</span>
            <span>{(totalDuration * 0.25).toFixed(1)}s</span>
            <span>{(totalDuration * 0.50).toFixed(1)}s</span>
            <span>{(totalDuration * 0.75).toFixed(1)}s</span>
            <span>{totalDuration.toFixed(1)}s</span>
          </div>

          {/* Track 1: Visual (Video only) */}
          {!isAudio && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-mono font-bold text-carbon">
                <span>VISUAL WINDOWS (EFFNET-B0)</span>
              </div>
              <div className="h-6 w-full bg-paper rounded-lg border border-ash relative overflow-hidden flex items-center">
                {visual.results.map((vr, i) => {
                  const left = (vr.timestamp_s / totalDuration) * 100;
                  const width = Math.max((1.0 / totalDuration) * 100, 3);
                  const isHigh = (vr.fake_score || 0) >= 0.70;
                  return (
                    <div
                      key={i}
                      style={{ left: `${left}%`, width: `${width}%` }}
                      onClick={() => setSelectedTimelineEvent({
                        start_s: vr.timestamp_s,
                        end_s: vr.timestamp_s + 1.0,
                        kind: 'visual',
                        level: isHigh ? 'HIGH' : 'LOW',
                        evidence_source: 'EfficientNet-B0 Face Crop',
                        score: vr.fake_score,
                      })}
                      className={`absolute h-4 rounded cursor-pointer transition-all ${
                        isHigh ? 'bg-carbon' : 'bg-ash/60'
                      }`}
                      title={`Visual @ ${vr.timestamp_s.toFixed(1)}s | Fake Score: ${(vr.fake_score || 0).toFixed(4)}`}
                    />
                  );
                })}
              </div>
            </div>
          )}

          {/* Track 2: Audio AASIST */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono font-bold text-carbon">
              <span>AUDIO WINDOWS (AASIST GRAPH ATTENTION)</span>
            </div>
            <div className="h-6 w-full bg-paper rounded-lg border border-ash relative overflow-hidden flex items-center">
              {audio.results.map((ar, i) => {
                const left = (ar.start_s / totalDuration) * 100;
                const width = Math.max(((ar.end_s - ar.start_s) / totalDuration) * 100, 4);
                const isHigh = (ar.spoof_score || 0) >= 0.70;
                return (
                  <div
                    key={i}
                    style={{ left: `${left}%`, width: `${width}%` }}
                    onClick={() => setSelectedTimelineEvent({
                      start_s: ar.start_s,
                      end_s: ar.end_s,
                      kind: 'audio',
                      level: isHigh ? 'HIGH' : 'LOW',
                      evidence_source: 'AASIST Audio Window',
                      score: ar.spoof_score,
                    })}
                    className={`absolute h-4 rounded cursor-pointer transition-all ${
                      isHigh ? 'bg-carbon' : 'bg-ash/60'
                    }`}
                    title={`Audio [${ar.start_s.toFixed(1)}s - ${ar.end_s.toFixed(1)}s] | Spoof Score: ${(ar.spoof_score || 0).toFixed(4)}`}
                  />
                );
              })}
            </div>
          </div>

          {/* Track 3: Fraud Directives */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono font-bold text-carbon">
              <span>FRAUD INTENT SPANS</span>
            </div>
            <div className="h-6 w-full bg-paper rounded-lg border border-ash relative overflow-hidden flex items-center">
              {fraud?.requested_actions && fraud.requested_actions.length > 0 ? (
                fraud.requested_actions.map((act, i) => {
                  const left = (act.start_s / totalDuration) * 100;
                  const width = Math.max(((act.end_s - act.start_s) / totalDuration) * 100, 6);
                  return (
                    <div
                      key={i}
                      style={{ left: `${left}%`, width: `${width}%` }}
                      onClick={() => setSelectedTimelineEvent({
                        start_s: act.start_s,
                        end_s: act.end_s,
                        kind: 'fraud',
                        level: 'HIGH',
                        evidence_source: `Action: ${act.action}`,
                        score: null,
                      })}
                      className="absolute h-4 rounded bg-carbon text-paper text-[9px] font-mono flex items-center justify-center cursor-pointer px-1 truncate font-bold"
                      title={`Fraud Action: ${act.action} ("${act.phrase}")`}
                    >
                      {act.action}
                    </div>
                  );
                })
              ) : (
                <div className="text-[11px] font-mono text-smoke pl-3">No direct extraction triggers detected</div>
              )}
            </div>
          </div>

          {/* Track 4: Speech Segments */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono font-bold text-carbon">
              <span>TRANSCRIPT SEGMENTS (WHISPER)</span>
            </div>
            <div className="h-6 w-full bg-paper rounded-lg border border-ash relative overflow-hidden flex items-center">
              {speech.segments.map((seg, i) => {
                const left = (seg.start_s / totalDuration) * 100;
                const width = Math.max(((seg.end_s - seg.start_s) / totalDuration) * 100, 5);
                return (
                  <div
                    key={i}
                    style={{ left: `${left}%`, width: `${width}%` }}
                    onClick={() => setSelectedTimelineEvent({
                      start_s: seg.start_s,
                      end_s: seg.end_s,
                      kind: 'speech',
                      level: 'INFO',
                      evidence_source: `Transcript: "${seg.text}"`,
                      score: null,
                    })}
                    className="absolute h-4 rounded bg-mint border border-carbon/20 text-carbon cursor-pointer text-[9px] font-mono px-1 truncate font-semibold"
                    title={`[${seg.start_s.toFixed(1)}s - ${seg.end_s.toFixed(1)}s]: "${seg.text}"`}
                  >
                    {seg.text}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Selected Event Drawer */}
          {selectedTimelineEvent && (
            <div className="mt-4 p-4 rounded-xl bg-paper border border-carbon flex items-center justify-between font-mono text-xs">
              <div>
                <span className="font-bold text-carbon">
                  [{selectedTimelineEvent.start_s.toFixed(1)}s – {selectedTimelineEvent.end_s.toFixed(1)}s]
                </span>
                <span className="text-slate ml-2">{selectedTimelineEvent.evidence_source}</span>
                {selectedTimelineEvent.score !== null && (
                  <span className="ml-2 text-smoke">
                    (Score: {selectedTimelineEvent.score.toFixed(4)})
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => setSelectedTimelineEvent(null)}
                className="font-bold uppercase text-carbon hover:underline text-[11px]"
              >
                Close ✕
              </button>
            </div>
          )}

        </div>
      </div>

      {/* 5. Forensic Speech & Transcript Inspector */}
      {speech.segments && speech.segments.length > 0 && (
        <div className="editorial-card-lg p-6 sm:p-8 bg-paper space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-ash/80">
            <div>
              <h2 className="font-display text-2xl sm:text-3xl font-black uppercase tracking-tight text-carbon">
                FORENSIC SPEECH TRANSCRIPT ({speech.model || 'WHISPER'})
              </h2>
              <p className="text-xs font-mono text-slate">
                Timestamped verbatim transcription (Language: {speech.language || 'en'}).
              </p>
            </div>
            <span className="text-[11px] font-mono text-slate bg-mist px-3 py-1 rounded-pill border border-ash">
              {speech.segments.length} segments · {speech.processing_time_s ? `${speech.processing_time_s.toFixed(2)}s process time` : 'processed'}
            </span>
          </div>

          <div className="space-y-2 max-h-80 overflow-y-auto pr-2">
            {speech.segments.map((seg, idx) => {
              const hasFraudAction = fraud?.requested_actions?.some(
                (act) => Math.max(seg.start_s, act.start_s) < Math.min(seg.end_s, act.end_s)
              );
              return (
                <div
                  key={idx}
                  className={`p-3.5 rounded-xl border flex items-start space-x-3 transition-colors ${
                    hasFraudAction
                      ? 'bg-mist border-carbon text-carbon'
                      : 'bg-paper border-ash/80 text-slate'
                  }`}
                >
                  <span className="font-mono text-xs font-bold text-carbon shrink-0 pt-0.5">
                    [{seg.start_s.toFixed(1)}s – {seg.end_s.toFixed(1)}s]
                  </span>
                  <p className="text-xs font-sans leading-relaxed flex-1 text-carbon">
                    "{seg.text}"
                  </p>
                  {hasFraudAction && (
                    <span className="editorial-pill-tag bg-carbon text-paper text-[10px] shrink-0 font-mono">
                      FLAGGED DIRECTIVE
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 6. High-Risk Extraction Findings & Social Engineering */}
      {fraud?.requested_actions && fraud.requested_actions.length > 0 && (
        <div className="editorial-inverted-card p-8 sm:p-10 space-y-6">
          <div className="pb-4 border-b border-graphite">
            <span className="editorial-pill-tag bg-graphite text-mint text-[11px] font-mono font-bold mb-2">
              CRITICAL FORENSIC FINDING
            </span>
            <h2 className="font-display text-3xl sm:text-4xl font-black uppercase tracking-tight text-paper">
              DETECTED HIGH-RISK EXTRACTION DIRECTIVES
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {fraud.requested_actions.map((act, i) => (
              <div key={i} className="p-5 rounded-[20px] bg-graphite/80 border border-graphite space-y-2">
                <div className="flex items-center justify-between font-mono text-xs">
                  <span className="px-2.5 py-0.5 rounded-pill bg-mint text-carbon font-bold">
                    {act.action}
                  </span>
                  <span className="text-smoke">
                    {act.start_s.toFixed(1)}s – {act.end_s.toFixed(1)}s
                  </span>
                </div>
                <p className="text-xs font-mono text-paper bg-carbon p-3 rounded-lg border border-graphite">
                  "{act.phrase}"
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 7b. Active Learning & Human Ground-Truth Verification */}
      <div className="editorial-card-lg p-6 sm:p-8 bg-paper space-y-6 border border-ash">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-ash/80">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-pill bg-mist border border-ash text-carbon text-[11px] font-mono font-bold uppercase tracking-wider mb-2">
              <Sparkles className="w-3.5 h-3.5 text-carbon" />
              <span>ACTIVE LEARNING FEEDBACK LOOP</span>
            </div>
            <h2 className="font-display text-2xl sm:text-3xl font-black uppercase tracking-tight text-carbon">
              VERIFY REPORT &amp; TRAIN AI MODELS
            </h2>
          </div>
          <span className="text-xs font-mono text-smoke">
            Human-in-the-loop ground-truth calibration
          </span>
        </div>

        {fbSuccess && (
          <div className="p-5 rounded-xl bg-mint/40 border border-mint text-carbon font-mono text-xs space-y-3">
            <div className="flex items-center space-x-2.5 font-bold text-sm">
              <Check className="w-5 h-5 text-carbon shrink-0" />
              <span>{fbSuccess}</span>
            </div>
            {fbTrainingData && (
              <div className="pt-3 border-t border-carbon/15 grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
                <div className="p-2 rounded bg-paper/60 border border-carbon/10">
                  <span className="text-slate block text-[10px] uppercase font-bold">Adapter Version</span>
                  <span className="font-bold text-carbon text-xs">{fbTrainingData.active_version}</span>
                </div>
                <div className="p-2 rounded bg-paper/60 border border-carbon/10">
                  <span className="text-slate block text-[10px] uppercase font-bold">Samples Trained</span>
                  <span className="font-bold text-carbon text-xs">{fbTrainingData.samples_used}</span>
                </div>
                <div className="p-2 rounded bg-paper/60 border border-carbon/10">
                  <span className="text-slate block text-[10px] uppercase font-bold">Loss Delta</span>
                  <span className="font-bold text-carbon text-xs">{fbTrainingData.initial_loss} → {fbTrainingData.final_loss}</span>
                </div>
                <div className="p-2 rounded bg-paper/60 border border-carbon/10">
                  <span className="text-slate block text-[10px] uppercase font-bold">Trainable Weights</span>
                  <span className="font-bold text-carbon text-xs">{fbTrainingData.trainable_parameters?.toLocaleString()}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {fbError && (
          <div className="p-4 rounded-xl bg-crimson/10 border border-crimson text-crimson font-mono text-xs flex items-center space-x-3">
            <AlertTriangle className="w-5 h-5 text-crimson shrink-0" />
            <span>{fbError}</span>
          </div>
        )}

        {!fbSuccess && (
          <div className="space-y-5">
            <p className="text-xs font-mono text-slate leading-relaxed">
              Confirm whether this detection was accurate or a false positive/negative. Your verified confirmation updates the persistent training dataset, triggers actual gradient-descent optimization on the model adapter, and versions the checkpoint.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              {/* Media Origin Verification */}
              <div className="p-4 rounded-xl bg-mist border border-ash space-y-2.5">
                <span className="font-mono text-xs font-bold text-carbon uppercase block">
                  1. Ground Truth Media Origin:
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setFbMedia('REAL')}
                    className={`flex-1 py-2.5 px-3 rounded-lg font-mono text-xs font-bold transition-all ${
                      fbMedia === 'REAL'
                        ? 'bg-carbon text-paper shadow-none'
                        : 'bg-paper border border-ash text-slate hover:text-carbon'
                    }`}
                  >
                    📷 CONFIRMED REAL
                  </button>
                  <button
                    type="button"
                    onClick={() => setFbMedia('FAKE')}
                    className={`flex-1 py-2.5 px-3 rounded-lg font-mono text-xs font-bold transition-all ${
                      fbMedia === 'FAKE'
                        ? 'bg-carbon text-paper shadow-none'
                        : 'bg-paper border border-ash text-slate hover:text-carbon'
                    }`}
                  >
                    ⚠️ CONFIRMED DEEPFAKE
                  </button>
                </div>
              </div>

              {/* Fraud Intent Verification */}
              <div className="p-4 rounded-xl bg-mist border border-ash space-y-2.5">
                <span className="font-mono text-xs font-bold text-carbon uppercase block">
                  2. Ground Truth Fraud Intent:
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setFbFraud('HARMLESS')}
                    className={`flex-1 py-2.5 px-3 rounded-lg font-mono text-xs font-bold transition-all ${
                      fbFraud === 'HARMLESS'
                        ? 'bg-carbon text-paper shadow-none'
                        : 'bg-paper border border-ash text-slate hover:text-carbon'
                    }`}
                  >
                    🛡️ CONFIRMED HARMLESS
                  </button>
                  <button
                    type="button"
                    onClick={() => setFbFraud('SCAM')}
                    className={`flex-1 py-2.5 px-3 rounded-lg font-mono text-xs font-bold transition-all ${
                      fbFraud === 'SCAM'
                        ? 'bg-carbon text-paper shadow-none'
                        : 'bg-paper border border-ash text-slate hover:text-carbon'
                    }`}
                  >
                    🚨 CONFIRMED SCAM / FRAUD
                  </button>
                </div>
              </div>

            </div>

            {/* Notes input */}
            <div className="space-y-1.5">
              <label className="font-mono text-xs text-slate block">
                Analyst Notes / Context (optional):
              </label>
              <input
                type="text"
                placeholder="e.g. Low-light webcam call with lighting glare; actual human speaker confirmed."
                value={fbNotes}
                onChange={(e) => setFbNotes(e.target.value)}
                className="w-full px-4 py-2 rounded-lg bg-paper border border-ash text-xs font-mono text-carbon placeholder:text-smoke focus:outline-none focus:border-carbon"
              />
            </div>

            {/* Submit button */}
            <div className="flex justify-end">
              <button
                type="button"
                disabled={!fbMedia || !fbFraud || fbSubmitting}
                onClick={handleSendFeedback}
                className="editorial-btn-primary flex items-center space-x-2 font-mono text-xs uppercase disabled:opacity-40"
              >
                <Database className="w-4 h-4" />
                <span>{fbSubmitting ? 'Extracting features & optimizing adapter...' : 'Submit Ground-Truth & Train Adapter'}</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 8. Actionable Safe Steps Protocol */}
      <div className="editorial-card-lg p-6 sm:p-8 bg-paper space-y-4 border border-ash">
        <h2 className="font-display text-2xl font-black uppercase tracking-tight text-carbon">
          RECOMMENDED NEXT STEPS &amp; VERIFICATION PROTOCOL
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-sans">
          <div className="p-4 rounded-xl bg-mist border border-ash space-y-1">
            <p className="font-bold text-carbon font-mono">01. OUT-OF-BAND CALL</p>
            <p className="text-slate">Call the claimed sender on their known official number from your corporate directory.</p>
          </div>
          <div className="p-4 rounded-xl bg-mist border border-ash space-y-1">
            <p className="font-bold text-carbon font-mono">02. NEVER SHARE SECRETS</p>
            <p className="text-slate">Legitimate institutions will never ask you to read out 2FA OTP codes or wire emergency funds secretly.</p>
          </div>
          <div className="p-4 rounded-xl bg-mist border border-ash space-y-1">
            <p className="font-bold text-carbon font-mono">03. REPORT INCIDENT</p>
            <p className="text-slate">If extortion or credential theft was attempted, immediately alert your security department.</p>
          </div>
        </div>
      </div>

    </div>
  );
};
