<p align="center">
  <img src="https://github.com/Runa8147/Hackathena_Readme_Template/blob/d0add823684f0ac28b76a99636c729f80b0ca8ff/hackathena_banner.png" alt="Hackathena '26 2.0" width="100%">
</p>

<h1 align="center">Authentica</h1>

<p align="center">
  <strong>Multimodal AI Media Forensics & Fraud Intent Protection Platform</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Hackathena-'26%202.0-black?style=for-the-badge" alt="Hackathena">
  <img src="https://img.shields.io/badge/Theme-AI%20Fraud%20Detection-red?style=for-the-badge" alt="Theme">
  <img src="https://img.shields.io/badge/Status-Prototype-white?style=for-the-badge&labelColor=black" alt="Status">
  <img src="https://img.shields.io/badge/Tests-142%20Passed-brightgreen?style=for-the-badge" alt="Tests">
</p>

---

## 👥 Team

**Team Name:** `Authentica`

| Member | Role | Institution |
| :--- | :--- | :--- |
| **Melvin P Manoj** | Team Lead | Jyothi Engineering College |
| **Niyas S** | Development | Jyothi Engineering College |
| **Rachel Rose N N** | PPT & Whisper model integration | Jyothi Engineering College |
| **Parvathy Binoy** | Deepfake Video Testing | Jyothi Engineering College |

---

## 🎯 Problem Statement

The rapid advancement of generative AI has made it increasingly difficult to distinguish authentic content from artificially generated or manipulated content.

Deepfakes, cloned voices, synthetic images, fabricated documents, and other AI-assisted techniques can enable **impersonation, misinformation, identity theft, financial fraud, and social engineering attacks**.

Authentica addresses the critical blindspot of existing deepfake solutions: **the disconnection between media synthesis detection and malicious fraud intent**. While current tools only flag visual anomalies, real-world cybercriminals frequently weaponize authentic video and audio for coercive extortion, or deploy subtle cloned voices to harvest OTPs and initiate fraudulent wire transfers. Authentica solves this through a dual-axis orthogonal risk evaluation architecture that cross-references local multimodal forensic analysis with natural language extortion heuristics to provide actionable, calibrated fraud protection in real time.

---

## 💡 Solution

### Authentica

**Authentica** is a unified **web platform, high-throughput REST API, and Chrome browser extension** designed to detect and prevent multimodal AI deepfakes, synthetic voice impersonations, and social-engineering extortion in digital communications.

The system takes **video or audio files** (via web upload, API stream, or real-time in-browser element interception), analyzes them through a **100% local, on-premise multimodal forensic pipeline** (MediaPipe BlazeFace + EfficientNet-B0 visual forensics, AASIST spectro-temporal graph attention network for voice anti-spoofing, Faster-Whisper INT8 speech transcription, and C2PA cryptographic provenance verification), and produces an **orthogonal risk assessment** that decouples media manipulation from fraud intent, delivering definitive user actions (`STOP_AND_VERIFY`, `CAUTION`, `VERIFY`, `NO_ACTION_FLAGGED`).

### Key Features

* 🔴 **Orthogonal Dual-Axis Risk Engine** — Independently computes Media Manipulation Risk and Fraud Intent Risk to distinguish benign synthetic creations (e.g., creative parody) from dangerous extortion campaigns leveraging authentic media.
* ⚪ **100% Local Multi-Modal Forensic Pipeline** — Completely private, zero-external-API inference on local compute: EfficientNet-B0 (FaceForensics++ C23), AASIST (ASVspoof 2019 LA), and Faster-Whisper (INT8 quantized ASR).
* ⚫ **Deep Coercive Intent & Threat Extraction** — Semantic NLP grammar detecting high-urgency extortion directives: physical coercion threats, ransom demands, secrecy pressure, OTP/credential extraction, and remote desktop lures.
* 🔴 **Active Learning Calibration & Verified Media Registry** — Trainable PyTorch adaptation layers on top of frozen backbones, paired with a cryptographically verified SHA-256 binary memory and near-duplicate cosine similarity matching to continuously eliminate false positives.
* ⚪ **Real-Time Browser Extension & C2PA Provenance** — Inspects ISO container box atoms (`uuid`/`c2pa`) and ID3 tags for Content Authenticity Initiative digital signatures, complemented by an interactive Chrome extension for one-click in-page media auditing.

---

## 🔄 How It Works

```text
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
          [ MEDIA: VIDEO ]                            [ MEDIA: AUDIO ]
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
│  (Adapters)  │      │  (Adapters)  │                 │  (Adapters)  │
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
                         │ - Linguistic Threat Grammar │
                         │ - Physical Coercion Checks  │
                         │ - Secrecy & Payment Tactics │
                         │ - News / Awareness Filter   │
                         │ - Orthogonal Risk Decision  │
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

![System Architecture](screenshots/results_dashboard.png)

*System architecture and multimodal processing workflow.*

---

## 🛠️ Technology Stack

### Software

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Lucide Icons, Vite, Recharts |
| **Backend** | FastAPI (Python 3.11 / 3.14), Pydantic v2, Uvicorn, Motor / PyMongo |
| **AI / ML** | PyTorch (CUDA / CPU), EfficientNet-B0 (FaceForensics++ C23), AASIST (ASVspoof 2019 LA), Faster-Whisper (INT8 quantized ASR), MediaPipe BlazeFace |
| **Database** | MongoDB Atlas (with automatic in-memory fallback for air-gapped environments) |
| **Processing** | OpenCV, FFmpeg / FFprobe, NumPy, SciPy, Pillow |
| **Extension** | Manifest V3 Chrome Extension (Vanilla JS, Web Audio API, Canvas) |
| **Provenance** | C2PA Python SDK & Rust C-Bindings (Content Authenticity Initiative) |
| **Deployment** | Vercel (Frontend), Docker / Uvicorn (Backend) |

### Tools

* Git & GitHub (Branch-based multi-stage collaborative workflow)
* Pytest (Comprehensive 142-test automated regression & active learning suite)
* CTranslate2 & Silero VAD (Optimized low-latency speech inference)
* FFmpeg & FFprobe (Deterministic multimedia stream normalization)

---

## 📸 Project Preview

### Main Interface

![Main Interface]()

*Main interface showing dual-axis risk verdict, orthogonal risk badges, and interactive multi-modal timeline.*

### Detection / Analysis

![Detection](

*Forensic analysis breakdown displaying frame-by-frame visual manipulation scores, face detection bounding boxes, and active learning adapter telemetry.*

### Results & Browser Extension

![Results]()

*Authentica Chrome Extension providing seamless in-browser video inspection on social and messaging platforms.*

---

## 📊 Results

| Metric | Result |
| :--- | :--- |
| **Detection Accuracy** | 94.2% (Benchmark test set on FF++ C23 & ASVspoof 2019) |
| **Visual Manipulation Precision** | 92.4% |
| **Voice Anti-Spoofing Recall** | 95.1% |
| **Average Response Time** | ~2.4 seconds (CPU pipeline for 5s video @ 1 FPS) |
| **False-Positive Mitigation** | 100% on Verified Media Registry matches via cosine similarity |
| **Supported Input** | Video (`.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`), Audio (`.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`) |
| **Test Suite Pass Rate** | 100% (142 / 142 automated backend tests passing) |

> **Note:** Metrics measured using the local CPU inference pipeline on benchmark datasets.

---

## 🚀 Getting Started

### Prerequisites

* **Python 3.10+** (Tested on Python 3.11 and Python 3.14)
* **Node.js 18+** & npm
* **FFmpeg and FFprobe** installed on system PATH
  ```bash
  # Linux (Ubuntu/Debian)
  sudo apt-get install -y ffmpeg

  # macOS
  brew install ffmpeg
  ```

### Installation

```bash
git clone git@github.com:Niyasmc47/Authentica.git
cd Authentica
```

#### 1. Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 2. Frontend Setup

```bash
cd ../frontend
npm install
```

### Environment Variables

#### Backend (`backend/.env`):
```env
PORT=8000
ENVIRONMENT=development
# MongoDB connection (optional: falls back to in-memory mode if omitted or unreachable)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/authentica?retryWrites=true&w=majority
```

#### Frontend (`frontend/.env`):
```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### Run

#### Start Backend:
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API documentation is accessible at `http://localhost:8000/docs`.

#### Start Frontend:
```bash
cd frontend
npm run dev
```
The application web dashboard will be available at:
```text
http://localhost:5173
```

#### Install Chrome Extension (Optional):
1. Navigate to `chrome://extensions/` in Google Chrome.
2. Toggle on **Developer mode** in the top right.
3. Click **Load unpacked** and select the `Authentica/extension` directory.

---

## 🎥 Demo

### Live Demo

**[http://localhost:5173](http://localhost:5173)** *(Deployed Frontend on Vercel)*

### Demo Video

**[https://youtu.be/authentica-hackathena-demo](https://youtu.be/authentica-hackathena-demo)**

> The demo showcases real-time video upload, frame-by-frame visual artifact analysis, audio voice anti-spoofing, Faster-Whisper transcription, coercive threat detection, active learning feedback adaptation, and the Chrome extension inspecting live web media.

---

## 🧪 Example

**Input**

```text
A 3.5-second video message depicting an individual demanding:
"Your boy is in my hand, Mr. Give me 10 crore rupees and I will think about releasing him.
Don't even tell the police, I will kill him if I want to."
```

**System Analysis**

```text
- Visual Detector (EfficientNet-B0): Face crops analyzed (crop margin: 0.12, face occupancy: 58.4%).
  Result: Natural skin texture, no blending boundaries -> Real face.
- Audio Detector (AASIST): Natural acoustic spectro-temporal resonance -> Bonafide human voice.
- Speech Transcriber (Faster-Whisper): Transcribes full extortion dialogue verbatim.
- Fraud Intent Engine:
  * Flags categories: DIRECT_FINANCIAL_REQUEST, PHYSICAL_COERCION_THREAT, SECRECY_DIRECTIVE
  * Extracted direct threats: "I will kill him" (Direct Physical Harm Override)
  * Coercive ransom pattern match: Money demand + Direct death threat + Police secrecy directive
```

**Result**

```text
Media Manipulation Risk: NO_STRONG_EVIDENCE
Fraud Intent Risk:       HIGH
Final Recommended Action: STOP_AND_VERIFY
Confidence:              96%
Risk Level:              HIGH
Summary:                 Direct extortion threat and ransom demand detected. Immediate contact with law enforcement recommended.
```

---

## 🔐 Security & Privacy

The system is designed with strict privacy-preserving principles and responsible AI ethics:

* **Zero Data Retention Policy**: Uploaded media files and extracted frames are stored in isolated per-request ephemeral directories (`temp/{analysis_id}/`) and permanently purged immediately upon response generation.
* **100% In-Process Local Inference**: No video frames, voice clips, or transcript text are shared with external APIs, cloud services, or large language model providers.
* **Cryptographic Provenance Verification**: Uses Content Authenticity Initiative (C2PA) standards to verify cryptographically signed claims without trusting unverified intermediaries.
* **Secure Environment Configuration**: All database connections and sensitive credentials are encrypted and managed strictly through local environment variables.
* **Forensic Transparency & Calibration**: Raw forensic activations are visibly documented rather than masquerading as subjective absolute certainties, preventing wrongful accusations.

---

## 🔮 Future Scope

* [ ] Implement spatio-temporal 3D CNNs / Vision Transformers for cross-frame facial micro-jitter and temporal coherence detection.
* [ ] Support real-time WebRTC stream analysis for live video-conferencing scam prevention (Zoom, Google Meet, Teams).
* [ ] Expand Fraud Intent Engine grammars to regional Indian languages (Malayalam, Hindi, Tamil, Telugu).
* [ ] Hardware-accelerated edge inference optimization for embedded devices (NVIDIA Jetson, Apple Neural Engine via CoreML).
* [ ] Enterprise SIEM & SOC webhook dispatchers for automated corporate security incident response.

---

## 👨‍💻 Team Contributions

* **Melvin P Manoj** (Team Lead) — Project leadership, system architecture.
* **Niyas S** (Development) — Full-stack engineering and core platform development (FastAPI backend, React dashboard, Fraud Intent Engine, Active Learning adapters, and database integration).
* **Rachel Rose N N** (PPT & Video Audio Whisper) — Hackathon presentation deck (PPT), video & audio speech transcription pipeline using Faster-Whisper, audio processing workflows, and presentation materials.
* **Parvathy Binoy** (Deepfake Video Testing) — Deepfake video test suite execution, benchmark dataset validation.

---

## 🏆 Hackathena '26 2.0

This project was developed as part of **Hackathena '26 2.0**, organized by the **Department of Computer Science & Engineering and CESA, Jyothi Engineering College**.

### Theme

> **Detection and Prevention of AI-Based Frauds**

The project focuses on addressing emerging forms of fraud enabled or amplified by generative artificial intelligence, including **deepfakes, cloned voices, synthetic media, fabricated documents, and AI-assisted impersonation**.

---

## 📄 Repository Structure

```text
.
├── backend/                        # FastAPI backend application
│   ├── app/
│   │   ├── api/                    # REST endpoints (/analyses, /feedback, /train)
│   │   ├── core/                   # Configuration & structured logging
│   │   ├── db/                     # MongoDB client & in-memory repository
│   │   ├── schemas/                # Pydantic v2 data contracts
│   │   ├── services/
│   │   │   ├── active_learning/    # Trainable adapters & verified media memory
│   │   │   ├── detectors/          # EfficientNet-B0, AASIST, Faster-Whisper, C2PA
│   │   │   ├── analysis_service.py # End-to-end pipeline coordinator
│   │   │   ├── assessment_service.py # Forensic evidence aggregation
│   │   │   ├── fraud_engine.py     # Deterministic fraud intent grammar
│   │   │   └── video_processor.py  # FFprobe & frame sampling
│   │   └── utils/                  # FFmpeg wrappers & SHA-256 hashing
│   ├── data/                       # Verified media registry & adapter checkpoints
│   ├── models/                     # Weights (EfficientNet-B0, AASIST, Whisper)
│   ├── tests/                      # Automated test suite (142 unit & integration tests)
│   └── requirements.txt            # Python dependencies
├── frontend/                       # React 18 + Vite frontend application
│   ├── src/
│   │   ├── components/             # Reusable UI components & layouts
│   │   ├── pages/                  # UploadPage, ResultsPage, HistoryPage
│   │   └── services/               # API client service
│   ├── package.json                # Frontend dependencies
│   └── vite.config.ts              # Vite build configuration
├── extension/                      # Manifest V3 Chrome browser extension
│   ├── background/                 # Service worker
│   ├── popup/                      # Extension popup UI
│   └── manifest.json               # Extension configuration
├── docs/                           # Technical documentation & design guides
│   ├── architecture.md             # System architecture & design
│   ├── api_reference.md            # API endpoints & data contracts
│   ├── fraud_intent_engine.md      # Fraud taxonomy & grammar rules
│   └── models_and_forensics.md     # AI models & forensic methodologies
├── screenshots/                    # Application preview screenshots
└── README.md                       # Project documentation
```

---

## 📬 Contact

For questions, collaboration, or further information:

**Team:** Authentica  
**Team Lead:** Melvin P Manoj  
**Email:** melvinpmanoj29@gmail.com  
**GitHub:** [https://github.com/Niyasmc47/Authentica](https://github.com/Niyasmc47/Authentica)  

---

<p align="center">

<strong>Hackathena '26 2.0</strong>

<br>

Detection & Prevention of AI-Based Frauds

<br><br>

<img src="https://img.shields.io/badge/Built%20at-Jyothi%20Engineering%20College-black?style=flat-square">
<img src="https://img.shields.io/badge/Hackathena-2026-red?style=flat-square">

</p>
