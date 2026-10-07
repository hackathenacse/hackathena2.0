# AUTHENTICA — REST API Reference Specification

## 🌐 Base URL & Endpoints Summary

- **Development Server:** `http://localhost:8000`
- **Protocol:** HTTP/1.1 (JSON responses, Multipart file uploads)
- **CORS:** Enabled for local frontend development (`http://localhost:5173`, `http://localhost:3000`)

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Service health, model status, and FFmpeg verification | Public |
| `POST` | `/api/analyses` | Upload video or audio file for multi-stage forensic analysis | Public |

---

## 1. Health Check Endpoint

### `GET /api/health`

Returns runtime service status, model availability, and underlying binary dependencies.

#### Response (`200 OK`)
```json
{
  "status": "ok",
  "version": "1.0.0",
  "ffmpeg_available": true,
  "ffprobe_available": true,
  "models": {
    "visual_detector": "EfficientNet-B0-FFPP-C23",
    "audio_detector": "AASIST-ASVspoof2019-LA",
    "speech_transcriber": "faster-whisper-base-int8",
    "c2pa": "c2pa-python-0.6.0"
  }
}
```

---

## 2. Media Analysis Endpoint

### `POST /api/analyses`

Ingests a video or standalone audio file, executes the complete Stage 1–4 forensic pipeline, and returns the comprehensive analysis report.

#### Request Headers
- `Content-Type: multipart/form-data`

#### Request Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `file` | `UploadFile` (Binary) | **Yes** | Video (`.mp4`, `.mov`, `.webm`, `.avi`, `.mkv`) or Audio (`.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`, `.aac`, `.wma`) file |

#### Constraints
- **Max File Size:** 100 MB (`104,857,600` bytes)
- **Max Media Duration:** 300.0 seconds
- **Minimum Duration:** 3.0 seconds (for full reliability gate pass)

---

### Response Schema (Video Input)

```json
{
  "id": "7b9e6a46-fb2f-498c-93f7-0a7730111b5c",
  "status": "completed",
  "created_at": "2026-10-06T12:00:00.000000+00:00",
  "input": {
    "media_type": "VIDEO"
  },
  "video": {
    "filename": "sample_video.mp4",
    "sha256": "33cab4d8a97f5226e5aa623684380ccb39f7795ad61040e653b7e1765906c118",
    "duration_s": 15.0,
    "fps": 30.0,
    "width": 1280,
    "height": 720,
    "frames_sampled": 15,
    "audio_available": true
  },
  "audio_metadata": null,
  "visual": {
    "available": true,
    "model": "EfficientNet-B0-FFPP-C23",
    "status": "completed",
    "frames_analyzed": 15,
    "faces_found": 15,
    "face_detection_rate": 1.0,
    "results": [
      {
        "timestamp_s": 0.0,
        "face_detected": true,
        "real_score": 0.0012,
        "fake_score": 0.9988
      }
    ]
  },
  "audio": {
    "available": true,
    "model": "AASIST-ASVspoof2019-LA",
    "status": "completed",
    "windows_analyzed": 6,
    "processing_time_s": 0.42,
    "results": [
      {
        "start_s": 0.0,
        "end_s": 4.0,
        "spoof_score": 0.9850
      }
    ]
  },
  "speech": {
    "available": true,
    "model": "faster-whisper-base-int8",
    "status": "completed",
    "language": "en",
    "processing_time_s": 0.85,
    "segments": [
      {
        "start_s": 0.5,
        "end_s": 4.2,
        "text": "This is an urgent call regarding your bank account. Transfer money now."
      }
    ]
  },
  "reliability": {
    "level": "OK",
    "reasons": []
  },
  "evidence": {
    "visual": {
      "level": "HIGH",
      "models": [
        {
          "name": "EfficientNet-B0-FFPP-C23",
          "score": 0.9988
        }
      ]
    },
    "audio": {
      "level": "HIGH",
      "models": [
        {
          "name": "AASIST-ASVspoof2019-LA",
          "score": 0.9850
        }
      ]
    },
    "provenance": {
      "state": "NONE_FOUND",
      "valid": null,
      "trusted": null,
      "signer": null,
      "note": "No C2PA manifest found in container."
    },
    "metadata": {
      "media_type": "VIDEO",
      "width": 1280,
      "height": 720,
      "duration_s": 15.0,
      "fps": 30.0,
      "frames_sampled": 15,
      "audio_available": true
    },
    "reliability": {
      "level": "OK",
      "reasons": []
    }
  },
  "timeline": [
    {
      "start_s": 0.0,
      "end_s": 15.0,
      "kind": "visual",
      "level": "HIGH",
      "evidence_source": "EfficientNet-B0 FaceForensics++ (15/15 frames)",
      "score": 0.9988
    },
    {
      "start_s": 0.0,
      "end_s": 15.0,
      "kind": "audio",
      "level": "HIGH",
      "evidence_source": "AASIST Voice Anti-Spoofing (6 windows)",
      "score": 0.9850
    },
    {
      "start_s": 0.5,
      "end_s": 4.2,
      "kind": "speech",
      "level": "INFO",
      "evidence_source": "Transcript: \"This is an urgent call regarding your bank account...\"",
      "score": null
    }
  ],
  "assessment": {
    "media": "LIKELY_MANIPULATED",
    "fraud": "HIGH",
    "action": "STOP_AND_VERIFY"
  },
  "explanation": [
    "Visual facial manipulation detection produced HIGH evidence of manipulation across 15/15 sampled frames.",
    "Audio anti-spoofing detector produced HIGH evidence of acoustic voice synthesis across 6 analyzed windows.",
    "Speech transcript analysis detected 2 high-risk extraction directives."
  ],
  "limitations": [
    "Raw model activations represent similarity to training distribution artifacts, not absolute mathematical proof of origin.",
    "Absence of C2PA provenance credentials does not necessarily indicate malicious tampering."
  ],
  "fraud": {
    "level": "HIGH",
    "categories": [
      {
        "category": "DIRECT_FINANCIAL_REQUEST",
        "severity": "HIGH",
        "evidence": [
          {
            "phrase": "transfer money now",
            "start_s": 2.1,
            "end_s": 4.2
          }
        ]
      }
    ],
    "requested_actions": [
      {
        "action": "WIRE_TRANSFER",
        "phrase": "transfer money now",
        "start_s": 2.1,
        "end_s": 4.2
      }
    ],
    "news_context_downgrade": false
  }
}
```

---

### Response Schema (Standalone Audio Input)

When an audio file (e.g. `.wav`, `.mp3`) is submitted, `input.media_type` is `"AUDIO"`, `video` is `null`, `audio_metadata` is populated, and `visual` is marked `not_applicable`:

```json
{
  "id": "c1f92e48-6789-4a92-9112-a1b2c3d4e5f6",
  "status": "completed",
  "created_at": "2026-10-06T12:05:00.000000+00:00",
  "input": {
    "media_type": "AUDIO"
  },
  "video": null,
  "audio_metadata": {
    "filename": "suspicious_voicemail.mp3",
    "sha256": "9b12a83c74de...",
    "duration_s": 12.4,
    "sample_rate_hz": 44100,
    "channels": 2,
    "codec": "mp3",
    "bitrate_kbps": 192,
    "mime_type": "audio/mpeg"
  },
  "visual": {
    "available": false,
    "model": null,
    "status": "not_applicable",
    "frames_analyzed": 0,
    "faces_found": 0,
    "face_detection_rate": null,
    "results": []
  },
  "audio": {
    "available": true,
    "model": "AASIST-ASVspoof2019-LA",
    "status": "completed",
    "windows_analyzed": 5,
    "processing_time_s": 0.35,
    "results": [ ... ]
  },
  "speech": {
    "available": true,
    "model": "faster-whisper-base-int8",
    "status": "completed",
    "language": "en",
    "processing_time_s": 0.62,
    "segments": [ ... ]
  },
  "evidence": {
    "visual": {
      "level": "N/A",
      "models": []
    },
    "audio": {
      "level": "HIGH",
      "models": [ { "name": "AASIST-ASVspoof2019-LA", "score": 0.9712 } ]
    },
    "provenance": { "state": "NONE_FOUND", ... },
    "metadata": {
      "media_type": "AUDIO",
      "duration_s": 12.4,
      "audio_available": true
    },
    "reliability": { "level": "OK", "reasons": [] }
  },
  "assessment": {
    "media": "LIKELY_MANIPULATED",
    "fraud": "HIGH",
    "action": "STOP_AND_VERIFY"
  },
  "explanation": [
    "Visual facial manipulation detection is not applicable for audio-only media.",
    "Audio anti-spoofing detector produced HIGH evidence of acoustic voice synthesis across 5 analyzed windows.",
    "Speech transcript analysis detected direct financial extraction directives."
  ]
}
```

---

## 3. Error Codes & Handling

| HTTP Code | Error Reason | Example Error Response |
| :---: | :--- | :--- |
| `400` | Unsupported file extension | `{"detail": "Unsupported file extension: .exe. Allowed extensions: .mp4, .mov, .wav, .mp3, ..."}` |
| `400` | Corrupted media container | `{"detail": "Unable to extract media metadata. File may be damaged or invalid."}` |
| `413` | File size exceeds limit | `{"detail": "File size (124.5 MB) exceeds maximum allowed limit (100.0 MB)."}` |
| `422` | Empty upload file | `{"detail": "Uploaded file is empty (0 bytes)."}` |
| `500` | Internal processing error | `{"detail": "Internal forensic analysis error occurred during processing."}` |

---

## 4. Example `curl` Commands

### Upload a Video File
```bash
curl -X POST "http://localhost:8000/api/analyses" \
  -H "Accept: application/json" \
  -F "file=@/path/to/suspect_video.mp4"
```

### Upload a Standalone Audio File
```bash
curl -X POST "http://localhost:8000/api/analyses" \
  -H "Accept: application/json" \
  -F "file=@/path/to/voice_recording.wav"
```

### Check Service Health
```bash
curl -X GET "http://localhost:8000/api/health"
```
