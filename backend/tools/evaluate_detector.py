import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas.analysis import (
    AudioResult,
    AudioWindowResult,
    SpeechResult,
    SpeechSegment,
    VideoInfo,
    VisualFrameResult,
    VisualResult,
)
from app.schemas.evidence import ProvenanceResult
from app.schemas.reliability import ReliabilityResult
from app.services.assessment_service import AssessmentService
from app.services.evidence_service import EvidenceService
from app.services.fraud_engine import FraudIntentEngine
from app.services.timeline_service import TimelineService


# -----------------------------------------------------------------------------
# INTERNAL EVALUATION DATASET
# Contains:
#   A. Authentic benign videos (e.g. conversational, casual financial phrases)
#   B. Manipulated deepfakes (synthetic facial artifacts + cloned audio)
#   C. Authentic videos with scam dialogue (real video + social engineering)
#   D. Synthetic/manipulated videos with harmless dialogue (e.g. Morgan Freeman AI)
#   E. Re-encoded / compressed / noisy clips
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# INTERNAL EVALUATION DATASET (26 Comprehensive Labeled Benchmark Cases)
# Groups:
#   A. Authentic Benign Videos (Conversational / Casual / Workplace)
#   B. Authentic Financial & Requests (Harmless context / non-fraudulent)
#   C. Manipulated Deepfakes + Urgent Scams (High Manipulation + High Fraud)
#   D. Synthetic / Manipulated Videos with Harmless Dialogue (High Media + Low Fraud)
#   E. Authentic Videos with Social Engineering Scams (Real Media + High Fraud)
#   F. Single-Frame Spikes / Compression Artifacts / Sensor Noise (Spike Attenuation)
#   G. Educational / News Warnings (Reported Context Downgrade Rules)
#   H. Low-Sample / Short Duration / Ambiguous Cases (Reliability Guardrails)
# -----------------------------------------------------------------------------

BENCHMARK_CASES = [
    # Group A: Authentic Benign Videos
    {
        "name": "authentic_benign_conversational",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 10.0,
        "visual_frames": [(i, 0.99, 0.01) for i in range(10)],
        "audio_windows": [(0.0, 4.0, 0.02), (4.0, 8.0, 0.03)],
        "speech": "Good morning everyone, welcome to our weekly product demo.",
    },
    {
        "name": "authentic_benign_vlog_travel",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 12.0,
        "visual_frames": [(i, 0.98, 0.02) for i in range(12)],
        "audio_windows": [(0.0, 4.0, 0.03), (4.0, 8.0, 0.02), (8.0, 12.0, 0.03)],
        "speech": "Today we are exploring the historic old city architecture and checking out local cafes.",
    },
    {
        "name": "authentic_benign_interview",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 10.0,
        "visual_frames": [(i, 0.98, 0.02) for i in range(10)],
        "audio_windows": [(0.0, 4.0, 0.02), (4.0, 8.0, 0.02)],
        "speech": "I have five years of experience building scalable backend microservices with Python and FastAPI.",
    },
    {
        "name": "authentic_benign_lecture",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 12.0,
        "visual_frames": [(i, 0.99, 0.01) for i in range(12)],
        "audio_windows": [(0.0, 4.0, 0.02), (4.0, 8.0, 0.02), (8.0, 12.0, 0.01)],
        "speech": "In today's calculus lecture, we will formally define limits and explore derivative continuity.",
    },

    # Group B: Authentic Financial & Requests (Harmless Context / False-Positive Prevention)
    {
        "name": "authentic_financial_need_i_need_money",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 10.0,
        "visual_frames": [(i, 0.98, 0.02) for i in range(10)],
        "audio_windows": [(0.0, 4.0, 0.03), (4.0, 8.0, 0.02)],
        "speech": "I need money to fix my bicycle before the weekend trip.",
    },
    {
        "name": "authentic_casual_lend_request",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 8.0,
        "visual_frames": [(i, 0.97, 0.03) for i in range(8)],
        "audio_windows": [(0.0, 4.0, 0.04), (4.0, 8.0, 0.03)],
        "speech": "Can you lend me ₹200 for lunch? I forgot my wallet at home.",
    },
    {
        "name": "authentic_financial_rent_split",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 10.0,
        "visual_frames": [(i, 0.98, 0.02) for i in range(10)],
        "audio_windows": [(0.0, 4.0, 0.03), (4.0, 8.0, 0.02)],
        "speech": "Hey roomie, our rent and utility bill split comes out to ₹8,000 each this month.",
    },
    {
        "name": "authentic_grocery_shopping_reimburse",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 8.0,
        "visual_frames": [(i, 0.98, 0.02) for i in range(8)],
        "audio_windows": [(0.0, 4.0, 0.02), (4.0, 8.0, 0.03)],
        "speech": "I picked up groceries for dinner tonight, can you transfer your half when you get a chance?",
    },

    # Group C: Manipulated Deepfakes + Urgent Scams (High Media + High Fraud)
    {
        "name": "deepfake_ceo_urgent_wire_fraud",
        "gt_media": "MANIPULATED",
        "gt_fraud": "HIGH",
        "duration_s": 12.0,
        "visual_frames": [(i, 0.01, 0.99) for i in range(12)],
        "audio_windows": [(0.0, 4.0, 0.98), (4.0, 8.0, 0.99)],
        "speech": "This is the CEO speaking. We have an urgent acquisition. Transfer ₹50,000 immediately and keep this confidential.",
    },
    {
        "name": "deepfake_tech_support_remote_otp",
        "gt_media": "MANIPULATED",
        "gt_fraud": "HIGH",
        "duration_s": 10.0,
        "visual_frames": [(i, 0.02, 0.98) for i in range(10)],
        "audio_windows": [(0.0, 4.0, 0.96), (4.0, 8.0, 0.97)],
        "speech": "This is your bank security. Please install AnyDesk immediately and share your OTP verification code right now.",
    },
    {
        "name": "deepfake_law_enforcement_arrest_threat",
        "gt_media": "MANIPULATED",
        "gt_fraud": "HIGH",
        "duration_s": 12.0,
        "visual_frames": [(i, 0.03, 0.97) for i in range(12)],
        "audio_windows": [(0.0, 4.0, 0.96), (4.0, 8.0, 0.95)],
        "speech": "This is the police department. A warrant has been issued for your arrest. Transfer ₹30,000 to the court escrow immediately.",
    },
    {
        "name": "deepfake_relative_kidnapping_ransom",
        "gt_media": "MANIPULATED",
        "gt_fraud": "HIGH",
        "duration_s": 10.0,
        "visual_frames": [(i, 0.01, 0.99) for i in range(10)],
        "audio_windows": [(0.0, 4.0, 0.98), (4.0, 8.0, 0.99)],
        "speech": "Mom I am in serious trouble, I got arrested and need ₹25,000 bail money sent right away please hurry.",
    },

    # Group D: Synthetic / Manipulated Media with Harmless Dialogue (High Media + Low Fraud)
    {
        "name": "synthetic_morgan_freeman_ai_demo",
        "gt_media": "MANIPULATED",
        "gt_fraud": "LOW",
        "duration_s": 16.0,
        "visual_frames": [(i, 0.001, 0.999) for i in range(16)],
        "audio_windows": [(i * 2.0, i * 2.0 + 4.0, 0.999) for i in range(6)],
        "speech": "I am not Morgan Freeman, and what you see is not real. What would you say if I told you my voice was generated by an AI model?",
    },
    {
        "name": "synthetic_parody_monologue",
        "gt_media": "MANIPULATED",
        "gt_fraud": "LOW",
        "duration_s": 12.0,
        "visual_frames": [(i, 0.04, 0.96) for i in range(12)],
        "audio_windows": [(0.0, 4.0, 0.95), (4.0, 8.0, 0.94), (8.0, 12.0, 0.96)],
        "speech": "Why did the espresso machine file a police report? Because it got mugged in broad daylight.",
    },
    {
        "name": "synthetic_historical_speech_recreation",
        "gt_media": "MANIPULATED",
        "gt_fraud": "LOW",
        "duration_s": 14.0,
        "visual_frames": [(i, 0.03, 0.97) for i in range(14)],
        "audio_windows": [(0.0, 4.0, 0.98), (4.0, 8.0, 0.97), (8.0, 12.0, 0.96)],
        "speech": "Four score and seven years ago our fathers brought forth on this continent a new nation conceived in liberty.",
    },
    {
        "name": "synthetic_poetry_reading",
        "gt_media": "MANIPULATED",
        "gt_fraud": "LOW",
        "duration_s": 10.0,
        "visual_frames": [(i, 0.05, 0.95) for i in range(10)],
        "audio_windows": [(0.0, 4.0, 0.96), (4.0, 8.0, 0.95)],
        "speech": "The woods are lovely dark and deep, but I have promises to keep, and miles to go before I sleep.",
    },

    # Group E: Authentic Videos with Social Engineering Scams (Real Media + High Fraud)
    {
        "name": "authentic_footage_scam_threat",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "HIGH",
        "duration_s": 10.0,
        "visual_frames": [(i, 0.98, 0.02) for i in range(10)],
        "audio_windows": [(0.0, 4.0, 0.03), (4.0, 8.0, 0.02)],
        "speech": "This is federal law enforcement. You face immediate arrest unless you wire ₹50,000 to the court account right now.",
    },
    {
        "name": "authentic_footage_lottery_fee_advance",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "HIGH",
        "duration_s": 10.0,
        "visual_frames": [(i, 0.97, 0.03) for i in range(10)],
        "audio_windows": [(0.0, 4.0, 0.03), (4.0, 8.0, 0.03)],
        "speech": "Congratulations you won ten lakh rupees in our international lucky draw. Pay the five thousand processing tax immediately to claim.",
    },
    {
        "name": "authentic_footage_crypto_guaranteed_return",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "HIGH",
        "duration_s": 10.0,
        "visual_frames": [(i, 0.98, 0.02) for i in range(10)],
        "audio_windows": [(0.0, 4.0, 0.02), (4.0, 8.0, 0.03)],
        "speech": "Invest ten thousand rupees into our proprietary crypto trading bot today for guaranteed five hundred percent weekly returns.",
    },
    {
        "name": "authentic_real_person_ransom_threat",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "HIGH",
        "duration_s": 8.0,
        "visual_frames": [(i, 0.98, 0.02) for i in range(8)],
        "audio_windows": [(0.0, 4.0, 0.03), (4.0, 8.0, 0.02)],
        "speech": "Your boy is in my hand, Mr. Give me 10 crore rupees and I will think about releasing him. Don't even tell the police, I will kill him if I want to.",
    },

    # Group F: Single-Frame Spikes / Compression Artifacts / Sensor Noise (Spike Attenuation)
    {
        "name": "authentic_reencoded_single_spike_frame",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 16.0,
        "visual_frames": [(i, 0.98, 0.02) for i in range(15)] + [(15, 0.08, 0.92)],
        "audio_windows": [(0.0, 4.0, 0.03), (4.0, 8.0, 0.04), (8.0, 12.0, 0.02)],
        "speech": "The weather forecast predicts heavy rain across the state tomorrow.",
    },
    {
        "name": "authentic_reencoded_two_isolated_spikes",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 18.0,
        "visual_frames": [(i, 0.97, 0.03) for i in range(8)] + [(8, 0.12, 0.88)] + [(i, 0.97, 0.03) for i in range(9, 15)] + [(15, 0.14, 0.86)] + [(16, 0.98, 0.02), (17, 0.97, 0.03)],
        "audio_windows": [(0.0, 4.0, 0.03), (4.0, 8.0, 0.04), (8.0, 12.0, 0.03), (12.0, 16.0, 0.02)],
        "speech": "For this recipe, gently fold the whipped cream into the melted dark chocolate and chill for two hours.",
    },
    {
        "name": "authentic_low_light_webcam_noise",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 12.0,
        "visual_frames": [(i, 0.65, 0.35) for i in range(12)],
        "audio_windows": [(0.0, 4.0, 0.05), (4.0, 8.0, 0.06), (8.0, 12.0, 0.04)],
        "speech": "Let us review our study group notes for the upcoming midterm exam.",
    },

    # Group G: Educational / News Warnings (Reported Context Downgrade Rules)
    {
        "name": "news_report_police_scam_warning",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 10.0,
        "visual_frames": [(i, 0.99, 0.01) for i in range(10)],
        "audio_windows": [(0.0, 4.0, 0.02), (4.0, 8.0, 0.03)],
        "speech": "In this news report, police warned that scammers often ask victims to wire money immediately or face arrest.",
    },
    {
        "name": "educational_cybersecurity_training",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 12.0,
        "visual_frames": [(i, 0.98, 0.02) for i in range(12)],
        "audio_windows": [(0.0, 4.0, 0.02), (4.0, 8.0, 0.03), (8.0, 12.0, 0.02)],
        "speech": "This training module demonstrates how spear phishing emails ask employees for urgent wire transfers.",
    },

    # Group H: Low-Sample / Short Duration / Ambiguous Cases (Reliability Guardrails)
    {
        "name": "authentic_ultra_short_portrait_3s",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 3.48,
        "visual_frames": [(0.0, 0.43, 0.57), (1.0, 0.16, 0.84), (2.0, 0.10, 0.90)],
        "audio_windows": [(0.0, 3.48, 0.0)],
        "speech": "i need money, need money",
        "reliability_level": "LOW",
        "reliability_reasons": ["video duration below recommended minimum", "only 3 valid face observations"],
    },
    {
        "name": "short_ambiguous_low_evidence",
        "gt_media": "AUTHENTIC",
        "gt_fraud": "LOW",
        "duration_s": 3.0,
        "visual_frames": [(0.0, 0.45, 0.55), (1.0, 0.48, 0.52)],
        "audio_windows": [(0.0, 3.0, 0.40)],
        "speech": "Hey check this out.",
        "reliability_level": "LOW",
        "reliability_reasons": ["short duration sample (<4s)"],
    },
]


def run_evaluation():
    print("=" * 80)
    print("AUTHENTICA — DETECTOR & FRAUD ACCURACY EVALUATION (INTERNAL EVALUATION SET)")
    print("=" * 80)

    evidence_service = EvidenceService()
    timeline_service = TimelineService()
    assessment_service = AssessmentService()
    fraud_engine = FraudIntentEngine()

    results = []

    for case in BENCHMARK_CASES:
        name = case["name"]
        gt_media = case["gt_media"]
        gt_fraud = case["gt_fraud"]

        # Build Visual Result
        visual_results = [
            VisualFrameResult(
                timestamp_s=float(t),
                face_detected=True,
                real_score=r,
                fake_score=f,
            )
            for t, r, f in case["visual_frames"]
        ]
        visual = VisualResult(
            available=True,
            model="EfficientNet-B0-FFPP-C23",
            status="completed",
            frames_analyzed=len(visual_results),
            faces_found=len(visual_results),
            face_detection_rate=1.0,
            results=visual_results,
        )

        # Build Audio Result
        audio_results = [
            AudioWindowResult(
                start_s=float(s),
                end_s=float(e),
                spoof_score=score,
            )
            for s, e, score in case["audio_windows"]
        ]
        audio = AudioResult(
            available=True,
            model="AASIST-ASVspoof2019-LA",
            status="completed",
            windows_analyzed=len(audio_results),
            results=audio_results,
        )

        duration_s = case.get("duration_s", 10.0)
        # Build Speech & Fraud Result
        speech_text = case["speech"]
        speech = SpeechResult(
            available=True,
            model="faster-whisper-base-int8",
            status="completed",
            language="en",
            duration_s=duration_s,
            text=speech_text,
            segments=[
                SpeechSegment(start_s=0.0, end_s=duration_s, text=speech_text)
            ] if speech_text else []
        )

        fraud_result = fraud_engine.analyze(speech)

        # Build Matrix & Assessment
        video_info = VideoInfo(
            filename=f"{name}.mp4",
            sha256="testsha256",
            duration_s=duration_s,
            fps=30.0,
            width=1280,
            height=720,
            frames_sampled=len(visual_results),
            audio_available=True,
        )
        provenance = ProvenanceResult(
            state="NONE_FOUND",
            valid=None,
            trusted=None,
            signer=None,
            note="Absence of content credentials does not indicate manipulation."
        )
        reliability = ReliabilityResult(
            level=case.get("reliability_level", "OK"),
            reasons=case.get("reliability_reasons", [])
        )

        matrix = evidence_service.build_matrix(video_info, visual, audio, provenance, reliability)
        timeline = timeline_service.aggregate(visual, audio, speech, video_info.duration_s, fraud_result)
        assessment, _, _ = assessment_service.assess(matrix, timeline, fraud_result)

        vis_score = matrix.visual.models[0].score if matrix.visual.models else 0.0
        aud_score = matrix.audio.models[0].score if matrix.audio.models else 0.0

        pred_media = assessment.media
        pred_fraud = assessment.fraud or fraud_result.level
        pred_action = assessment.action

        # Classification matches
        # Media: MANIPULATED matches LIKELY_MANIPULATED / SUSPICIOUS; AUTHENTIC matches NO_STRONG_EVIDENCE / UNCERTAIN
        media_correct = (gt_media == "MANIPULATED" and pred_media in ("LIKELY_MANIPULATED", "SUSPICIOUS")) or \
                        (gt_media == "AUTHENTIC" and pred_media in ("NO_STRONG_EVIDENCE", "UNCERTAIN"))

        fraud_correct = (gt_fraud == "HIGH" and pred_fraud == "HIGH") or \
                        (gt_fraud in ("LOW", "NOT_ASSESSABLE") and pred_fraud in ("LOW", "NOT_ASSESSABLE", "MEDIUM")) or \
                        (gt_fraud == pred_fraud)

        overall_correct = media_correct and fraud_correct

        results.append({
            "name": name,
            "gt_media": gt_media,
            "gt_fraud": gt_fraud,
            "vis_score": vis_score,
            "aud_score": aud_score,
            "pred_media": pred_media,
            "pred_fraud": pred_fraud,
            "action": pred_action,
            "media_correct": media_correct,
            "fraud_correct": fraud_correct,
            "correct": overall_correct,
        })

    # Print Table
    print(f"\n{'Clip':<42} | {'GT-Med':<8} | {'GT-Frd':<6} | {'Vis':<6} | {'Aud':<6} | {'Pred-Media':<18} | {'Pred-Fraud':<10} | {'Action':<15} | {'Match'}")
    print("-" * 135)
    for r in results:
        match_str = "PASS" if r["correct"] else "FAIL"
        print(f"{r['name']:<42} | {r['gt_media']:<8} | {r['gt_fraud']:<6} | {r['vis_score']:<6.3f} | {r['aud_score']:<6.3f} | {r['pred_media']:<18} | {r['pred_fraud']:<10} | {r['action']:<15} | {match_str}")

    # Compute Metrics for Media Dimension (Positive = MANIPULATED)
    m_tp = sum(1 for r in results if r["gt_media"] == "MANIPULATED" and r["pred_media"] in ("LIKELY_MANIPULATED", "SUSPICIOUS"))
    m_fn = sum(1 for r in results if r["gt_media"] == "MANIPULATED" and r["pred_media"] not in ("LIKELY_MANIPULATED", "SUSPICIOUS"))
    m_tn = sum(1 for r in results if r["gt_media"] == "AUTHENTIC" and r["pred_media"] in ("NO_STRONG_EVIDENCE", "UNCERTAIN"))
    m_fp = sum(1 for r in results if r["gt_media"] == "AUTHENTIC" and r["pred_media"] in ("LIKELY_MANIPULATED", "SUSPICIOUS"))

    m_prec = m_tp / (m_tp + m_fp) if (m_tp + m_fp) > 0 else 0.0
    m_rec = m_tp / (m_tp + m_fn) if (m_tp + m_fn) > 0 else 0.0
    m_f1 = (2 * m_prec * m_rec) / (m_prec + m_rec) if (m_prec + m_rec) > 0 else 0.0
    m_fpr = m_fp / (m_fp + m_tn) if (m_fp + m_tn) > 0 else 0.0
    m_fnr = m_fn / (m_fn + m_tp) if (m_fn + m_tp) > 0 else 0.0

    print("\n" + "=" * 50)
    print("MEDIA MANIPULATION METRICS (INTERNAL EVALUATION SET):")
    print(f"  TP: {m_tp} | FP: {m_fp} | TN: {m_tn} | FN: {m_fn}")
    print(f"  False Positive Rate (FPR): {m_fpr:.2%}")
    print(f"  False Negative Rate (FNR): {m_fnr:.2%}")
    print(f"  Precision:                 {m_prec:.2%}")
    print(f"  Recall:                    {m_rec:.2%}")
    print(f"  F1 Score:                  {m_f1:.4f}")
    print("=" * 50)

    # Compute Metrics for Fraud Dimension (Positive = HIGH FRAUD)
    f_tp = sum(1 for r in results if r["gt_fraud"] == "HIGH" and r["pred_fraud"] == "HIGH")
    f_fn = sum(1 for r in results if r["gt_fraud"] == "HIGH" and r["pred_fraud"] != "HIGH")
    f_tn = sum(1 for r in results if r["gt_fraud"] != "HIGH" and r["pred_fraud"] != "HIGH")
    f_fp = sum(1 for r in results if r["gt_fraud"] != "HIGH" and r["pred_fraud"] == "HIGH")

    f_prec = f_tp / (f_tp + f_fp) if (f_tp + f_fp) > 0 else 0.0
    f_rec = f_tp / (f_tp + f_fn) if (f_tp + f_fn) > 0 else 0.0
    f_f1 = (2 * f_prec * f_rec) / (f_prec + f_rec) if (f_prec + f_rec) > 0 else 0.0
    f_fpr = f_fp / (f_fp + f_tn) if (f_fp + f_tn) > 0 else 0.0
    f_fnr = f_fn / (f_fn + f_tp) if (f_fn + f_tp) > 0 else 0.0

    print("\n" + "=" * 50)
    print("FRAUD INTENT METRICS (INTERNAL EVALUATION SET):")
    print(f"  TP: {f_tp} | FP: {f_fp} | TN: {f_tn} | FN: {f_fn}")
    print(f"  False Positive Rate (FPR): {f_fpr:.2%}")
    print(f"  False Negative Rate (FNR): {f_fnr:.2%}")
    print(f"  Precision:                 {f_prec:.2%}")
    print(f"  Recall:                    {f_rec:.2%}")
    print(f"  F1 Score:                  {f_f1:.4f}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Authentica accuracy on benchmark dataset.")
    parser.add_argument("--dataset", type=str, default=None, help="Optional custom dataset directory")
    args = parser.parse_args()
    run_evaluation()
