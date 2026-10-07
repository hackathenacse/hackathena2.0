# Authentica — Chrome Browser Extension (Manifest V3)

> **Quick Warning & Live Tab Media Forensic Scanner**  
> Hackathon Load-Unpacked Developer Build

The **Authentica Chrome Extension** is a focused, user-initiated security companion for the Authentica forensic platform. It enables users to capture an **8-second sample** of media currently playing in the active browser tab, stream it securely to the Authentica multi-modal forensic backend, and receive an immediate, actionable risk summary with a direct link to the full forensic evidence report.

---

## 🏗️ Architecture Overview

The extension strictly adheres to modern Chrome **Manifest V3** security standards:

```text
  [Active Tab (Media)] 
           │
           │ (User clicks "Scan Current Tab")
           ▼
    [Extension Popup]
           │
           ▼ (START_SCAN message)
  [Background Service Worker]
           │ 
           ├──> chrome.tabCapture.getMediaStreamId()
           ├──> Ensures Offscreen Document
           ▼
   [Offscreen Document]
           │
           ├──> navigator.mediaDevices.getUserMedia(streamId)
           ├──> AudioContext -> destination (Preserves tab audio playback)
           ├──> MediaRecorder (Supported WebM codecs: VP8/Opus)
           ├──> Records exactly 8 seconds (CAPTURE_DURATION_MS = 8000)
           ├──> Cleans up hardware streams & AudioContext
           ▼
   [POST /api/analyses] (Existing Authentica Backend Pipeline)
           │
           ├── Stage 1: Validation, Hashing, Sampling
           ├── Stage 2: EfficientNet, AASIST, Whisper, Reliability Gate
           └── Stage 3: Fraud Intent Engine, Timeline Synthesis, Action Assessment
           ▼
    [Risk Summary] ──> Popup Action Banner (STOP_AND_VERIFY / VERIFY / CAUTION / NO_ACTION)
           │
           └──> [Open Full Analysis] ──> Web App at http://localhost:5173/results/:id
```

---

## 📋 1. Prerequisites

Before installing the extension, ensure the Authentica backend and (optionally) the frontend are running:

* **Google Chrome**: Version 116 or newer (supports MV3 Offscreen documents and tabCapture stream IDs).
* **Authentica Backend**: Python 3.10+ FastAPI server running on `http://localhost:8000`.
  ```bash
  cd backend
  # From project virtual environment
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```
* **Authentica Web Frontend** (Optional for full report deep-link): Running on `http://localhost:5173`.
  ```bash
  cd frontend
  npm run dev
  ```

---

## 🛠️ 2. Build & Preparation

The extension is implemented using native modern ES modules and Web APIs directly supported by Chromium.

* **No complex bundling is required.**
* All icons (`16x16`, `32x32`, `48x48`, `128x128`), manifests, and module scripts are pre-packaged in the `extension/` directory.
* If you modify any TypeScript type definitions, ensure they conform to `shared/types.ts`.

---

## 💻 3. Chrome Installation Guide (Load Unpacked)

Follow these steps to load the extension in Google Chrome:

1. Open Google Chrome.
2. In the address bar, navigate to:
   ```text
   chrome://extensions
   ```
3. In the top-right corner of the Extensions page, toggle **Developer mode** to **ON**.
4. Click the **Load unpacked** button in the top-left toolbar.
5. In the file picker dialog, navigate to the project directory and select the **`extension`** folder:
   ```text
   E:\projects\My_projects\Authentica\extension
   ```
6. Click **Select Folder**.
7. The **Authentica — AI Media Protection** card will now appear in your extensions list.
8. Click the puzzle icon (Extensions menu) in Chrome's top-right toolbar and click the **Pin icon (📌)** next to Authentica for quick access.

---

## ⚙️ 4. Configuration

The extension comes pre-configured with default local development ports:

| Setting | Default Value | Description |
| :--- | :--- | :--- |
| **Backend API URL** | `http://localhost:8000` | Authentica FastAPI forensic server |
| **Web App URL** | `http://localhost:5173` | React/Vite forensic dashboard |

### Adjusting Server URLs:
1. Click the **Authentica** icon in your toolbar to open the popup.
2. Click the **Gear icon (⚙️)** in the top-right corner of the popup header.
3. Update the API Server or Web App URL.
4. Click **Test Server** to verify backend health (`/api/health`).
5. Click **Save**. Settings are persisted in Chrome local extension storage.

---

## 🧪 5. Controlled Demo Walkthrough

A dedicated verification laboratory with real video cases is provided in the repository:

### Step 1: Open the Demo Lab
Open the included demo page in Google Chrome:
```text
file:///E:/projects/My_projects/Authentica/demo/index.html
```
*(Or serve it via any local static server: `python -m http.server 3000 --directory demo`)*

### Step 2: Choose a Test Case
The demo page contains 3 pre-built scenarios:
1. **Case 1: Standard Demonstration** (`media/authentic_sample.mp4`) — Benign briefing speech.
2. **Case 2: Synthetic Artifacts** (`media/deepfake_sample.mp4`) — High-frequency visual test pattern.
3. **Case 3: Urgent CEO Wire Scam** (`media/scam_ceo_wire.mp4`) — Synthesized audio directing: *"This is the CEO speaking. We have an urgent acquisition deal. Transfer funds immediately to the new account number and keep this strictly confidential."*

### Step 3: Execute the Scan
1. Click **Play** on **Case 3 (Urgent CEO Wire Scam)**.
2. Click the **Authentica** extension icon in your Chrome toolbar.
3. Verify that the tab title shows `Authentica — Live Extension Verification Lab`.
4. Click the **Scan Current Tab** button.

### Step 4: Observe Real-time Behavior
* **Audio Playback Continues:** Notice that you can still hear the video audio through your speakers during capture (via the offscreen `AudioContext` routing).
* **Countdown:** The popup displays an 8-second countdown timer (`8s... 7s... 6s...`).
* **Upload & Analysis:** The extension uploads the secure WebM clip to `POST /api/analyses` and displays live progress indicators.

### Step 5: Review the Result
* The popup displays the prominent directive banner:
  - 🔴 **STOP AND VERIFY**
  - **Media Forensics:** `UNCERTAIN`
  - **Fraud Intent Risk:** `HIGH`
  - **Flagged Directive:** `TRANSFER_MONEY`
  - **Findings:** Highlights authority, urgency, and money extraction directives.
* Click **[ Open Full Analysis ]**:
  - Automatically opens `http://localhost:5173/results/<analysis_id>` in a new tab, showing the interactive timeline, audio spectrogram windows, speech transcript, and safety checklist.

---

## 🔒 6. Privacy & User Consent Model

* **No Background Spying:** The extension does **not** scan tabs automatically, run continuous loops, or observe pages silently.
* **Explicit User Trigger:** Recording only occurs when the user clicks **"Scan Current Tab"**.
* **Zero Clip Retention:** Captured video/audio blobs are streamed directly to the analysis endpoint in memory and discarded immediately upon completion. They are never saved to extension storage or persistent disk.
* **Minimal Manifest Permissions:**
  - `tabCapture`: To obtain the media stream ID for the active tab only.
  - `activeTab`: To inspect the currently focused tab on user request.
  - `offscreen`: To execute the audio routing and MediaRecorder in a dedicated sandbox.
  - `storage`: To persist user-configured API endpoints and display the latest scan summary.

---

## ⚠️ 7. Known Capture Limitations

1. **Internal Browser Pages (`chrome://`):** Chrome security policies prohibit extensions from capturing internal pages (`chrome://extensions`, `chrome://settings`, the Chrome Web Store, or `devtools://`). The popup clearly identifies these tabs as restricted and disables scanning.
2. **Hardware DRM Protected Media:** Widevine-protected streaming video (e.g., Netflix, Disney+, Spotify) uses hardware decryption pipelines that block `tabCapture` stream extraction by browser design.
3. **Silent Tabs:** If a tab has no audio playback, the extension automatically falls back to video-only capture and completes visual analysis gracefully.

---

## 🔧 8. Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **"Backend Offline" indicator in popup** | Backend server is not running on `localhost:8000` | Start the backend server (`uvicorn app.main:app --port 8000`) and test connection in the extension settings drawer. |
| **"Browser internal pages cannot be captured"** | You are on a `chrome://` or `about:` URL | Switch to a regular web page or open `demo/index.html`. |
| **"Uploaded file is empty (0 bytes)"** | Tab was paused or closed immediately after clicking scan | Ensure the video is playing before starting the scan. |
| **"Analysis Report Not Found" on web page** | Web app was not running or backend cache expired | Verify both backend and frontend are running. Results are cached in backend memory for recall. |
| **Extension popup closes during capture** | Clicking outside the popup dismisses it | The background service worker and offscreen recorder continue recording in the background! Reopening the popup instantly reconnects to the active countdown and result. |
