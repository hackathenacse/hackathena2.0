# Authentica — Backend System Foundation (Stage 1)

> **Hackathena '26 2.0 Project**  
> **Theme:** Detection and Prevention of AI-Based Frauds  
> **Module:** Stage 1 Core Backend & Media Preprocessing Pipeline  
> **Lead Developer (Stage 1):** Member 1 (System Foundation & Ingestion Engine)

---

## 📌 Overview

This backend is the system foundation for **Authentica**, an AI-based fraud and deepfake detection platform. 

In **Stage 1**, this service provides:
1. High-throughput video ingestion and safe multipart streaming.
2. File validation (MIME types, allowed extensions, maximum duration, maximum file size).
3. Cryptographic media fingerprinting (**SHA-256**) for integrity and duplicate prevention.
4. Robust local media inspection and frame sampling (~1 FPS) using **OpenCV** and **FFmpeg/FFprobe**.
5. Safe audio stream extraction (16kHz mono WAV) for downstream speech & voice analysis.
6. Unified **Stage 1 Shared Data Contract** with modular interfaces for **Member 2** (Visual AI Detector) and **Member 3** (Audio Spoofing & Speech Transcriber).
7. Strict ephemeral processing with **Zero Data Retention** (temporary workspaces are completely deleted immediately upon request completion).

---

## 🏗️ Stage 1 Architecture & Pipeline

```
               [ User / Client ]
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
           │  SHA-256 Fingerprint  │ (hashlib streaming)
           └───────────┬───────────┘
                       ▼
           ┌───────────────────────┐
           │  Video Preprocessing  │
           │ (OpenCV + FFprobe)    │ (Duration, FPS, Resolution, Audio check)
           └───────────┬───────────┘
                       ▼
           ┌───────────────────────┐
           │  Frame Sampling (1fps)│ (Sampled frames saved to temp/frames/)
           └───────────┬───────────┘
                       ▼
           ┌───────────────────────┐
           │   Audio Extraction    │ (FFmpeg -> 16kHz mono PCM WAV)
           └───────────┬───────────┘
                       ▼
      ┌─────────────────────────────────┐
      │  Pluggable AI Model Interfaces  │
      ├────────────────┬────────────────┤
      │    Member 2    │    Member 3    │
      │ VisualDetector │ Audio / Speech │
      │ (Placeholder)  │ (Placeholder)  │
      └────────────────┴────────────────┘
                       ▼
           ┌───────────────────────┐
           │   Response Assembly   │
           └───────────┬───────────┘
                       ▼
           ┌───────────────────────┐
           │   Workspace Cleanup   │ (shutil.rmtree -> Zero Retention)
           └───────────┬───────────┘
                       ▼
             [ JSON Response ]
```

---

## 🧩 Team Member Integration Guide

### 👁️ Member 2: Visual AI Deepfake Detector (Stage 1 Implemented)
Implemented in: 📁 `app/services/detectors/visual_detector.py`

- **Model Name:** `EfficientNet-B0-FFPP-C23`
- **Source / Repository:** [Xicor9/efficientnet-b0-ffpp-c23](https://huggingface.co/Xicor9/efficientnet-b0-ffpp-c23)
- **License:** MIT License
- **Face Detector:** Google MediaPipe FaceDetector (`blaze_face_short_range.tflite`)
- **Device Support:** Auto-selects CUDA when available; automatically falls back to CPU.
- **Expected Input:** Video frame samples at ~1 FPS. MediaPipe locates faces, selects the primary face by maximum bounding box area, applies a 10% safety margin, and extracts RGB face crops.
- **Preprocessing:** Resizes face crops to (224, 224), converts to PyTorch tensor in range [0.0, 1.0].
- **Output Interpretation:**
  - `real_score`: Softmax probability score for Class 0 (Real/Authentic)
  - `fake_score`: Softmax probability score for Class 1 (Fake/Manipulated)
  - Missing faces or unreadable frames return `face_detected: false`, `real_score: null`, `fake_score: null` without crashing.

> ⚠️ **FORENSIC DISCLAIMER:**  
> *Authenitca uses a pretrained research model as one forensic signal. Its output is not a calibrated probability and does not by itself establish that media is fake.*  
> The visual detector provides evidence of facial manipulation/deepfake-style artifacts represented in its training dataset (FaceForensics++ C23: DeepFake, FaceSwap, Face2Face, NeuralTextures). Raw forensic scores are forwarded downstream for multi-modal evidence fusion.

```python
from app.services.detectors.visual_detector import VisualDeepfakeDetector

# Singleton access
detector = VisualDeepfakeDetector.get_instance()
# analyze(frames, video_info) returns VisualResult
```

### 🎙️ Member 3: Audio AI Anti-Spoofing & Speech-to-Text (Stage 1 Implemented)
Implemented in: 
- 📁 `app/services/detectors/audio_detector.py`
- 📁 `app/services/detectors/speech_transcriber.py`

#### 1. Audio AI Anti-Spoofing Detector
- **Model Name:** `AASIST-ASVspoof2019-LA`
- **Source / Repository:** [Clova AI AASIST](https://github.com/clovaai/aasist)
- **License:** BSD-3-Clause License
- **Architecture:** SincNet raw waveform filterbank front-end -> 6 High-Frequency Residual Blocks with MaxFeatureMap -> Integrated Spectro-Temporal Graph Attention Network (GAT) -> Graph Pooling -> 2-class Readout Head (Bonafide vs. Spoof).
- **Input Requirements:** 16 kHz mono raw audio waveform.
- **Windowing Strategy:** Sliding window analysis with ~4.0-second windows (64,000 samples @ 16kHz) and ~2.0-second stride (32,000 samples). Audio shorter than 4s is padded/tiled to 64,600 samples.
- **Output Interpretation:**
  - `spoof_score`: Softmax probability score for Class 1 (Synthetic / Spoofed / AI Voice Clone).
  - Window timestamps: `start_s` and `end_s`.
- **Known Limitations & Forensic Honesty:**
  - Pretrained on the ASVspoof 2019 Logical Access (LA) benchmark.
  - Highly compressed audio (e.g. repeated WhatsApp/telephony transcodings) or heavy environmental background noise can introduce variance.
  - Scores are raw forensic model outputs representing acoustic synthesis artifacts, not absolute proof.

#### 2. Speech-to-Text Transcription
- **Model Name:** `faster-whisper-base-int8`
- **Source / Repository:** [Systran/faster-whisper](https://github.com/SYSTRAN/faster-whisper) (OpenAI Whisper architecture via CTranslate2)
- **License:** MIT License
- **Configuration:** `base` model running on CPU INT8 quantization (with automatic CUDA GPU acceleration if available).
- **Features:** Automatic language identification (multilingual), Silero Voice Activity Detection (VAD) filtering to skip non-speech/silence, and segment timestamps (`start_s`, `end_s`, `text`).
- **Clarification:** Whisper is an Automatic Speech Recognition (ASR) engine to establish *"What was said and when"*. Fraud intent heuristics belong to subsequent pipeline stages.

```python
from app.services.detectors.audio_detector import LocalAudioAntiSpoofDetector
from app.services.detectors.speech_transcriber import FasterWhisperTranscriber

# Singleton access
audio_detector = LocalAudioAntiSpoofDetector.get_instance()
speech_transcriber = FasterWhisperTranscriber.get_instance()
```

---

## 📋 What is Implemented vs Intentionally Deferred

| Feature | Status | Responsible |
| :--- | :--- | :--- |
| **FastAPI REST Application & Health Check** | ✅ Implemented | Member 1 |
| **Video Ingestion & Multipart Validation** | ✅ Implemented | Member 1 |
| **SHA-256 Media Hashing** | ✅ Implemented | Member 1 |
| **OpenCV Frame Sampling (~1 FPS)** | ✅ Implemented | Member 1 |
| **FFmpeg Media Inspection & 16kHz Audio Extraction** | ✅ Implemented | Member 1 |
| **Ephemeral Privacy & Cleanup Manager** | ✅ Implemented | Member 1 |
| **Shared Pydantic Data Contracts** | ✅ Implemented | Member 1 |
| **MediaPipe Face Detection & Face Cropping** | ✅ Implemented | Member 2 |
| **EfficientNet-B0 FF++ C23 Deepfake Detector** | ✅ Implemented | Member 2 |
| **Batched Visual Inference & CUDA/CPU Auto-Fallback** | ✅ Implemented | Member 2 |
| **Local Audio Anti-Spoofing AI Model (AASIST)** | ✅ Implemented | Member 3 |
| **Sliding Window Audio Spoof Analysis (~4s window, 2s stride)** | ✅ Implemented | Member 3 |
| **Faster-Whisper Speech-to-Text & Language Detection** | ✅ Implemented | Member 3 |
| **Automated Pytest Suite (31 tests)** | ✅ Implemented | Team (All Passing) |
| **Timeline Fusion / Aggregated Fraud Risk Score** | ⏳ Stage 2/3 Integration | Team |
| **Fraud Intent & Keyword Heuristics (OTP/Transfers)** | ⏳ Stage 2 Integration | Team |
| **C2PA Metadata Verification** | ⏳ Stage 2 Integration | Team |
| **Frontend UI / React Dashboard** | ⏳ Later Stage | Member 2 |


> ⚠️ **IMPORTANT:** In Stage 1, detector interfaces return explicit `status: "unavailable"` and `available: false`. **No fake or fabricated AI detection scores are generated.**

---

## 🚀 Getting Started

### 1. Prerequisites

- **Python 3.10+** (Tested on Python 3.10 - 3.14)
- **FFmpeg & FFprobe** installed on system `PATH`

#### Installing FFmpeg:
- **Ubuntu/Debian:**
  ```bash
  sudo apt-get update && sudo apt-get install -y ffmpeg
  ```
- **macOS (Homebrew):**
  ```bash
  brew install ffmpeg
  ```
- **Fedora/RHEL:**
  ```bash
  sudo dnf install -y ffmpeg ffmpeg-free-devel
  ```
- **Windows (Chocolatey/Winget):**
  ```powershell
  winget install Gyan.FFmpeg
  ```

### 2. Create Virtual Environment & Install Dependencies

From the repository root or `backend/` directory:

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# Linux/macOS:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file (or copy `.env.example`):

```bash
cp .env.example .env
```

Default configurable parameters:
```env
MAX_FILE_SIZE_MB=100
MAX_DURATION_SECONDS=90.0
FRAME_SAMPLE_FPS=1.0
LOG_LEVEL=INFO
```

### 4. Run the Development Server

From inside the `backend/` directory:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will be available at:
- **API Base:** `http://localhost:8000`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **Alternative ReDoc Docs:** `http://localhost:8000/redoc`

---

## 🧪 Running Automated Tests

Run the test suite using `pytest`:

```bash
# Run all tests
pytest tests/ -v

# Run with output logging
pytest tests/ -v -s
```

---

## 📡 API Reference

### 1. Health Check
`GET /api/health`

**Sample Response:**
```json
{
  "status": "ok",
  "ffmpeg_available": true,
  "ffprobe_available": true,
  "version": "1.0.0"
}
```

---

### 2. Video Analysis Upload
`POST /api/analyses`

- **Content-Type:** `multipart/form-data`
- **Body Parameter:** `file` (Video file: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`)
- **Limits:** Max 100 MB, Max 90 seconds duration

**Sample `curl` command:**
```bash
curl -X POST "http://localhost:8000/api/analyses" \
  -H "accept: application/json" \
  -F "file=@/path/to/sample_video.mp4;type=video/mp4"
```

**Sample Response (Stage 1):**
```json
{
  "id": "e4b6c31a-637d-41a4-9e87-5c4e47cf793a",
  "status": "completed",
  "created_at": "2026-10-05T12:15:30.123456+00:00",
  "video": {
    "filename": "sample_video.mp4",
    "sha256": "4a5e2f7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f",
    "duration_s": 15.0,
    "fps": 30.0,
    "width": 1920,
    "height": 1080,
    "frames_sampled": 15,
    "audio_available": true
  },
  "visual": {
    "available": true,
    "model": "EfficientNet-B0-FFPP-C23",
    "status": "completed",
    "frames_analyzed": 15,
    "faces_found": 14,
    "face_detection_rate": 0.9333,
    "results": [
      {
        "timestamp_s": 0.0,
        "face_detected": true,
        "real_score": 0.9124,
        "fake_score": 0.0876
      },
      {
        "timestamp_s": 1.0,
        "face_detected": true,
        "real_score": 0.8841,
        "fake_score": 0.1159
      }
    ]
  },
  "audio": {
    "available": true,
    "model": "AASIST-ASVspoof2019-LA",
    "status": "completed",
    "windows_analyzed": 6,
    "processing_time_s": 0.45,
    "results": [
      {
        "start_s": 0.0,
        "end_s": 4.0,
        "spoof_score": 0.1245
      },
      {
        "start_s": 2.0,
        "end_s": 6.0,
        "spoof_score": 0.0982
      }
    ]
  },
  "speech": {
    "available": true,
    "model": "faster-whisper-base-int8",
    "status": "completed",
    "language": "en",
    "processing_time_s": 0.38,
    "segments": [
      {
        "start_s": 0.5,
        "end_s": 3.2,
        "text": "Hello, this is an authentic local voice sample."
      }
    ]
  }
}
```

---

## 🔒 Privacy & Local Processing Principles

1. **Local-Only Inference:** Media processing, decoding, frame sampling, and subsequent AI model evaluations run entirely within the local execution environment.
2. **No Paid/Cloud APIs:** Zero data sent to Gemini, OpenAI, Claude, or third-party cloud APIs.
3. **Strict Zero Retention:** Uploaded videos, sampled frame images (`.jpg`), and extracted audio clips (`.wav`) reside exclusively in ephemeral subdirectories (`temp/{analysis_id}/`) and are purged immediately after response delivery.
