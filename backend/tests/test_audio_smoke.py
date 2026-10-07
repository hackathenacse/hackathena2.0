import math
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
import torch

from app.schemas.analysis import VideoInfo
from app.services.detectors.audio_detector import (
    LocalAudioAntiSpoofDetector,
    TARGET_SAMPLE_RATE,
)
from app.services.evidence_service import EvidenceService


@pytest.fixture(scope="module")
def audio_detector():
    """Module-level detector loaded once."""
    detector = LocalAudioAntiSpoofDetector(device="cpu")
    detector.load()
    return detector


@pytest.fixture
def dummy_video_info():
    return VideoInfo(
        filename="smoke_test.mp4",
        sha256="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        duration_s=4.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=4,
        audio_available=True,
    )


def generate_speech_like_signal(duration_s: float = 4.0, f0: float = 140.0, sr: int = TARGET_SAMPLE_RATE) -> np.ndarray:
    """Generates synthetic speech-like harmonic signal with glottal pulse envelope."""
    total_samples = int(sr * duration_s)
    t = np.linspace(0, duration_s, total_samples, endpoint=False, dtype=np.float32)
    # Fundamental + 3 harmonics + syllabic modulation (~3Hz)
    syllables = 0.5 + 0.5 * np.sin(2 * np.pi * 3.5 * t)
    sig = (
        0.5 * np.sin(2 * np.pi * f0 * t) +
        0.25 * np.sin(2 * np.pi * 2 * f0 * t) +
        0.15 * np.sin(2 * np.pi * 3 * f0 * t) +
        0.10 * np.sin(2 * np.pi * 4 * f0 * t)
    ) * syllables
    return sig.astype(np.float32)


# 20 Acoustic & Codec Variety Generators
def generate_variety(variety_name: str, duration_s: float = 4.0, sr: int = TARGET_SAMPLE_RATE) -> np.ndarray:
    base = generate_speech_like_signal(duration_s, f0=150.0, sr=sr)
    t = np.linspace(0, duration_s, len(base), endpoint=False, dtype=np.float32)

    if variety_name == "clean_speech":
        return 0.5 * base

    elif variety_name == "quiet_speech":
        # Low energy (-35 dBFS approx)
        return 0.03 * base

    elif variety_name == "loud_speech":
        # Near 0 dBFS without clipping
        return 0.95 * (base / (np.max(np.abs(base)) + 1e-6))

    elif variety_name == "telephone_8khz":
        # Brickwall telephone passband (300 - 3400 Hz) + downsampled feel
        fft = np.fft.rfft(base)
        freqs = np.fft.rfftfreq(len(base), 1.0 / sr)
        fft[(freqs < 300) | (freqs > 3400)] = 0.0
        filtered = np.fft.irfft(fft, n=len(base))
        return 0.5 * filtered

    elif variety_name == "heavy_compression":
        # Non-linear dynamic compression (tanh soft clip)
        return np.tanh(3.0 * base) * 0.5

    elif variety_name == "low_bitrate":
        # Lowpass at 3 kHz + quantization noise
        fft = np.fft.rfft(base)
        freqs = np.fft.rfftfreq(len(base), 1.0 / sr)
        fft[freqs > 3000] = 0.0
        filtered = np.fft.irfft(fft, n=len(base))
        quantized = np.round(filtered * 32.0) / 32.0
        return 0.5 * quantized

    elif variety_name == "clipping":
        # Harsh digital clipping
        return np.clip(2.5 * base, -0.4, 0.4)

    elif variety_name == "light_reverb":
        # Single echo tap at 50ms
        delay_samples = int(sr * 0.05)
        out = np.copy(base)
        out[delay_samples:] += 0.3 * base[:-delay_samples]
        return 0.5 * out

    elif variety_name == "background_fan_white_noise":
        # Add white noise with SNR ~15 dB
        noise = np.random.normal(0, 0.03, size=len(base)).astype(np.float32)
        return 0.5 * base + noise

    elif variety_name == "room_reverb":
        # Multi-tap early reflections
        out = np.copy(base)
        for delay_s, gain in [(0.025, 0.35), (0.060, 0.25), (0.110, 0.15)]:
            d_samples = int(sr * delay_s)
            out[d_samples:] += gain * base[:-d_samples]
        return 0.4 * out

    elif variety_name == "packet_loss_dropouts":
        # Periodic 60ms zero-out dropout every 800ms
        out = np.copy(base)
        dropout_len = int(sr * 0.06)
        period = int(sr * 0.8)
        for start in range(period // 2, len(out) - dropout_len, period):
            out[start:start + dropout_len] = 0.0
        return 0.5 * out

    elif variety_name == "microphone_distance":
        # Attenuated high frequencies + lower amplitude
        fft = np.fft.rfft(base)
        freqs = np.fft.rfftfreq(len(base), 1.0 / sr)
        # 1/f decay
        envelope = 1.0 / (1.0 + freqs / 1000.0)
        fft *= envelope
        filtered = np.fft.irfft(fft, n=len(base))
        return 0.15 * filtered

    elif variety_name == "highpass_lowpass_filtered":
        # Bandpass 500 Hz to 2500 Hz
        fft = np.fft.rfft(base)
        freqs = np.fft.rfftfreq(len(base), 1.0 / sr)
        fft[(freqs < 500) | (freqs > 2500)] = 0.0
        return 0.5 * np.fft.irfft(fft, n=len(base))

    elif variety_name == "pitch_variation":
        # Frequency modulated fundamental (vibrato / pitch sweep 120Hz -> 240Hz)
        phase = 2 * np.pi * (140.0 * t + 40.0 * np.sin(2 * np.pi * 2.0 * t))
        sweep = 0.5 * np.sin(phase) + 0.25 * np.sin(2 * phase)
        return sweep.astype(np.float32)

    elif variety_name == "conversational_pauses":
        # 1.2s speech, 1.6s absolute silence, 1.2s speech
        out = np.zeros_like(base)
        s1 = int(sr * 1.2)
        s2 = int(sr * 2.8)
        out[:s1] = base[:s1]
        out[s2:] = base[s2:]
        return 0.5 * out

    elif variety_name == "coughing_throat_clearing":
        # Transient burst of colored high-frequency noise
        burst = np.random.normal(0, 0.4, size=int(sr * 0.4)).astype(np.float32)
        out = np.copy(base) * 0.2
        start = int(sr * 1.5)
        out[start:start + len(burst)] += burst
        return 0.5 * out

    elif variety_name == "laugh_chuckle":
        # Rhythmic bursts of 5Hz amplitude modulation
        chuckle_env = np.maximum(0.0, np.sin(2 * np.pi * 5.0 * t)) ** 2
        return (base * chuckle_env * 0.8).astype(np.float32)

    elif variety_name == "multi_speaker_overlap":
        # Two distinct speech harmonics (140 Hz and 220 Hz)
        spk2 = generate_speech_like_signal(duration_s, f0=220.0, sr=sr)
        return 0.35 * base + 0.35 * spk2

    elif variety_name == "music_in_background":
        # Speech + background musical triad (C major: 261.6, 329.6, 392.0 Hz)
        music = (
            0.1 * np.sin(2 * np.pi * 261.63 * t) +
            0.1 * np.sin(2 * np.pi * 329.63 * t) +
            0.1 * np.sin(2 * np.pi * 392.00 * t)
        )
        return 0.4 * base + music.astype(np.float32)

    elif variety_name == "mobile_speakerphone":
        # Non-linear distortion + high-pass filter
        distorted = np.arctan(2.0 * base)
        fft = np.fft.rfft(distorted)
        freqs = np.fft.rfftfreq(len(distorted), 1.0 / sr)
        fft[freqs < 400] = 0.0
        return 0.4 * np.fft.irfft(fft, n=len(distorted))

    else:
        return base


VARIETY_NAMES = [
    "clean_speech",
    "quiet_speech",
    "loud_speech",
    "telephone_8khz",
    "heavy_compression",
    "low_bitrate",
    "clipping",
    "light_reverb",
    "background_fan_white_noise",
    "room_reverb",
    "packet_loss_dropouts",
    "microphone_distance",
    "highpass_lowpass_filtered",
    "pitch_variation",
    "conversational_pauses",
    "coughing_throat_clearing",
    "laugh_chuckle",
    "multi_speaker_overlap",
    "music_in_background",
    "mobile_speakerphone",
]


@pytest.mark.parametrize("variety", VARIETY_NAMES)
@pytest.mark.asyncio
async def test_authentic_audio_smoke_varieties(variety, audio_detector, dummy_video_info, tmp_path):
    """
    P0.4 Smoke test verifying:
      - None of the 20 acoustic/codec varieties crash AASIST pipeline
      - Valid window results are generated with non-crashing status
      - Either spoof_score in [0.0, 1.0] or status='insufficient_speech'
      - Evidence aggregation handles the result gracefully
    """
    signal = generate_variety(variety, duration_s=4.0)
    wav_path = tmp_path / f"{variety}.wav"
    sf.write(str(wav_path), signal, TARGET_SAMPLE_RATE, subtype="PCM_16")

    # Run detector
    res = await audio_detector.analyze(wav_path, dummy_video_info)

    # 1. Pipeline never crashes and returns expected schema
    assert res is not None
    assert res.available is True
    assert res.status == "completed"
    assert res.model == "AASIST-ASVspoof2019-LA"
    assert len(res.results) >= 1

    # 2. Window validation
    for win in res.results:
        assert win.start_s >= 0.0
        assert win.end_s > win.start_s
        assert win.status in ("analyzed", "insufficient_speech")
        if win.spoof_score is not None:
            assert 0.0 <= win.spoof_score <= 1.0

    # 3. Evidence synthesis
    evidence_svc = EvidenceService()
    modality = evidence_svc._evaluate_audio_modality(res)
    assert modality.level in ("LOW", "MEDIUM", "HIGH", "N/A")
