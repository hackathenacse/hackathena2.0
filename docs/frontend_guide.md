# AUTHENTICA — Frontend Architecture & UI Guide

## 🎨 Design Philosophy & UX Architecture

The Authentica web application is engineered to make forensic AI outputs **immediately actionable and understandable for non-technical users**, avoiding opaque "black-box" confidence meters.

### Core User Flow
```
    UPLOAD                 ANALYSIS                 RESULTS                EVIDENCE               SAFE ACTION
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐       ┌────────────────┐       ┌──────────────┐
│ Drag & Drop │  ──>  │ Deterministic   │  ──>  │ Dual-Risk   │  ──>  │ Multi-Modal    │  ──>  │ Actionable   │
│ Video/Audio │       │ Real-Time Steps │       │ Directives  │       │ Timeline Tracks│       │ Safeguards   │
└─────────────┘       └─────────────────┘       └─────────────┘       └────────────────┘       └──────────────┘
```

---

## 🛠️ Technology Stack

- **Framework:** React 19 (Functional components, Hooks)
- **Language:** TypeScript 5.7 (Strict mode type definitions)
- **Build Tool:** Vite 8.3 (Fast HMR & optimized production bundling)
- **Styling:** Tailwind CSS 3.4 (Custom Cyber-Forensic theme, Glassmorphism gradients)
- **Iconography:** Lucide React (Forensic & security iconography)
- **Routing:** React Router v7 (Client-side routing with route state passing)

---

## 📁 Frontend Directory Structure

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── src/
│   ├── main.tsx                  # Application entry point
│   ├── App.tsx                   # Main router layout & navbar
│   ├── index.css                 # Custom glassmorphism classes & animations
│   ├── types/
│   │   └── analysis.ts           # Comprehensive TypeScript interfaces matching backend contracts
│   ├── services/
│   │   └── api.ts                # API client & local history storage manager
│   └── pages/
│       ├── AnalyzePage.tsx       # Media ingestion, dropzone & stage progress indicators
│       ├── ResultsPage.tsx       # Forensic dashboard, timeline, transcript & action plans
│       └── HistoryPage.tsx       # Local session analysis history & instant report recall
```

---

## 🧭 Application Pages & Key Features

### 1. Analyze Page (`/`)
- **Multi-Format Dropzone:** Accepts both video (`.mp4`, `.mov`, `.webm`, `.avi`, `.mkv`) and audio (`.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`, `.aac`, `.wma`).
- **Dynamic Format Badges & Media Icons:** Automatically changes UI cues (Video icon vs. Music icon) depending on selected file.
- **Deterministic Stage Progress Indicator:**
  - For **Video**: Frame sampling $\rightarrow$ Face detection $\rightarrow$ Visual model $\rightarrow$ Audio anti-spoofing $\rightarrow$ Whisper ASR $\rightarrow$ Fraud engine.
  - For **Audio**: Audio normalization $\rightarrow$ Audio anti-spoofing $\rightarrow$ Whisper ASR $\rightarrow$ Fraud engine (skips visual frames).

### 2. Forensic Results Page (`/results/:id`)
- **Action Recommendation Banner:** Prominent top-level banner (`STOP_AND_VERIFY`, `VERIFY`, `CAUTION`, `NO_ACTION_FLAGGED`).
- **Orthogonal Dual-Dimension Cards:**
  - Card 1: **Media Manipulation Risk** (`LIKELY_MANIPULATED`, `SUSPICIOUS`, `NO_STRONG_EVIDENCE`, `UNCERTAIN`)
  - Card 2: **Fraud Intent Risk** (`HIGH`, `MEDIUM`, `LOW`, `NOT_ASSESSABLE`)
- **Stage 2 Evidence Matrix:** 4-card forensic breakdown (Visual Forensics, Audio Anti-Spoof, C2PA Provenance, Reliability Gate).
- **Interactive Horizontal Multi-Track Timeline:**
  - Track 1: Visual Detections (Cleanly omitted for audio files)
  - Track 2: Audio Anti-Spoofing Windows (AASIST activations)
  - Track 3: High-Risk Fraud Intent Spans
  - Track 4: Spoken Transcript Segments
  - Clickable event drawer showing exact timestamps and activation scores.
- **Forensic Speech Transcript Inspector:**
  - Full transcript viewer with segment timestamps and highlighted extraction directives.
- **Detected Fraud Directives & Social-Engineering Tactics:** Visual callouts for extracted commands.
- **Grounded Explanations & Limitations:** Bulleted explanations linking verdicts to specific forensic indicators.
- **Actionable Safe Steps Protocol:** Clear instructions for out-of-band verification and incident reporting.
- **Export Capabilities:** One-click JSON report download and SHA-256 fingerprint clipboard copy.

### 3. Analysis History Page (`/history`)
- **Client-Side Storage:** Fast, private `localStorage` session caching.
- **Search & Filtering:** Real-time search across filenames, SHA-256 hashes, media types, and verdicts.
- **Type Badges:** Distinct visual tags for `VIDEO` vs `AUDIO` analyses.

---

## ⚡ Development & Build Commands

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start local development server (http://localhost:5173)
npm run dev

# Build for production (TypeScript check + Vite bundle)
npm run build

# Preview production build
npm run preview
```
