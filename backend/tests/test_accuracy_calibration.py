import pytest
from app.schemas.analysis import (
    AudioResult,
    AudioWindowResult,
    SpeechResult,
    SpeechSegment,
    VideoInfo,
    VisualFrameResult,
    VisualResult,
)
from app.schemas.evidence import (
    EvidenceMatrix,
    EvidenceMetadata,
    EvidenceModalityResult,
    ModelEvidenceItem,
    ProvenanceResult,
)
from app.schemas.reliability import ReliabilityResult
from app.schemas.timeline import TimelineEvent
from app.services.assessment_service import AssessmentService
from app.services.classification_rules import (
    aggregate_visual_window_bins,
    classify_audio_score,
    classify_score,
    classify_visual_score,
    classify_visual_window_level,
)
from app.services.evidence_service import EvidenceService
from app.services.fraud_engine import FraudIntentEngine
from app.services.reliability_service import ReliabilityService
from app.services.timeline_service import TimelineService


@pytest.fixture
def evidence_service():
    return EvidenceService()


@pytest.fixture
def timeline_service():
    return TimelineService()


@pytest.fixture
def assessment_service():
    return AssessmentService()


@pytest.fixture
def fraud_engine():
    return FraudIntentEngine()


# --------------------------------------------------------------------------
# 1. Visual Spike False Positive Prevention Tests
# --------------------------------------------------------------------------

def test_single_visual_frame_spike_does_not_force_high_or_likely_manipulated(evidence_service, assessment_service):
    """
    Regression Test: A real video with 15 low frames and 1 isolated high frame spike (e.g. 0.95)
    must NOT produce visual level HIGH or final verdict LIKELY_MANIPULATED.
    """
    # 15 frames at ~0.02, 1 spike frame at 0.95 (Mean = ~0.08)
    frames = [
        VisualFrameResult(timestamp_s=float(i), face_detected=True, real_score=0.98, fake_score=0.02)
        for i in range(15)
    ]
    frames.append(
        VisualFrameResult(timestamp_s=15.0, face_detected=True, real_score=0.05, fake_score=0.95)
    )

    visual = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=16,
        faces_found=16,
        face_detection_rate=1.0,
        results=frames,
    )

    audio_clean = AudioResult(
        available=True,
        model="AASIST-ASVspoof2019-LA",
        status="completed",
        windows_analyzed=4,
        results=[
            AudioWindowResult(start_s=0.0, end_s=4.0, spoof_score=0.02),
            AudioWindowResult(start_s=4.0, end_s=8.0, spoof_score=0.03),
            AudioWindowResult(start_s=8.0, end_s=12.0, spoof_score=0.01),
            AudioWindowResult(start_s=12.0, end_s=16.0, spoof_score=0.02),
        ],
    )

    video_info = VideoInfo(
        filename="real_person_with_glitch.mp4",
        sha256="abc1234567890",
        duration_s=16.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=16,
        audio_available=True,
    )

    provenance = ProvenanceResult(
        state="NONE_FOUND",
        valid=None,
        trusted=None,
        signer=None,
        note="Absence of content credentials does not indicate manipulation.",
    )

    reliability = ReliabilityResult(level="OK", reasons=[])

    matrix = evidence_service.build_matrix(video_info, visual, audio_clean, provenance, reliability)

    # Visual modality must be LOW or at most MEDIUM, never HIGH
    assert matrix.visual.level != "HIGH"
    assert matrix.visual.statistics is not None
    assert matrix.visual.statistics.mean_score < 0.15
    assert matrix.visual.statistics.max_score == 0.95

    # Final assessment: MUST NOT be LIKELY_MANIPULATED
    res, exp, lim = assessment_service.assess(matrix, [])
    assert res.media != "LIKELY_MANIPULATED"
    assert res.media in ("NO_STRONG_EVIDENCE", "SUSPICIOUS")


def test_consistent_low_evidence_produces_no_strong_evidence(evidence_service, assessment_service):
    """
    Regression Test: Real video with consistently low visual and audio scores produces NO_STRONG_EVIDENCE.
    """
    frames = [
        VisualFrameResult(timestamp_s=float(i), face_detected=True, real_score=0.99, fake_score=0.01)
        for i in range(10)
    ]
    visual = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=10,
        faces_found=10,
        face_detection_rate=1.0,
        results=frames,
    )

    audio = AudioResult(
        available=True,
        model="AASIST-ASVspoof2019-LA",
        status="completed",
        windows_analyzed=2,
        results=[
            AudioWindowResult(start_s=0.0, end_s=4.0, spoof_score=0.02),
            AudioWindowResult(start_s=4.0, end_s=8.0, spoof_score=0.03),
        ],
    )

    video_info = VideoInfo(
        filename="authentic_clip.mp4",
        sha256="def987654321",
        duration_s=8.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=10,
        audio_available=True,
    )

    provenance = ProvenanceResult(
        state="NONE_FOUND",
        valid=None,
        trusted=None,
        signer=None,
        note="Absence of content credentials does not indicate manipulation.",
    )
    reliability = ReliabilityResult(level="OK", reasons=[])

    matrix = evidence_service.build_matrix(video_info, visual, audio, provenance, reliability)
    assert matrix.visual.level == "LOW"
    assert matrix.audio.level == "LOW"

    res, exp, lim = assessment_service.assess(matrix, [])
    assert res.media == "NO_STRONG_EVIDENCE"
    assert res.media != "AUTHENTIC"


def test_consistent_high_multimodal_evidence_produces_likely_manipulated(evidence_service, assessment_service):
    """
    Regression Test: Persistent high visual and audio scores produce LIKELY_MANIPULATED.
    """
    frames = [
        VisualFrameResult(timestamp_s=float(i), face_detected=True, real_score=0.01, fake_score=0.99)
        for i in range(10)
    ]
    visual = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=10,
        faces_found=10,
        face_detection_rate=1.0,
        results=frames,
    )

    audio = AudioResult(
        available=True,
        model="AASIST-ASVspoof2019-LA",
        status="completed",
        windows_analyzed=2,
        results=[
            AudioWindowResult(start_s=0.0, end_s=4.0, spoof_score=0.98),
            AudioWindowResult(start_s=4.0, end_s=8.0, spoof_score=0.97),
        ],
    )

    video_info = VideoInfo(
        filename="deepfake_synthetic.mp4",
        sha256="fake123456",
        duration_s=8.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=10,
        audio_available=True,
    )

    provenance = ProvenanceResult(
        state="NONE_FOUND",
        valid=None,
        trusted=None,
        signer=None,
        note="Absence of content credentials does not indicate manipulation.",
    )
    reliability = ReliabilityResult(level="OK", reasons=[])

    matrix = evidence_service.build_matrix(video_info, visual, audio, provenance, reliability)
    assert matrix.visual.level == "HIGH"
    assert matrix.audio.level == "HIGH"

    res, exp, lim = assessment_service.assess(matrix, [])
    assert res.media == "LIKELY_MANIPULATED"


# --------------------------------------------------------------------------
# 2. Fraud Intent Engine Regression Tests
# --------------------------------------------------------------------------

def test_fraud_i_need_money_is_low(fraud_engine):
    """
    'I need money.' must NOT be classified as high or medium fraud.
    """
    speech = SpeechResult(
        available=True,
        model="faster-whisper-base-int8",
        status="completed",
        language="en",
        duration_s=3.0,
        text="I need money to buy groceries.",
        segments=[
            SpeechSegment(start_s=0.0, end_s=3.0, text="I need money to buy groceries.")
        ],
    )
    res = fraud_engine.analyze(speech)
    assert res.level == "LOW"
    assert len(res.requested_actions) == 0
    assert not any(c.category == "PAYMENT_CREDENTIAL" for c in res.categories)


def test_fraud_send_me_money_action(fraud_engine):
    """
    'Send me money.' contains SEND_MONEY action.
    """
    speech = SpeechResult(
        available=True,
        model="faster-whisper-base-int8",
        status="completed",
        language="en",
        duration_s=3.0,
        text="Send me money right away.",
        segments=[
            SpeechSegment(start_s=0.0, end_s=3.0, text="Send me money right away.")
        ],
    )
    res = fraud_engine.analyze(speech)
    assert any(a.action == "SEND_MONEY" for a in res.requested_actions)


def test_fraud_ceo_wire_urgent_secrecy(fraud_engine):
    """
    'I am your CEO. Send the money immediately. Don't tell anyone.' -> HIGH fraud.
    """
    speech = SpeechResult(
        available=True,
        model="faster-whisper-base-int8",
        status="completed",
        language="en",
        duration_s=5.0,
        text="I am your CEO. Send the money immediately. Don't tell anyone.",
        segments=[
            SpeechSegment(start_s=0.0, end_s=5.0, text="I am your CEO. Send the money immediately. Don't tell anyone.")
        ],
    )
    res = fraud_engine.analyze(speech)
    assert res.level == "HIGH"
    assert any(c.category == "AUTHORITY" for c in res.categories)
    assert any(c.category == "URGENCY" for c in res.categories)
    assert any(c.category == "SECRECY" for c in res.categories)
    assert any(a.action in ("SEND_MONEY", "TRANSFER_MONEY") for a in res.requested_actions)


def test_fraud_police_warned_downgrade(fraud_engine):
    """
    'Police warned that scammers ask victims to send money.' -> Not HIGH fraud.
    """
    speech = SpeechResult(
        available=True,
        model="faster-whisper-base-int8",
        status="completed",
        language="en",
        duration_s=5.0,
        text="Police warned that scammers ask victims to send money.",
        segments=[
            SpeechSegment(start_s=0.0, end_s=5.0, text="Police warned that scammers ask victims to send money.")
        ],
    )
    res = fraud_engine.analyze(speech)
    assert res.level != "HIGH"
    assert res.news_context_downgrade is True


def test_df2_morgan_freeman_harmless_ai(fraud_engine, assessment_service):
    """
    Regression Test: DF2.mp4 known transcript:
    'I am not Morgan Freeman, and what you see is not real.'
    Expected: media: LIKELY_MANIPULATED, fraud: LOW, action: CAUTION.
    """
    speech = SpeechResult(
        available=True,
        model="faster-whisper-base-int8",
        status="completed",
        language="en",
        duration_s=8.0,
        text="I am not Morgan Freeman, and what you see is not real. What would you say if I told you that my voice was generated by an AI model?",
        segments=[
            SpeechSegment(start_s=0.0, end_s=4.0, text="I am not Morgan Freeman, and what you see is not real."),
            SpeechSegment(start_s=4.0, end_s=8.0, text="What would you say if I told you that my voice was generated by an AI model?")
        ],
    )
    fraud_res = fraud_engine.analyze(speech)
    assert fraud_res.level == "LOW"

    # Simulated Stage 2 output for DF2.mp4
    matrix = EvidenceMatrix(
        visual=EvidenceModalityResult(
            level="HIGH",
            models=[ModelEvidenceItem(name="EfficientNet-B0-FFPP-C23", score=0.998)]
        ),
        audio=EvidenceModalityResult(
            level="HIGH",
            models=[ModelEvidenceItem(name="AASIST-ASVspoof2019-LA", score=0.999)]
        ),
        provenance=ProvenanceResult(
            state="NONE_FOUND",
            valid=None,
            trusted=None,
            signer=None,
            note="Absence of content credentials does not indicate manipulation."
        ),
        metadata=EvidenceMetadata(
            width=1280, height=720, duration_s=15.1, fps=30.0, frames_sampled=16, audio_available=True
        ),
        reliability=ReliabilityResult(level="OK", reasons=[]),
    )

    assessment, explanations, limitations = assessment_service.assess(matrix, [], fraud_res)
    assert assessment.media == "LIKELY_MANIPULATED"
    assert assessment.fraud == "LOW"
    assert assessment.action == "CAUTION"


def test_df2_actual_trace_evaluation(evidence_service, assessment_service, fraud_engine):
    """
    Regression Test: Evaluates DF2 actual frame trace:
    - Persistent visual manipulation in early windows ([0-3s] and [3-6s] HIGH)
    - Low audio spoofing scores
    - Harmless speech transcript
    Must produce visual: HIGH, media: SUSPICIOUS, fraud: LOW, action: CAUTION (Never UNCERTAIN).
    """
    frames = [
        VisualFrameResult(timestamp_s=0.0, face_detected=True, real_score=0.09, fake_score=0.91),
        VisualFrameResult(timestamp_s=1.0, face_detected=True, real_score=0.10, fake_score=0.90),
        VisualFrameResult(timestamp_s=2.0, face_detected=True, real_score=0.10, fake_score=0.90),
        VisualFrameResult(timestamp_s=3.0, face_detected=True, real_score=0.10, fake_score=0.90),
        VisualFrameResult(timestamp_s=4.0, face_detected=True, real_score=0.10, fake_score=0.90),
        VisualFrameResult(timestamp_s=5.0, face_detected=True, real_score=0.55, fake_score=0.45),
        VisualFrameResult(timestamp_s=6.0, face_detected=True, real_score=0.60, fake_score=0.40),
        VisualFrameResult(timestamp_s=7.0, face_detected=True, real_score=0.50, fake_score=0.50),
        VisualFrameResult(timestamp_s=8.0, face_detected=True, real_score=0.10, fake_score=0.90),
        VisualFrameResult(timestamp_s=9.0, face_detected=True, real_score=0.70, fake_score=0.30),
        VisualFrameResult(timestamp_s=10.0, face_detected=True, real_score=0.70, fake_score=0.30),
        VisualFrameResult(timestamp_s=11.0, face_detected=True, real_score=0.70, fake_score=0.30),
        VisualFrameResult(timestamp_s=12.0, face_detected=True, real_score=0.10, fake_score=0.90),
        VisualFrameResult(timestamp_s=13.0, face_detected=True, real_score=0.65, fake_score=0.35),
        VisualFrameResult(timestamp_s=14.0, face_detected=True, real_score=0.70, fake_score=0.30),
        VisualFrameResult(timestamp_s=15.0, face_detected=True, real_score=0.70, fake_score=0.30),
    ]

    visual = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=16,
        faces_found=16,
        face_detection_rate=1.0,
        results=frames,
    )

    audio = AudioResult(
        available=True,
        model="AASIST-ASVspoof2019-LA",
        status="completed",
        windows_analyzed=7,
        results=[
            AudioWindowResult(start_s=0.0, end_s=4.0, spoof_score=0.21),
            AudioWindowResult(start_s=2.0, end_s=6.0, spoof_score=0.11),
            AudioWindowResult(start_s=4.0, end_s=8.0, spoof_score=0.07),
            AudioWindowResult(start_s=6.0, end_s=10.0, spoof_score=0.00),
            AudioWindowResult(start_s=8.0, end_s=12.0, spoof_score=0.00),
            AudioWindowResult(start_s=10.0, end_s=14.0, spoof_score=0.00),
            AudioWindowResult(start_s=12.0, end_s=15.1, spoof_score=0.97),
        ],
    )

    video_info = VideoInfo(
        filename="DF2.mp4",
        sha256="33cab4d8a97f5226e5aa623684380ccb39f7795ad61040e653b7e1765906c118",
        duration_s=15.1,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=16,
        audio_available=True,
    )

    provenance = ProvenanceResult(
        state="NONE_FOUND",
        valid=None,
        trusted=None,
        signer=None,
        note="Absence of content credentials does not indicate manipulation.",
    )
    reliability = ReliabilityResult(level="OK", reasons=[])

    matrix = evidence_service.build_matrix(video_info, visual, audio, provenance, reliability)

    # 1. Visual evidence must identify persistent manipulation
    assert matrix.visual.level == "HIGH"
    assert matrix.visual.statistics.consecutive_high_count >= 2
    assert len(matrix.visual.statistics.localized_high_regions) > 0
    assert matrix.visual.statistics.localized_high_regions[0].start_s == 0.0
    assert matrix.visual.statistics.localized_high_regions[0].end_s >= 6.0

    # 2. Media Assessment must be SUSPICIOUS (or LIKELY_MANIPULATED if multimodal), NEVER UNCERTAIN
    speech = SpeechResult(
        available=True,
        model="faster-whisper-base-int8",
        status="completed",
        language="en",
        duration_s=15.1,
        text="I am not Morgan Freeman, and what you see is not real.",
        segments=[
            SpeechSegment(start_s=0.0, end_s=4.5, text="I am not Morgan Freeman, and what you see is not real.")
        ],
    )
    fraud_res = fraud_engine.analyze(speech)

    assessment, explanations, limitations = assessment_service.assess(matrix, [], fraud_res)
    assert assessment.media in ("SUSPICIOUS", "LIKELY_MANIPULATED")
    assert assessment.media != "UNCERTAIN"
    assert assessment.fraud == "LOW"
    assert assessment.action in ("VERIFY", "CAUTION")


def test_localized_high_regions_retention(evidence_service):
    """
    Test: 3 consecutive HIGH visual windows (0-3s, 3-6s, 6-9s) followed by 5 LOW windows (9-24s).
    Must retain localized_high_regions and classify visual as HIGH despite low whole-video mean.
    """
    frames = []
    # 0-9s: High fake scores (~0.92)
    for i in range(9):
        frames.append(VisualFrameResult(timestamp_s=float(i), face_detected=True, real_score=0.08, fake_score=0.92))
    # 9-24s: Low fake scores (~0.05)
    for i in range(9, 24):
        frames.append(VisualFrameResult(timestamp_s=float(i), face_detected=True, real_score=0.95, fake_score=0.05))

    visual = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=24,
        faces_found=24,
        face_detection_rate=1.0,
        results=frames,
    )

    modality = evidence_service._evaluate_visual_modality(visual, video_duration_s=24.0)
    assert modality.level == "HIGH"
    assert modality.statistics.consecutive_high_count == 3
    assert len(modality.statistics.localized_high_regions) == 1
    assert modality.statistics.localized_high_regions[0].start_s == 0.0
    assert modality.statistics.localized_high_regions[0].end_s == 9.0


def test_isolated_visual_spike_does_not_create_localized_region(evidence_service):
    """
    Test: Single isolated spike frame does not create a localized high region.
    """
    frames = [
        VisualFrameResult(timestamp_s=float(i), face_detected=True, real_score=0.98, fake_score=0.02)
        for i in range(15)
    ]
    frames.append(
        VisualFrameResult(timestamp_s=15.0, face_detected=True, real_score=0.05, fake_score=0.95)
    )

    visual = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=16,
        faces_found=16,
        face_detection_rate=1.0,
        results=frames,
    )

    modality = evidence_service._evaluate_visual_modality(visual, video_duration_s=16.0)
    assert modality.level != "HIGH"
    assert modality.statistics.consecutive_high_count <= 1
    assert modality.statistics.persistent_high_window_ratio == 0.0
    assert len(modality.statistics.localized_high_regions) == 0


# --------------------------------------------------------------------------
# 3. Authentic Benchmark Video & False Positive Prevention Tests
# --------------------------------------------------------------------------

def test_authentic_friend_video_benchmark(evidence_service, timeline_service, assessment_service, fraud_engine):
    """
    Critical Benchmark Test:
    Authentic friend's video saying joking phrase 'i need money, need money'.
    Specs:
      - duration = 3.48s, width = 478, height = 850, fps = 30.02
      - frames_sampled = 4, faces_found = 3
      - frame scores: [0.28, 0.70, 0.8278] (mean = ~0.6026, max = 0.8278)
      - audio spoof score = 0.0
      - speech text = 'I need money, need money'
    
    Verifications:
      1. Reliability is LOW due to duration < 4.0s and visual face sample size < 5.
      2. Evidence visual level is MEDIUM (never HIGH for 0.60 score).
      3. Timeline visual window level is MEDIUM (100% consistent with Evidence visual level).
      4. Media Assessment is UNCERTAIN (due to small sample size / degraded reliability).
      5. Fraud Intent is LOW with zero requested actions.
      6. Action is VERIFY.
      7. Explanation honestly cites small sample size without overconfident manipulation claims.
    """
    frames = [
        VisualFrameResult(timestamp_s=0.0, face_detected=True, real_score=0.72, fake_score=0.28),
        VisualFrameResult(timestamp_s=1.0, face_detected=True, real_score=0.30, fake_score=0.70),
        VisualFrameResult(timestamp_s=2.0, face_detected=True, real_score=0.1722, fake_score=0.8278),
        VisualFrameResult(timestamp_s=3.0, face_detected=False, real_score=None, fake_score=None),
    ]

    visual = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=4,
        faces_found=3,
        face_detection_rate=0.75,
        results=frames,
    )

    audio = AudioResult(
        available=True,
        model="AASIST-ASVspoof2019-LA",
        status="completed",
        windows_analyzed=1,
        results=[
            AudioWindowResult(start_s=0.0, end_s=3.48, spoof_score=0.0),
        ],
    )

    video_info = VideoInfo(
        filename="friend_authentic_joke.mp4",
        sha256="friend1234567890abcdef",
        duration_s=3.48,
        fps=30.02,
        width=478,
        height=850,
        frames_sampled=4,
        audio_available=True,
    )

    provenance = ProvenanceResult(
        state="NONE_FOUND",
        valid=None,
        trusted=None,
        signer=None,
        note="Absence of content credentials does not indicate manipulation.",
    )

    # 1. Evaluate Reliability Gate
    reliability_service = ReliabilityService()
    reliability = reliability_service.evaluate(video_info, visual, audio)
    assert reliability.level == "LOW"
    assert any("sample size" in r.lower() for r in reliability.reasons)
    assert any("duration" in r.lower() for r in reliability.reasons)

    # 2. Build Evidence Matrix
    matrix = evidence_service.build_matrix(video_info, visual, audio, provenance, reliability)
    assert matrix.visual.level == "MEDIUM"
    assert matrix.visual.level != "HIGH"
    assert matrix.audio.level == "LOW"

    # 3. Aggregate Timeline Events
    speech = SpeechResult(
        available=True,
        model="faster-whisper-base-int8",
        status="completed",
        language="en",
        duration_s=3.48,
        text="I need money, need money",
        segments=[
            SpeechSegment(start_s=0.0, end_s=3.0, text="I need money, need money")
        ],
    )
    fraud_res = fraud_engine.analyze(speech)
    timeline = timeline_service.aggregate(visual, audio, speech, video_duration_s=3.48, fraud=fraud_res)

    visual_timeline_events = [ev for ev in timeline if ev.kind == "visual"]
    assert len(visual_timeline_events) >= 1
    # Strict Consistency Check: Timeline visual event level MUST match Evidence visual level
    assert visual_timeline_events[0].level == matrix.visual.level
    assert visual_timeline_events[0].level == "MEDIUM"

    # 4. Synthesize Final Assessment
    assessment, explanations, limitations = assessment_service.assess(matrix, timeline, fraud_res)
    assert assessment.media == "UNCERTAIN"
    assert assessment.fraud == "LOW"
    assert assessment.action == "VERIFY"

    # 5. Verify Grounded Explanations
    assert not any("high-confidence facial manipulation artifacts" in exp for exp in explanations)
    assert any("visual evidence is insufficient for a confident assessment" in exp for exp in explanations)


def test_single_source_of_truth_score_classification():
    """
    Verifies that classify_score, classify_visual_score, and classify_audio_score
    produce deterministic, single-source-of-truth results across all boundaries.
    """
    assert classify_visual_score(None) == "N/A"
    assert classify_visual_score(0.10) == "LOW"
    assert classify_visual_score(0.299) == "LOW"
    assert classify_visual_score(0.30) == "MEDIUM"
    assert classify_visual_score(0.6028) == "MEDIUM"
    assert classify_visual_score(0.6999) == "MEDIUM"
    assert classify_visual_score(0.70) == "HIGH"
    assert classify_visual_score(0.99) == "HIGH"

    assert classify_audio_score(None) == "N/A"
    assert classify_audio_score(0.0) == "LOW"
    assert classify_audio_score(0.40) == "MEDIUM"
    assert classify_audio_score(0.75) == "HIGH"


# --------------------------------------------------------------------------
# 4. Calibration & Consistency Verification Tests (A through I)
# --------------------------------------------------------------------------

def test_a_same_score_produces_identical_evidence_and_timeline_level(evidence_service, timeline_service):
    """
    Test A: The same underlying score (e.g. 0.6028) produces identical visual evidence level
    and timeline window level.
    """
    frames = [
        VisualFrameResult(timestamp_s=0.0, face_detected=True, real_score=0.3972, fake_score=0.6028),
        VisualFrameResult(timestamp_s=1.0, face_detected=True, real_score=0.3972, fake_score=0.6028),
        VisualFrameResult(timestamp_s=2.0, face_detected=True, real_score=0.3972, fake_score=0.6028),
    ]
    visual = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=3,
        faces_found=3,
        face_detection_rate=1.0,
        results=frames,
    )
    modality = evidence_service._evaluate_visual_modality(visual, video_duration_s=3.0)
    audio = AudioResult(available=False, model="", status="none", windows_analyzed=0, results=[])
    speech = SpeechResult(available=False, model="", status="none", language=None, duration_s=0.0, text="", segments=[])
    timeline = timeline_service.aggregate(visual, audio, speech, video_duration_s=3.0)

    visual_events = [ev for ev in timeline if ev.kind == "visual"]
    assert len(visual_events) >= 1
    assert modality.level == "MEDIUM"
    assert visual_events[0].level == "MEDIUM"
    assert modality.level == visual_events[0].level


def test_b_three_face_observations_cannot_produce_high_forensic_evidence(evidence_service, assessment_service):
    """
    Test B: 3 face observations with elevated scores cannot produce a confident LIKELY_MANIPULATED verdict
    because low sample size and degraded reliability force media to UNCERTAIN.
    """
    frames = [
        VisualFrameResult(timestamp_s=0.0, face_detected=True, real_score=0.1, fake_score=0.9),
        VisualFrameResult(timestamp_s=1.0, face_detected=True, real_score=0.1, fake_score=0.9),
        VisualFrameResult(timestamp_s=2.0, face_detected=True, real_score=0.1, fake_score=0.9),
    ]
    visual = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=3,
        faces_found=3,
        face_detection_rate=1.0,
        results=frames,
    )
    audio = AudioResult(available=False, model="", status="none", windows_analyzed=0, results=[])
    video_info = VideoInfo(
        filename="short_face.mp4",
        sha256="test3faces",
        duration_s=3.0,
        fps=30.0,
        width=478,
        height=850,
        frames_sampled=3,
        audio_available=False,
    )
    reliability = ReliabilityService().evaluate(video_info, visual, audio)
    assert reliability.level == "LOW"

    matrix = evidence_service.build_matrix(
        video_info,
        visual,
        audio,
        ProvenanceResult(state="NONE_FOUND", valid=None, trusted=None, signer=None, note="None"),
        reliability
    )
    res, exp, lim = assessment_service.assess(matrix, [])
    assert res.media == "UNCERTAIN"
    assert res.media != "LIKELY_MANIPULATED"


def test_c_zero_consecutive_high_windows_cannot_produce_persistent_high(evidence_service):
    """
    Test C: High ratio or spikes with 0 consecutive high windows cannot produce persistent HIGH.
    """
    frames = [
        VisualFrameResult(timestamp_s=0.0, face_detected=True, real_score=0.1, fake_score=0.9),
        VisualFrameResult(timestamp_s=3.5, face_detected=True, real_score=0.9, fake_score=0.1),
        VisualFrameResult(timestamp_s=6.5, face_detected=True, real_score=0.1, fake_score=0.9),
    ]
    visual = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=3,
        faces_found=3,
        face_detection_rate=1.0,
        results=frames,
    )
    modality = evidence_service._evaluate_visual_modality(visual, video_duration_s=9.0)
    assert modality.statistics.consecutive_high_count == 0
    assert modality.statistics.persistent_high_window_ratio == 0.0


def test_d_i_need_money_results_in_fraud_low_no_actions(fraud_engine):
    """
    Test D: Phrase 'I need money' yields fraud: LOW and requested_actions: [].
    """
    speech = SpeechResult(
        available=True,
        model="faster-whisper-base-int8",
        status="completed",
        language="en",
        duration_s=3.0,
        text="I need money",
        segments=[SpeechSegment(start_s=0.0, end_s=3.0, text="I need money")],
    )
    res = fraud_engine.analyze(speech)
    assert res.level == "LOW"
    assert len(res.requested_actions) == 0


def test_e_send_me_money_triggers_send_money_action(fraud_engine):
    """
    Test E: Phrase 'Send me money' triggers direct action SEND_MONEY.
    """
    speech = SpeechResult(
        available=True,
        model="faster-whisper-base-int8",
        status="completed",
        language="en",
        duration_s=3.0,
        text="Send me money now",
        segments=[SpeechSegment(start_s=0.0, end_s=3.0, text="Send me money now")],
    )
    res = fraud_engine.analyze(speech)
    assert any(a.action == "SEND_MONEY" for a in res.requested_actions)


def test_f_low_reliability_forces_media_uncertain(assessment_service):
    """
    Test F: Low reliability forces media = UNCERTAIN regardless of evidence modality levels.
    """
    matrix = EvidenceMatrix(
        visual=EvidenceModalityResult(
            level="HIGH",
            models=[ModelEvidenceItem(name="EfficientNet-B0-FFPP-C23", score=0.95)]
        ),
        audio=EvidenceModalityResult(
            level="HIGH",
            models=[ModelEvidenceItem(name="AASIST-ASVspoof2019-LA", score=0.95)]
        ),
        provenance=ProvenanceResult(state="NONE_FOUND", valid=None, trusted=None, signer=None, note="None"),
        metadata=EvidenceMetadata(width=478, height=850, duration_s=2.0, fps=30.0, frames_sampled=2, audio_available=True),
        reliability=ReliabilityResult(level="LOW", reasons=["Short duration < 4.0s", "Insufficient face sample size (2 < 5)"]),
    )
    res, exp, lim = assessment_service.assess(matrix, [])
    assert res.media == "UNCERTAIN"


def test_g_audio_spoof_zero_produces_low_not_guaranteed_authentic():
    """
    Test G: Audio spoof score 0 produces audio: LOW, which does NOT imply guaranteed authentic.
    """
    level = classify_audio_score(0.0)
    assert level == "LOW"


def test_h_portrait_video_preserves_aspect_ratio():
    """
    Test H: Face detector handles portrait 478x850 image with square aspect ratio preservation.
    """
    import numpy as np
    from app.services.detectors.visual_detector import VisualDeepfakeDetector

    detector = VisualDeepfakeDetector()
    # Create a 850x478 black frame with a white square box simulating face region
    frame = np.zeros((850, 478, 3), dtype=np.uint8)
    frame[200:400, 150:350] = 200

    # Test square crop logic internally
    x, y, w, h = 150, 200, 200, 200
    crop = detector._crop_square_face(frame, origin_x=x, origin_y=y, width=w, height=h, margin_ratio=0.15)
    assert crop is not None
    assert crop.shape[0] == crop.shape[1]  # Must be square 1:1 aspect ratio


def test_i_verification_disclaimer_for_uncertain_media_low_fraud(assessment_service):
    """
    Test I: Verification disclaimer appears when action is VERIFY on UNCERTAIN media and fraud is LOW.
    """
    matrix = EvidenceMatrix(
        visual=EvidenceModalityResult(level="MEDIUM", models=[]),
        audio=EvidenceModalityResult(level="LOW", models=[]),
        provenance=ProvenanceResult(state="NONE_FOUND", valid=None, trusted=None, signer=None, note="None"),
        metadata=EvidenceMetadata(width=478, height=850, duration_s=3.48, fps=30.0, frames_sampled=4, audio_available=True),
        reliability=ReliabilityResult(level="LOW", reasons=["Duration < 4.0s", "Face count < 5"]),
    )
    speech = SpeechResult(
        available=True, model="whisper", status="completed", language="en", duration_s=3.48,
        text="I need money",
        segments=[SpeechSegment(start_s=0.0, end_s=3.48, text="I need money")]
    )
    fraud = FraudIntentEngine().analyze(speech)
    assessment, explanations, limitations = assessment_service.assess(matrix, [], fraud)
    assert assessment.media == "UNCERTAIN"
    assert assessment.action == "VERIFY"
    assert any("verification recommendation is due to uncertainty in media authenticity" in exp for exp in explanations)


