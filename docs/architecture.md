# AUTHENTICA — System Architecture & Design

## 🏛️ High-Level Architectural Overview

Authentica is a multi-modal AI forensic and social-engineering detection platform engineered to detect deepfakes, synthetic speech, manipulated media provenance, and social-engineering extortion attempts.

The system is designed around **four core principles**:
1. **Multi-Modal Local AI Forensics:** Zero external AI API dependencies; models run locally on private compute infrastructure.
2. **Orthogonal Risk Modeling:** Media manipulation and fraud intent are evaluated independently. Synthetic media can be benign (e.g. parody), while genuine authentic media can be weaponized for scams (e.g. real CEO footage paired with urgency).
3. **Forensic Transparency & Calibration:** Model scores are treated as raw forensic activations rather than absolute probabilities. Dynamic timelines and grounded explanations explain *why* a verdict was rendered.
4. **Zero-Retention Ephemeral Privacy:** Media files, frames, and extracted audio are processed in isolated ephemeral workspaces and immediately destroyed after analysis response delivery.

---

## 🔄 End-to-End Pipeline Workflow

```
                                [ CLIENT / USER ]
                                        │
                         POST /api/analyses (multipart)
                                        ▼
                         ┌─────────────────────────────┐
                         │   Fast Validation Layer     │
                         │ - MIME & Extension Check    │
                         │ - Max File Size (100 MB)    │
                         │ - Magic Header Verification │
                         └──────────────┬──────────────┘
                                        ▼
                         ┌─────────────────────────────┐
                         │    Ephemeral Workspace      │
                         │    (temp/{analysis_id}/)    │
                         └──────────────┬──────────────┘
                                        ▼
                         ┌─────────────────────────────┐
                         │     Crypto Fingerprint      │
                         │   (Streaming SHA-256 Hash)  │
                         └──────────────┬──────────────┘
                                        ▼
                         ┌─────────────────────────────┐
                         │     Media Type Probing      │
                         │ (FFprobe Stream Inspection) │
                         └──────────────┬──────────────┘
                                        │
                  ┌─────────────────────┴─────────────────────┐
                  ▼                                           ▼
          [ MEDIA_TYPE: VIDEO ]                       [ MEDIA_TYPE: AUDIO ]
                  │                                           │
       ┌──────────┴──────────┐                                │
       ▼                     ▼                                ▼
┌──────────────┐      ┌──────────────┐                 ┌──────────────┐
│Frame Sampling│      │Audio Extract │                 │Audio Normal. │
│   (~1 FPS)   │      │(16kHz Mono)  │                 │(16kHz Mono)  │
└──────┬───────┘      └──────┬───────┘                 └──────┬───────┘
       │                     │                                │
       ▼                     ▼                                ▼
┌──────────────┐      ┌──────────────┐                 ┌──────────────┐
│ Visual Model │      │ Audio Models │                 │ Audio Models │
│  MediaPipe   │      │    AASIST    │                 │    AASIST    │
│  BlazeFace   │      │ Anti-Spoof   │                 │ Anti-Spoof   │
│      +       │      │      +       │                 │      +       │
│EfficientNetB0│      │Faster-Whisper│                 │Faster-Whisper│
└──────┬───────┘      └──────┬───────┘                 └──────┬───────┘
       │                     │                                │
       └──────────────┬──────┘                                │
                      │                                       │
                      ▼                                       ▼
       ┌─────────────────────────────┐         ┌─────────────────────────────┐
       │   STAGE 2: FORENSIC FUSION  │         │   STAGE 2: FORENSIC FUSION  │
       │ - Video Reliability Gate    │         │ - Audio Reliability Gate    │
       │ - C2PA Provenance Engine    │         │ - C2PA Provenance Engine    │
       │ - Multi-Modal Timeline      │         │ - Audio Timeline Track      │
       │ - Evidence Matrix Generator │         │ - Evidence Matrix Generator │
       └──────────────┬──────────────┘         └──────────────┬──────────────┘
                      │                                       │
                      └───────────────────┬───────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────┐
                         │ STAGE 3: FRAUD INTENT ENGINE│
                         │ - Linguistic Directives     │
                         │ - Social Engineering Tactics│
                         │ - Scam Awareness Downgrade  │
                         │ - Orthogonal Risk Matrix    │
                         │ - Final User Action         │
                         └──────────────┬──────────────┘
                                        ▼
                         ┌─────────────────────────────┐
                         │      Response Assembly      │
                         │   (Unified JSON Payload)    │
                         └──────────────┬──────────────┘
                                        ▼
                         ┌─────────────────────────────┐
                         │      Workspace Cleanup      │
                         │  (Zero Retention Deletion)  │
                         └──────────────┬──────────────┘
                                        ▼
                                [ Client Response ]
```

---

## 📦 Core Subsystems & Components

### 1. Ingestion & Preprocessing Subsystem (`app/services/video_processor.py`)
- **Format Support:**
  - **Video:** `.mp4`, `.mov`, `.webm`, `.avi`, `.mkv`
  - **Audio:** `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`, `.aac`, `.wma`
- **Stream Probing:** Determines true container stream characteristics. Detects attached picture streams (`disposition.attached_pic == 1` or single MJPEG posters) to avoid misclassifying album-art audio as video.
- **Frame Extraction:** Uses OpenCV to sample video frames at ~1 FPS with millisecond-accurate timestamps (`timestamp_s`).
- **Audio Extraction:** Normalizes audio into single-channel 16,000 Hz 16-bit PCM WAV (`-ar 16000 -ac 1 -c:a pcm_s16le`).

### 2. Forensic AI Detectors Subsystem (`app/services/detectors/`)
- **Visual Deepfake Detector (`visual_detector.py`):**
  - Face Detection: MediaPipe BlazeFace Short Range model (`blaze_face_short_range.tflite`) extracts the largest face with a 10% safety margin.
  - Deepfake Classification: Hugging Face `EfficientNet-B0-FFPP-C23` pretrained on FaceForensics++ C23.
  - Generates per-frame `fake_score` and `real_score`.
- **Audio Anti-Spoofing Detector (`audio_detector.py`):**
  - Architecture: Clova AI AASIST Graph Attention Network.
  - Evaluates 4.0-second sliding windows (64,000 samples @ 16kHz) with 2.0-second stride.
  - Computes `spoof_score` indicating acoustic synthesis or voice cloning artifacts.
- **Speech-to-Text Transcriber (`speech_transcriber.py`):**
  - Engine: `faster-whisper-base` running on CTranslate2 INT8 execution.
  - Utilizes Silero VAD silence suppression.
  - Extracts timestamped speech segments (`start_s`, `end_s`, `text`) and detected language.

### 3. Forensic Fusion & Synthesis Subsystem (`app/services/`)
- **Reliability Gate (`reliability_service.py`):**
  - Ensures forensic assessments are only rendered when input quality meets minimum reliability thresholds.
  - Video checks: Duration $\ge 3.0$s, Resolution $\ge 200\times 200$, Face detection rate $\ge 30\%$, Model health.
  - Audio checks: Duration $\ge 3.0$s, Model health.
- **Provenance Verification (`c2pa_service.py`):**
  - Uses `c2pa-python` to read Content Authenticity Initiative manifests, signature validity, and issuing signers.
- **Multi-Modal Timeline (`timeline_service.py`):**
  - Consolidates contiguous visual anomalies, audio anomalies, speech intervals, and fraud triggers into an aligned chronological timeline.
- **Evidence Matrix (`evidence_service.py`):**
  - Maps model activations into categorical evidence tiers (`HIGH`, `MEDIUM`, `LOW`, `N/A`) with multi-frame persistence filtering.
- **Grounded Explanations (`assessment_service.py`):**
  - Generates clear, plain-language bullet points citing specific timestamp ranges and observed artifacts.

### 4. Fraud Intent Engine (`app/services/fraud_engine.py`)
- **Directive Matcher:** Matches spoken transcript phrases against high-risk fraud categories:
  - OTP & 2FA extraction
  - Financial wire & transfer demands
  - Remote desktop software installation
  - Executive / law enforcement impersonation
- **Context Filter:** Mitigates false positives in educational and news reporting contexts ("police warned", "scam alert").
- **Orthogonal Decision Engine:** Integrates media manipulation evidence and fraud intent into unified user recommendations:
  - `STOP_AND_VERIFY`: Critical fraud risk or high-confidence weaponized manipulation.
  - `VERIFY`: Moderate risks, suspicious indicators, or degraded reliability.
  - `CAUTION`: Synthetic media detected without harmful fraud intent.
  - `NO_ACTION_FLAGGED`: Clear media with no detected fraud directives.

---

## 🔒 Security & Privacy Guarantees

1. **Zero Data Retention:** No uploaded audio, video, or extracted frames are retained on disk or stored in external databases. Ephemeral directories are strictly wiped immediately after request completion.
2. **Local AI Execution:** All AI inference runs locally in-process without transmitting data to third-party cloud APIs.
3. **Defensive Validation:** Strict limits on file size (100 MB max) and video duration (300 seconds max) protect against denial-of-service and memory exhaustion.
