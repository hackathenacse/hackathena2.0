# AUTHENTICA — Complete Development Log (Stages 1 – 4 & Audio Analysis)

**Theme:** AI Fraud & Deepfake Detection (Hackathena '26 2.0)  
**Status:** 100% Operational & Verified on Local Infrastructure  
**Test Suite:** 71 / 71 Automated Pytest Unit & Integration Tests Passing  

---

## 🚀 Unified Multi-Modal Pipeline Architecture

```
                      [ Client Media Upload (Video / Audio) ]
                                         │
                           POST /api/analyses (multipart)
                                         ▼
                             ┌───────────────────────┐
                             │ Fast Validation Layer │ (MIME, Extension, Size, Header)
                             └───────────┬───────────┘
                                         ▼
                             ┌───────────────────────┐
                             │  Ephemeral Workspace  │ (temp/{analysis_id}/)
                             └───────────┬───────────┘
                                         ▼
                             ┌───────────────────────┐
                             │  SHA-256 Fingerprint  │ (Streaming crypto hash)
                             └───────────┬───────────┘
                                         ▼
                             ┌───────────────────────┐
                             │  Media Type Probing   │ (FFprobe: Video vs Standalone Audio)
                             └───────────┬───────────┘
                                         │
                     ┌───────────────────┴───────────────────┐
                     ▼                                       ▼
             [ VIDEO PIPELINE ]                      [ AUDIO PIPELINE ]
                     │                                       │
     ┌───────────────┴───────────────┐                       │
     ▼                               ▼                       ▼
┌──────────────┐             ┌──────────────┐         ┌──────────────┐
│Frame Sampling│             │16kHz PCM WAV │         │16kHz PCM WAV │
│   (~1 FPS)   │             │  Extraction  │         │ Normalization│
└──────┬───────┘             └──────┬───────┘         └──────┬───────┘
       │                            │                        │
       ▼                            ▼                        ▼
┌──────────────┐             ┌──────────────┐         ┌──────────────┐
│   STAGE 1    │             │   STAGE 1    │         │   STAGE 1    │
│  BlazeFace   │             │    AASIST    │         │    AASIST    │
│      +       │             │ Anti-Spoofing│         │ Anti-Spoofing│
│EfficientNet-B0│            │      +       │         │      +       │
│ (FF++ C23)   │             │Faster-Whisper│         │Faster-Whisper│
└──────┬───────┘             └──────┬───────┘         └──────┬───────┘
       │                            │                        │
       └────────────────────┬───────┘                        │
                            │                                │
                            ▼                                ▼
              ┌───────────────────────────┐    ┌───────────────────────────┐
              │ STAGE 2: FORENSICS FUSION │    │ STAGE 2: AUDIO SYNTHESIS  │
              │ - Video Reliability Gate  │    │ - Audio Reliability Gate  │
              │ - C2PA Provenance Check   │    │ - C2PA Provenance Check   │
              │ - Multi-Modal Timeline    │    │ - Audio Anomaly Timeline  │
              │ - Evidence Matrix Build   │    │ - Evidence Matrix Build   │
              └─────────────┬─────────────┘    └─────────────┬─────────────┘
                            │                                │
                            └────────────────┬───────────────┘
                                             │
                                             ▼
                             ┌───────────────────────────────┐
                             │ STAGE 3: FRAUD INTENT ENGINE  │
                             │ - Spoken Directive Extraction │
                             │ - Social Engineering Taxonomy │
                             │ - Scam Awareness Downgrade    │
                             │ - Orthogonal Risk Assessment  │
                             │ - Final Action Recommendation │
                             └───────────────┬───────────────┘
                                             ▼
                             ┌───────────────────────────────┐
                             │ STAGE 4: USER PROTECTION UI   │
                             │ - Interactive Multi-Track Bar │
                             │ - Speech Transcript Inspector │
                             │ - Clear Explanations & Limits │
                             │ - Local Session History       │
                             └───────────────┬───────────────┘
                                             ▼
                             ┌───────────────────────────────┐
                             │       Workspace Cleanup       │ (Zero-Retention Purge)
                             └───────────────┬───────────────┘
                                             ▼
                              [ JSON Response / React View ]
```

---

## 📅 Stage-by-Stage Implementation History

### Stage 1: Multi-Modal Ingestion & Local AI Models
- **FastAPI Core (`backend/app/main.py`):** Structured async REST backend with lifespan checks verifying FFmpeg/FFprobe availability, CORS setup, and global error handling.
- **Media Ingestion & Validation (`backend/app/services/video_processor.py`):**
  - Robust multipart file streaming with MIME validation and extension gating.
  - Streaming SHA-256 cryptographic fingerprint computation.
  - 1 FPS frame sampling with millisecond timestamps using OpenCV.
  - Audio extraction to standardized 16kHz mono 16-bit PCM WAV using FFmpeg.
- **Visual AI Face Deepfake Detector (`backend/app/services/detectors/visual_detector.py`):**
  - MediaPipe BlazeFace Short Range model (`blaze_face_short_range.tflite`) for face localization and bounding box extraction.
  - Pretrained `EfficientNet-B0-FFPP-C23` model ([Xicor9/efficientnet-b0-ffpp-c23](https://huggingface.co/Xicor9/efficientnet-b0-ffpp-c23)) running locally on GPU/CPU for facial manipulation inference.
- **Audio Voice Anti-Spoofing Detector (`backend/app/services/detectors/audio_detector.py`):**
  - Pretrained Clova AI AASIST Graph Attention Network ([clovaai/aasist](https://github.com/clovaai/aasist)) executing on raw 16kHz audio waveforms with 4-second sliding windows and 2-second stride.
- **Speech-to-Text Transcription (`backend/app/services/detectors/speech_transcriber.py`):**
  - `faster-whisper-base` engine via CTranslate2 INT8 execution, Silero VAD silence suppression, multilingual automatic language detection, and timestamped speech segments.
- **Zero-Retention Ephemeral Privacy (`backend/app/utils/temp_manager.py`):**
  - Ephemeral directories (`temp/{analysis_id}/`) wiped immediately after request completion.

### Stage 2: Forensics Synthesis, Provenance & Evidence Matrix
- **Reliability Gate (`backend/app/services/reliability_service.py`):**
  - Verifies minimum duration ($\ge 3.0$s), frame resolution ($\ge 200\times 200$), and primary face coverage ($\ge 30\%$).
  - Gracefully handles low-quality media by degrading reliability to `LOW` instead of generating false positives.
- **C2PA Provenance Inspection (`backend/app/services/c2pa_service.py`):**
  - Integrates `c2pa-python` to inspect Content Authenticity Initiative manifests and cryptographic signatures.
- **Multi-Modal Timeline Aggregator (`backend/app/services/timeline_service.py`):**
  - Dynamically computes chronological windows for visual artifacts, acoustic anomalies, fraud triggers, and speech segments.
  - Aggregates contiguous anomaly windows and counts only frames evaluated within each respective window range.
- **Evidence Matrix & Assessment (`backend/app/services/evidence_service.py`, `assessment_service.py`):**
  - Categorizes evidence levels (`HIGH`, `MEDIUM`, `LOW`, `N/A`) for each modality.
  - Delivers grounded, transparent explanations and explicit forensic limitation disclaimers.

### Stage 3: Fraud Intent Engine & Orthogonal Assessment
- **Orthogonal Risk Modeling (`backend/app/services/fraud_engine.py`):**
  - Decouples **Media Manipulation Risk** (`LIKELY_MANIPULATED`, `SUSPICIOUS`, `NO_STRONG_EVIDENCE`, `UNCERTAIN`) from **Fraud Intent Risk** (`HIGH`, `MEDIUM`, `LOW`, `NOT_ASSESSABLE`).
- **High-Risk Extraction Directives:**
  - Detects OTP and 2FA credential theft directives.
  - Detects financial transfer demands (Bank wire, UPI, Crypto, Rupees/Dollars/Euros).
  - Detects remote desktop software directives (AnyDesk, TeamViewer, QuickSupport).
  - Detects urgent executive/law enforcement impersonation patterns.
- **Scam Awareness & News Context Filter:**
  - Recognizes awareness/reporting phrasing ("police warned against", "fraudsters are using", "scam alert") and safely downgrades fraud severity.
- **Unified Action Recommendations:**
  - `STOP_AND_VERIFY`, `VERIFY`, `CAUTION`, `NO_ACTION_FLAGGED`.

### Stage 4: User Protection Layer & Web Application
- **React 19 + TypeScript + Tailwind CSS Frontend (`frontend/`):**
  - Modern, responsive cyber-forensic UI with dark glassmorphism theme.
  - `/` Analyze Page: Drag-and-drop file upload, file preview, dynamic format badges, and deterministic step checklist.
  - `/results/:id` Results Page: Dual-dimension risk cards, Evidence Matrix, Interactive Horizontal Multi-Track Timeline, Forensic Speech & Transcript Inspector, Social-Engineering Tactics cards, and Recommended Next Steps checklist.
  - `/history` History Page: Client-side local storage caching, search/filter, and instant report retrieval.

### Standalone Audio Analysis End-to-End
- **Automatic Container Probing:** `probe_media_type` identifies standalone audio files (.wav, .mp3, .m4a, .flac, .ogg, .aac, .wma) while handling embedded album art cover streams.
- **Audio Processing Pipeline:** Normalizes audio to 16kHz mono WAV, bypasses visual detectors (`visual.status = "not_applicable"`), runs AASIST anti-spoofing and Faster-Whisper transcription, applies audio-specific reliability gates, and generates grounded audio explanations.
- **Full UI Support:** Dynamic audio format badges, Music icons, dedicated audio progress steps, audio timeline tracks, and speech transcript viewers.

### Calibration & Accuracy Hardening
- Implemented multi-frame anomaly persistence gating to eliminate false positives caused by single-frame visual or acoustic model spikes on authentic recordings.
- Refined regex pattern matching to distinguish subjective statements (e.g. *"I need money"*) from genuine extortion directives (e.g. *"Transfer money to this account immediately"*).

---

## 🧪 Comprehensive Test Suite Verification

All **71 automated unit and integration tests** pass with 100% success across the complete codebase:

```bash
$ pytest backend/tests/ -v
======================= 71 passed, 5 warnings in 50.44s ========================
```

| Test Module | Coverage Area | Tests | Status |
| :--- | :--- | :---: | :---: |
| `test_accuracy_calibration.py` | Multi-frame persistence & subjective phrase calibration | 8 | ✅ PASSED |
| `test_analysis_service.py` | End-to-end video analysis orchestration | 3 | ✅ PASSED |
| `test_assessment.py` | Media verdict rules & safety guarantees | 2 | ✅ PASSED |
| `test_audio_analysis.py` | Standalone audio (.wav, .mp3, short clips, corrupted) | 4 | ✅ PASSED |
| `test_audio_detector.py` | AASIST model, sliding windows, padding, error handling | 5 | ✅ PASSED |
| `test_c2pa.py` | Provenance manifest extraction & signature validation | 5 | ✅ PASSED |
| `test_evidence_service.py` | Evidence matrix aggregation & score mapping | 2 | ✅ PASSED |
| `test_ffmpeg.py` | FFmpeg/FFprobe availability & SHA-256 computation | 3 | ✅ PASSED |
| `test_fraud_engine.py` | Directive extraction, categories, news downgrade | 10 | ✅ PASSED |
| `test_health.py` | System health check endpoint | 1 | ✅ PASSED |
| `test_reliability.py` | Resolution, face coverage, duration & error gates | 6 | ✅ PASSED |
| `test_speech_transcriber.py`| Whisper transcription, language ID, VAD filtering | 4 | ✅ PASSED |
| `test_timeline.py` | Dynamic timeline window aggregation & frame counts | 3 | ✅ PASSED |
| `test_validation.py` | File size, extension, MIME, and corrupted header rejection | 4 | ✅ PASSED |
| `test_video_processor.py` | Video metadata, frame sampling, duration limits | 3 | ✅ PASSED |
| `test_visual_detector.py` | EfficientNet-B0 inference, BlazeFace crop, batching | 8 | ✅ PASSED |
