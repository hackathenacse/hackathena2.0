import pytest
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


def make_matrix(visual_level: str, audio_level: str, rel_level: str = "OK") -> EvidenceMatrix:
    return EvidenceMatrix(
        visual=EvidenceModalityResult(
            level=visual_level,
            models=[ModelEvidenceItem(name="VisualModel", score=0.8 if visual_level == "HIGH" else 0.1)],
        ),
        audio=EvidenceModalityResult(
            level=audio_level,
            models=[ModelEvidenceItem(name="AudioModel", score=0.8 if audio_level == "HIGH" else 0.1)],
        ),
        provenance=ProvenanceResult(
            state="NONE_FOUND",
            valid=None,
            trusted=None,
            signer=None,
            note="Absence of content credentials does not indicate manipulation.",
        ),
        metadata=EvidenceMetadata(
            width=1280,
            height=720,
            duration_s=10.0,
            fps=30.0,
            frames_sampled=10,
            audio_available=True,
        ),
        reliability=ReliabilityResult(
            level=rel_level,
            reasons=[] if rel_level == "OK" else ["Video resolution below threshold"],
        ),
    )


def test_assessment_rules():
    service = AssessmentService()
    timeline = [
        TimelineEvent(
            start_s=0.0,
            end_s=3.0,
            kind="visual",
            level="HIGH",
            evidence_source="visual_window",
            score=0.85,
        )
    ]

    # Rule 1: Reliability LOW -> UNCERTAIN
    matrix_low_rel = make_matrix("HIGH", "HIGH", rel_level="LOW")
    res, exp, lim = service.assess(matrix_low_rel, timeline)
    assert res.media == "UNCERTAIN"
    assert any("degraded" in e.lower() for e in exp)
    assert len(lim) > 0

    # Rule 2: Visual HIGH + Audio HIGH -> LIKELY_MANIPULATED
    matrix_both_high = make_matrix("HIGH", "HIGH", rel_level="OK")
    res, exp, lim = service.assess(matrix_both_high, timeline)
    assert res.media == "LIKELY_MANIPULATED"
    assert any("Multi-modal synthesis" in e for e in exp)

    # Rule 3: Visual HIGH + Audio LOW -> SUSPICIOUS
    matrix_vis_high = make_matrix("HIGH", "LOW", rel_level="OK")
    res, exp, lim = service.assess(matrix_vis_high, timeline)
    assert res.media == "SUSPICIOUS"

    # Rule 4: Visual LOW + Audio HIGH -> SUSPICIOUS
    matrix_aud_high = make_matrix("LOW", "HIGH", rel_level="OK")
    res, exp, lim = service.assess(matrix_aud_high, timeline)
    assert res.media == "SUSPICIOUS"

    # Rule 5: Visual MEDIUM + Audio MEDIUM -> SUSPICIOUS
    matrix_both_med = make_matrix("MEDIUM", "MEDIUM", rel_level="OK")
    res, exp, lim = service.assess(matrix_both_med, timeline)
    assert res.media == "SUSPICIOUS"

    # Rule 6: All available LOW + Reliability OK -> NO_STRONG_EVIDENCE (NEVER "AUTHENTIC")
    matrix_low = make_matrix("LOW", "LOW", rel_level="OK")
    res, exp, lim = service.assess(matrix_low, timeline)
    assert res.media == "NO_STRONG_EVIDENCE"
    assert res.media != "AUTHENTIC"
    assert any("No strong indicators" in e for e in exp)


def test_assessment_never_outputs_authentic():
    service = AssessmentService()
    # Test all permutations of levels
    levels = ["LOW", "MEDIUM", "HIGH", "N/A"]
    for v in levels:
        for a in levels:
            for r in ["OK", "LOW"]:
                matrix = make_matrix(v, a, rel_level=r)
                res, _, _ = service.assess(matrix, [])
                assert res.media != "AUTHENTIC"
                assert res.media in {"LIKELY_MANIPULATED", "SUSPICIOUS", "NO_STRONG_EVIDENCE", "UNCERTAIN"}
