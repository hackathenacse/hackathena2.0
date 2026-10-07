# AUTHENTICA — AI Models & Forensic Methodologies

## 🧠 Local AI Model Inventory

Authentica executes **100% of its AI model inference locally in-process**. No media files, extracted features, or transcripts are sent to third-party cloud APIs.

| Modality | Model Identifier | Architecture / Source | Device / Format | License |
| :--- | :--- | :--- | :--- | :--- |
| **Face Detection** | `blaze_face_short_range.tflite` | MediaPipe BlazeFace Short Range | CPU (TensorFlow Lite) | Apache 2.0 |
| **Visual Manipulation** | `EfficientNet-B0-FFPP-C23` | [Xicor9/efficientnet-b0-ffpp-c23](https://huggingface.co/Xicor9/efficientnet-b0-ffpp-c23) | PyTorch (CUDA / CPU) | MIT |
| **Voice Anti-Spoofing** | `AASIST-ASVspoof2019-LA` | [Clova AI AASIST](https://github.com/clovaai/aasist) | PyTorch (CUDA / CPU) | BSD-3-Clause |
| **Speech-to-Text** | `faster-whisper-base-int8` | [Systran/faster-whisper](https://github.com/SYSTRAN/faster-whisper) (OpenAI Whisper) | CTranslate2 INT8 | MIT |
| **Provenance** | `c2pa-python 0.6.0` | Content Authenticity Initiative | Native Rust C-Bindings | Apache 2.0 / MIT |

---

## 1. Visual Deepfake Detection Subsystem

### MediaPipe BlazeFace Face Extraction
- **Objective:** Identify and crop primary facial regions from sampled video frames (~1 FPS).
- **Selection Strategy:** When multiple faces appear in a frame, the primary subject is determined by maximum bounding box area ($\text{Width} \times \text{Height}$).
- **Safety Margin:** A $10\%$ outward padding is applied to ensure facial boundaries, chin lines, and forehead compression artifacts are captured.
- **Resizing:** Cropped face tensors are normalized and resized to $224 \times 224$ RGB.

### EfficientNet-B0 FaceForensics++ Classifier
- **Training Corpus:** FaceForensics++ (FF++) benchmark dataset with C23 compression across four manipulation techniques:
  1. *Deepfakes* (Autoencoder-based facial replacement)
  2. *FaceSwap* (Graphics-based face swapping)
  3. *Face2Face* (Facial reenactment and expression transfer)
  4. *NeuralTextures* (Neural rendering modification of mouth interiors)
- **Output Polarity:**
  - `Class 0`: Real / Authentic
  - `Class 1`: Synthetic / Manipulated
  - `real_score` $= \text{Softmax}(z)_0$
  - `fake_score` $= \text{Softmax}(z)_1$
- **Calibration & Multi-Frame Persistence:**
  - A single noisy frame with a high activation is insufficient to declare a video manipulated.
  - `HIGH` evidence requires sustained high activations across multiple consecutive frames or $\ge 50\%$ of evaluated face crops.

---

## 2. Voice Anti-Spoofing Subsystem (AASIST)

### Architecture
- **Model:** AASIST (Audio Anti-Spoofing using Integrated Spectro-Temporal Graph Attention Networks).
- **Front-End:** SincNet raw waveform filterbank (learnable band-pass filters operating directly on 16kHz PCM audio).
- **Backbone:** 6 High-Frequency Residual blocks with Max-Feature-Map (MFM) activations.
- **Graph Attention:** Heterogeneous graph module with Spectral Graph Attention Network (S-GAT) and Temporal Graph Attention Network (T-GAT).
- **Readout Head:** 2-class classifier outputting raw logits for Bonafide (Real) vs. Spoof (Synthetic).

### Sliding Window Strategy
- **Window Size:** $4.0\text{ seconds}$ ($64,000\text{ samples}$ at $16\text{ kHz}$).
- **Stride:** $2.0\text{ seconds}$ ($32,000\text{ samples}$).
- **Short Audio Handling:** Audio shorter than 4 seconds is cyclically tiled/padded to 64,600 samples for inference.
- **Score Mapping:**
  - Softmax applied across logits:
    $$\text{spoof\_score} = \frac{e^{z_{\text{spoof}}}}{e^{z_{\text{bonafide}}} + e^{z_{\text{spoof}}}}$$
  - Scores $\ge 0.70$ represent significant acoustic synthesis artifacts.

---

## 3. Automatic Speech Recognition (Faster-Whisper)

- **Engine:** CTranslate2-optimized implementation of OpenAI Whisper Base model.
- **Quantization:** INT8 CPU execution for low memory footprint ($\approx 150\text{ MB}$) and fast real-time factor ($<0.1\times$).
- **Silero VAD:** Filters non-vocal audio segments and background noise to avoid hallucinated speech.
- **Transcription Output:** Produces timestamped segments containing `start_s`, `end_s`, and verbatim text used by the Stage 3 Fraud Intent Engine.

---

## 4. C2PA Provenance & Cryptographic Metadata

- **Standard:** Coalition for Content Provenance and Authenticity (C2PA) / Content Authenticity Initiative (CAI).
- **Manifest Extraction:** Probes MP4/MOV ISO box atoms (`uuid` / `c2pa`) and audio ID3 metadata tags for embedded cryptographic manifests.
- **Validation:**
  - `FOUND` + `valid: true`: Cryptographically signed manifest verified against root trust store.
  - `NONE_FOUND`: No manifest present in container.
  - **Important Principle:** *Absence of provenance credentials is standard for non-C2PA cameras and does NOT imply malicious manipulation.*

---

## 5. Forensic Calibration & Honesty Principles

1. **Activations, Not Probabilities:** Model outputs indicate statistical similarity to known training benchmarks (FaceForensics++, ASVspoof), not universal mathematical certainty.
2. **Quality Gate Preconditions:** Degraded resolution ($<200\times 200$), low face coverage ($<30\%$), or clipped audio ($<3.0\text{s}$) trigger the **Reliability Gate**, marking results `LOW` reliability rather than risking false positives.
3. **Multi-Modal Triangulation:** High confidence is achieved through cross-modal agreement (visual artifacts + acoustic anomalies + social engineering directives).
