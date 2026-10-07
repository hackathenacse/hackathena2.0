import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FileVideo, 
  Music, 
  Check, 
  AlertTriangle, 
  X, 
  ArrowRight, 
  Loader2,
  Lock,
  Layers,
  ShieldAlert,
  Cpu
} from 'lucide-react';
import { analyzeVideo, ApiError } from '../services/api';
import { ExtensionModal } from '../components/ExtensionModal';

const MAX_FILE_SIZE_MB = 100;
const VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.webm', '.mkv'];
const AUDIO_EXTENSIONS = ['.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac', '.wma'];
const ALLOWED_EXTENSIONS = [...VIDEO_EXTENSIONS, ...AUDIO_EXTENSIONS];

const VIDEO_STEPS = [
  '01  VALIDATING MEDIA CONTAINER & SIGNATURES',
  '02  EXTRACTING VIDEO FRAMES & 16KHZ AUDIO STREAM',
  '03  ANALYZING VISUAL FACIAL MANIPULATION (EFFNET-B0)',
  '04  EVALUATING ACOUSTIC VOICE ANTI-SPOOFING (AASIST)',
  '05  TRANSCRIBING SPEECH & DETECTING LANGUAGE (WHISPER)',
  '06  INSPECTING C2PA CONTENT CREDENTIALS PROVENANCE',
  '07  SYNTHESIZING MULTI-MODAL EVIDENCE TIMELINE',
  '08  ASSESSING SOCIAL-ENGINEERING FRAUD DIRECTIVES',
];

const AUDIO_STEPS = [
  '01  VALIDATING AUDIO CONTAINER & HEADER DATA',
  '02  EXTRACTING 16KHZ FORENSIC PCM WAVEFORM',
  '03  EVALUATING ACOUSTIC VOICE ANTI-SPOOFING (AASIST)',
  '04  TRANSCRIBING SPEECH & DETECTING LANGUAGE (WHISPER)',
  '05  INSPECTING C2PA CONTENT CREDENTIALS PROVENANCE',
  '06  SYNTHESIZING ACOUSTIC EVIDENCE TIMELINE',
  '07  ASSESSING SOCIAL-ENGINEERING FRAUD DIRECTIVES',
];

export const AnalyzePage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [isExtensionModalOpen, setIsExtensionModalOpen] = useState<boolean>(false);

  const isAudioFile = selectedFile 
    ? AUDIO_EXTENSIONS.some(ext => selectedFile.name.toLowerCase().endsWith(ext)) || selectedFile.type.startsWith('audio/')
    : false;

  const currentSteps = isAudioFile ? AUDIO_STEPS : VIDEO_STEPS;

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isAnalyzing) {
      setCurrentStepIndex(0);
      interval = setInterval(() => {
        setCurrentStepIndex((prev) => {
          if (prev < currentSteps.length - 1) {
            return prev + 1;
          }
          return prev;
        });
      }, 1400);
    }
    return () => clearInterval(interval);
  }, [isAnalyzing, currentSteps.length]);

  const validateFile = (file: File): boolean => {
    setError(null);
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError(`Unsupported format "${ext}". Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`);
      return false;
    }

    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > MAX_FILE_SIZE_MB) {
      setError(`File size (${sizeMB.toFixed(1)} MB) exceeds limit of ${MAX_FILE_SIZE_MB} MB.`);
      return false;
    }

    if (file.size === 0) {
      setError('Selected file is empty (0 bytes).');
      return false;
    }

    return true;
  };

  const handleFileSelect = (file: File) => {
    if (validateFile(file)) {
      setSelectedFile(file);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleStartAnalysis = async () => {
    if (!selectedFile) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      const result = await analyzeVideo(selectedFile);
      navigate(`/results/${result.id}`, { state: { analysis: result } });
    } catch (err: any) {
      setIsAnalyzing(false);
      if (err instanceof ApiError) {
        setError(`Analysis Error (${err.status}): ${err.detail}`);
      } else {
        setError(err.message || 'An unexpected error occurred during forensic analysis.');
      }
    }
  };

  return (
    <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8 space-y-12 sm:space-y-16">
      
      {/* 1. Hero Split Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start pt-2 sm:pt-4">
        
        {/* Left: Oversized Editorial Statement */}
        <div className="lg:col-span-6 space-y-6">
          
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-pill bg-paper border border-ash text-carbon text-xs font-mono font-bold uppercase tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-carbon" />
            <span>MEDIA AUTHENTICITY &amp; FRAUD DEFENSE</span>
          </div>

          <h1 className="font-display text-6xl sm:text-7xl lg:text-8xl font-black uppercase tracking-tight leading-[0.88] text-carbon">
            ANALYZE<br />
            BEFORE YOU<br />
            TRUST.
          </h1>

          <p className="text-base sm:text-lg text-slate leading-relaxed max-w-lg font-normal">
            Multi-modal forensic evaluation for synthetic video, cloned voices, and social-engineering extortion directives. Evaluated locally with zero data retention.
          </p>

          <div className="flex flex-wrap items-center gap-2 pt-2">
            <span className="editorial-pill-tag bg-mint text-carbon border border-carbon/20">
              EFFNET-B0 VISUAL
            </span>
            <span className="editorial-pill-tag bg-mint text-carbon border border-carbon/20">
              AASIST AUDIO
            </span>
            <span className="editorial-pill-tag bg-paper text-carbon border border-ash">
              WHISPER ASR
            </span>
            <span className="editorial-pill-tag bg-paper text-carbon border border-ash">
              C2PA PROVENANCE
            </span>
          </div>

        </div>

        {/* Right: Large White Upload / Processing Card */}
        <div className="lg:col-span-6">
          <div className="editorial-card-lg p-6 sm:p-8 bg-paper">
            
            {!isAnalyzing ? (
              <div className="space-y-6">
                
                <div className="flex items-center justify-between pb-4 border-b border-ash/80 font-mono text-xs text-slate">
                  <span className="font-bold uppercase text-carbon">MEDIA INGESTION</span>
                  <span className="text-smoke">ZERO-RETENTION</span>
                </div>

                {/* Dropzone */}
                <div
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-[24px] p-8 sm:p-10 text-center cursor-pointer transition-all ${
                    dragActive 
                      ? 'border-carbon bg-mist' 
                      : 'border-ash hover:border-carbon bg-mist/60 hover:bg-mist'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={ALLOWED_EXTENSIONS.join(',')}
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        handleFileSelect(e.target.files[0]);
                      }
                    }}
                  />

                  <div className="w-12 h-12 mx-auto rounded-full bg-paper border border-ash flex items-center justify-center mb-4 text-carbon font-mono">
                    ↓
                  </div>

                  <p className="font-display text-2xl sm:text-3xl font-bold uppercase tracking-tight text-carbon">
                    DROP VIDEO OR AUDIO HERE
                  </p>

                  <p className="text-xs font-mono text-slate mt-2">
                    or click to browse files from your disk
                  </p>

                  <div className="mt-6 flex flex-wrap items-center justify-center gap-1.5 text-[11px] font-mono text-slate">
                    <span className="px-2 py-0.5 rounded bg-paper border border-ash">MP4 · MOV · WEBM</span>
                    <span className="px-2 py-0.5 rounded bg-paper border border-ash">WAV · MP3 · M4A · FLAC</span>
                    <span className="px-2 py-0.5 rounded bg-paper border border-ash">MAX 100MB</span>
                  </div>
                </div>

                {/* Selected File Card */}
                {selectedFile && (
                  <div className="p-4 rounded-xl bg-mist border border-ash flex items-center justify-between">
                    <div className="flex items-center space-x-3 truncate">
                      <div className="p-2 rounded-lg bg-paper border border-ash text-carbon shrink-0">
                        {isAudioFile ? <Music className="w-5 h-5" /> : <FileVideo className="w-5 h-5" />}
                      </div>
                      <div className="truncate">
                        <div className="flex items-center space-x-2">
                          <p className="text-sm font-bold text-carbon truncate font-mono">{selectedFile.name}</p>
                          <span className="px-2 py-0.5 rounded-pill text-[10px] font-mono font-bold bg-mint text-carbon border border-carbon/20">
                            {isAudioFile ? 'AUDIO' : 'VIDEO'}
                          </span>
                        </div>
                        <p className="text-xs text-slate font-mono mt-0.5">
                          {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB · {selectedFile.type || (isAudioFile ? 'audio/stream' : 'video/stream')}
                        </p>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedFile(null);
                      }}
                      className="p-1.5 rounded-md text-slate hover:text-carbon hover:bg-paper border border-transparent hover:border-ash transition-colors ml-2"
                      title="Remove file"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                )}

                {/* Error Banner */}
                {error && (
                  <div className="p-4 rounded-xl bg-paper border border-carbon text-carbon text-xs font-mono space-y-1">
                    <div className="flex items-center space-x-2 font-bold uppercase text-rose-600">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span>VALIDATION / SYSTEM ERROR</span>
                    </div>
                    <p className="text-slate pl-6">{error}</p>
                  </div>
                )}

                {/* Submit / Action Row */}
                <div className="pt-4 border-t border-ash/80 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="flex items-center space-x-2 text-xs font-mono text-slate">
                    <Lock className="w-3.5 h-3.5 text-carbon shrink-0" />
                    <span>In-process execution · Zero cloud transfer</span>
                  </div>

                  <button
                    type="button"
                    disabled={!selectedFile}
                    onClick={handleStartAnalysis}
                    className={`w-full sm:w-auto editorial-btn-primary flex items-center justify-center space-x-2 font-mono uppercase tracking-wider ${
                      !selectedFile ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'
                    }`}
                  >
                    <span>START FORENSIC ANALYSIS</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>

              </div>
            ) : (
              /* Forensic Processing Sequence */
              <div className="py-4 space-y-6">
                
                <div className="pb-4 border-b border-ash/80">
                  <div className="flex items-center justify-between font-mono text-xs">
                    <span className="font-bold uppercase text-carbon">FORENSIC PIPELINE IN EXECUTION</span>
                    <span className="px-2 py-0.5 rounded bg-mint text-carbon font-bold">ACTIVE</span>
                  </div>
                  <h3 className="font-display text-3xl font-black uppercase tracking-tight text-carbon mt-2">
                    ANALYZING {isAudioFile ? 'AUDIO SIGNALS' : 'MEDIA SIGNALS'}
                  </h3>
                  <p className="text-xs font-mono text-slate mt-1 truncate">
                    Subject: <span className="font-bold text-carbon">{selectedFile?.name}</span>
                  </p>
                </div>

                {/* Steps Checklist */}
                <div className="space-y-2 font-mono text-xs">
                  {currentSteps.map((step, idx) => {
                    const isDone = idx < currentStepIndex;
                    const isCurrent = idx === currentStepIndex;

                    return (
                      <div
                        key={idx}
                        className={`p-3 rounded-xl border flex items-center justify-between transition-all ${
                          isDone
                            ? 'bg-paper border-ash text-slate'
                            : isCurrent
                            ? 'bg-carbon text-paper border-carbon font-bold'
                            : 'bg-mist/50 border-transparent text-smoke'
                        }`}
                      >
                        <span className="truncate pr-2">{step}</span>
                        <div className="shrink-0">
                          {isDone ? (
                            <span className="text-carbon font-bold">DONE ✓</span>
                          ) : isCurrent ? (
                            <span className="text-mint font-bold animate-pulse">RUNNING...</span>
                          ) : (
                            <span className="text-smoke">QUEUED</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="pt-4 border-t border-ash/80 text-[11px] font-mono text-slate flex items-center justify-between">
                  <span>Executing PyTorch AASIST + Faster-Whisper</span>
                  <span className="text-smoke">Estimated time: 1-3s</span>
                </div>

              </div>
            )}

          </div>
        </div>

      </div>

      {/* 2. Chrome Extension Callout Banner */}
      <div className="editorial-card p-6 sm:p-8 bg-paper border border-ash flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2 text-center md:text-left">
          <div className="inline-flex items-center space-x-2 px-3 py-0.5 rounded-pill bg-mist border border-ash text-carbon text-xs font-mono font-bold uppercase">
            <span>REAL-TIME BROWSER PROTECTION</span>
          </div>
          <h3 className="font-display text-2xl sm:text-3xl font-black uppercase tracking-tight text-carbon">
            Authentica Chrome Extension
          </h3>
          <p className="text-xs sm:text-sm text-slate max-w-xl font-sans leading-relaxed">
            Scan live Google Meet sessions, video calls, and web audio with 1-click active tab forensic capture.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsExtensionModalOpen(true)}
          className="editorial-btn-primary flex items-center space-x-2 shrink-0 font-mono text-xs uppercase px-6 py-3.5"
        >
          <span>Get Chrome Extension</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* 3. Inverted Solid Black Architecture Block */}
      <div className="editorial-inverted-card p-8 sm:p-12 space-y-8">
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-graphite">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-pill bg-graphite text-mint text-[11px] font-mono font-bold uppercase tracking-wider mb-2">
              <span>CORE FORENSIC PRINCIPLE</span>
            </div>
            <h2 className="font-display text-3xl sm:text-4xl lg:text-5xl font-black uppercase tracking-tight text-paper">
              MEDIA MANIPULATION ≠ FRAUD INTENT
            </h2>
          </div>
          <p className="text-xs font-mono text-smoke max-w-sm">
            Authentica evaluates physical generation artifacts and psychological social-engineering pressure as two independent dimensions.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          <div className="p-6 rounded-[24px] bg-graphite/60 border border-graphite space-y-3">
            <span className="font-mono text-xs font-bold text-mint uppercase">01 / VISUAL &amp; VOICE SYNTHESIS</span>
            <h3 className="font-display text-xl font-bold uppercase tracking-tight text-paper">
              Acoustic &amp; Facial Forensics
            </h3>
            <p className="text-xs text-smoke leading-relaxed font-sans">
              Measures facial boundary warps via EfficientNet-B0 and raw audio spectral phase anomalies via AASIST Graph Attention Networks.
            </p>
          </div>

          <div className="p-6 rounded-[24px] bg-graphite/60 border border-graphite space-y-3">
            <span className="font-mono text-xs font-bold text-mint uppercase">02 / FRAUD INTENT ENGINE</span>
            <h3 className="font-display text-xl font-bold uppercase tracking-tight text-paper">
              Linguistic Directives &amp; Extortion
            </h3>
            <p className="text-xs text-smoke leading-relaxed font-sans">
              Extracts high-risk directives (OTP extraction, wire transfer demands, remote AnyDesk installs, secrecy orders) from spoken speech.
            </p>
          </div>

          <div className="p-6 rounded-[24px] bg-graphite/60 border border-graphite space-y-3">
            <span className="font-mono text-xs font-bold text-mint uppercase">03 / CALIBRATED SAFE ACTION</span>
            <h3 className="font-display text-xl font-bold uppercase tracking-tight text-paper">
              Grounded Recommendations
            </h3>
            <p className="text-xs text-smoke leading-relaxed font-sans">
              Renders actionable protocols (STOP AND VERIFY, CAUTION, VERIFY, NO ACTION) based on multi-frame persistence and context awareness.
            </p>
          </div>

        </div>

      </div>

      {/* Extension Modal */}
      <ExtensionModal
        isOpen={isExtensionModalOpen}
        onClose={() => setIsExtensionModalOpen(false)}
      />

    </div>
  );
};
