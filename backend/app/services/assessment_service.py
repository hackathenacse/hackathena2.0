from typing import List, Optional, Tuple

from app.core.logging import logger
from app.schemas.evidence import EvidenceMatrix, MediaAssessment
from app.schemas.fraud import FraudResult
from app.schemas.timeline import TimelineEvent


class AssessmentService:
    """
    Stage 2 & Stage 3 Media Assessment, Fraud Intent & Action Synthesis Service.
    
    Synthesizes the EvidenceMatrix, Timeline, and Fraud findings into:
      1. MediaAssessment verdict ('media', 'fraud', 'action')
      2. Grounded, evidence-backed human explanations
      3. Systemic and model-specific limitations
      
    CRITICAL INVARIANTS:
      - Media manipulation and Fraud intent are independent orthogonal dimensions.
      - NEVER declares media "AUTHENTIC".
      - STOP_AND_VERIFY is triggered exclusively when high-risk fraud intent is present.
      - Never implies real financial or bank blocking.
    """

    DEFAULT_LIMITATIONS: List[str] = [
        "Detection models (EfficientNet-B0, AASIST) are trained on specific benchmark datasets and may exhibit degraded accuracy on out-of-distribution media, novel generative techniques, or heavy compression.",
        "Model scores are raw heuristic indicators, not calibrated statistical probabilities.",
        "Absence of C2PA Content Credentials does not imply manipulation, as standard recording equipment rarely embeds provenance metadata.",
        "Prototype thresholds and rule-based fraud heuristics should be calibrated against domain-specific operational data.",
    ]

    def assess(
        self,
        matrix: EvidenceMatrix,
        timeline: List[TimelineEvent],
        fraud: Optional[FraudResult] = None,
    ) -> Tuple[MediaAssessment, List[str], List[str]]:
        """
        Determines the media assessment verdict, fraud level, and recommended action.
        
        Args:
            matrix: Synthesized EvidenceMatrix containing visual, audio, provenance, metadata, reliability.
            timeline: Aggregated chronological timeline events.
            fraud: Stage 3 FraudResult findings.
            
        Returns:
            Tuple of (MediaAssessment, explanation_list, limitations_list)
        """
        rel_level = matrix.reliability.level
        visual_level = matrix.visual.level
        audio_level = matrix.audio.level

        # 1. Determine Media Manipulation Verdict strictly based on Stage 2 rules
        exact_verified = getattr(matrix.metadata, "exact_verified_match", False)
        verified_record = getattr(matrix.metadata, "verified_ground_truth", None)

        if exact_verified and verified_record:
            gt_m = verified_record.get("ground_truth_media")
            if gt_m == "REAL":
                media_verdict = "NO_STRONG_EVIDENCE"
            elif gt_m == "FAKE":
                media_verdict = "LIKELY_MANIPULATED"
            else:
                media_verdict = "UNCERTAIN"
        elif rel_level == "LOW":
            # Genuine media quality degradation, corruption, or execution failure
            media_verdict = "UNCERTAIN"
        elif visual_level == "HIGH" and audio_level == "HIGH":
            # CASE B: Multi-modal high-confidence synthetic manipulation (face swap + voice clone)
            media_verdict = "LIKELY_MANIPULATED"
        elif visual_level == "HIGH" or audio_level == "HIGH":
            # CASE A: Strong persistent single-modality manipulation (visual face swap or audio clone)
            media_verdict = "SUSPICIOUS"
        elif visual_level == "MEDIUM" or audio_level == "MEDIUM":
            # Moderate / borderline forensic anomalies observed
            media_verdict = "SUSPICIOUS"
        elif visual_level == "LOW" and (audio_level == "LOW" or audio_level == "N/A") and rel_level == "OK":
            # CASE C: Clean authentic media across available modalities
            media_verdict = "NO_STRONG_EVIDENCE"
        elif audio_level == "LOW" and (visual_level == "LOW" or visual_level == "N/A") and rel_level == "OK":
            # CASE C: Clean authentic media across available modalities
            media_verdict = "NO_STRONG_EVIDENCE"
        elif visual_level == "N/A" and audio_level == "N/A":
            # CASE D: Genuinely insufficient modality data (no faces and no audio track)
            media_verdict = "UNCERTAIN"
        else:
            # CASE D: Genuinely unresolvable or degraded evidence
            media_verdict = "UNCERTAIN"

        # 2. Determine Fraud Intent Level
        fraud_level = fraud.level if fraud else "LOW"

        # 3. Combine Media Verdict + Fraud Level -> Final Action
        if fraud_level == "HIGH":
            action = "STOP_AND_VERIFY"
        elif media_verdict in ("SUSPICIOUS", "LIKELY_MANIPULATED") and fraud_level == "MEDIUM":
            action = "VERIFY"
        elif media_verdict == "LIKELY_MANIPULATED" and fraud_level == "LOW":
            action = "CAUTION"
        elif media_verdict == "NO_STRONG_EVIDENCE" and fraud_level in ("LOW", "NOT_ASSESSABLE"):
            action = "NO_ACTION_FLAGGED"
        elif media_verdict == "UNCERTAIN":
            action = "VERIFY"
        else:
            action = "VERIFY"

        assessment = MediaAssessment(
            media=media_verdict,
            fraud=fraud_level,
            action=action,
        )

        # 4. Generate Grounded Explanations
        explanations = self._generate_explanations(matrix, media_verdict, timeline, fraud, action)
        limitations = list(self.DEFAULT_LIMITATIONS)

        logger.info(
            f"Assessment Completed: media={media_verdict} | fraud={fraud_level} | action={action} | "
            f"explanations_count={len(explanations)}"
        )
        return assessment, explanations, limitations

    def _generate_explanations(
        self,
        matrix: EvidenceMatrix,
        media_verdict: str,
        timeline: List[TimelineEvent],
        fraud: Optional[FraudResult],
        action: str,
    ) -> List[str]:
        reasons: List[str] = []

        # 0. Verified Media Memory Context
        if getattr(matrix.metadata, "exact_verified_match", False) and getattr(matrix.metadata, "verified_ground_truth", None):
            gt = matrix.metadata.verified_ground_truth
            reasons.append(
                f"Exact Verified Media: File binary matches a certified {gt.get('ground_truth_media')} record in the Authentica ground-truth registry."
            )

        if getattr(matrix.metadata, "near_duplicate_match", None):
            nd = matrix.metadata.near_duplicate_match
            reasons.append(
                f"Near-Duplicate Supporting Signal: Perceptual similarity ({nd['similarity'] * 100:.1f}%) "
                f"matches previously analyzed '{nd.get('filename')}' ({nd.get('ground_truth_media')})."
            )

        # 1. Reliability Context
        if matrix.reliability.level == "LOW":
            has_sample_issue = any("sample size" in r.lower() or "usable face" in r.lower() for r in matrix.reliability.reasons)
            if has_sample_issue:
                n_faces = matrix.visual.statistics.valid_frame_count if matrix.visual.statistics else 0
                n_sampled = matrix.metadata.frames_sampled or len(timeline)
                if n_sampled > 0:
                    reasons.append(
                        f"Only {n_faces} of {n_sampled} sampled frames contained usable faces, "
                        f"so visual evidence is insufficient for a confident assessment."
                    )
                else:
                    reasons.append(
                        "Visual analysis produced ambiguous evidence from a small number of usable facial observations, resulting in an UNCERTAIN assessment."
                    )
            else:
                rel_details = "; ".join(matrix.reliability.reasons) if matrix.reliability.reasons else "Quality criteria not met"
                reasons.append(f"Media quality or detector execution was degraded ({rel_details}), resulting in an UNCERTAIN assessment.")

        # 2. Visual Modality
        if media_verdict == "UNCERTAIN" and matrix.reliability.level == "LOW":
            if matrix.visual.level == "HIGH":
                reasons.append("Visual detector observed elevated anomaly signals, but insufficient sample size or degraded quality precludes a definitive manipulation verdict.")
            elif matrix.visual.level == "MEDIUM":
                reasons.append("Visual detector observed moderate/borderline facial anomalies in sampled frames.")
            elif matrix.visual.level == "LOW":
                reasons.append("Visual detector found no significant synthetic facial artifacts in analyzed frames.")
            elif matrix.visual.level == "N/A":
                if matrix.metadata.media_type == "AUDIO":
                    reasons.append("Visual facial manipulation detection is not applicable for audio-only media.")
                else:
                    reasons.append("Visual facial manipulation detection was not applicable (no faces detected or detector unavailable).")
        else:
            if matrix.visual.level == "HIGH":
                reasons.append("Visual detector identified persistent, high-confidence facial manipulation artifacts across analyzed video frames.")
            elif matrix.visual.level == "MEDIUM":
                reasons.append("Visual detector observed moderate/borderline facial anomalies in sampled frames.")
            elif matrix.visual.level == "LOW":
                reasons.append("Visual detector found no significant synthetic facial artifacts in analyzed frames.")
            elif matrix.visual.level == "N/A":
                if matrix.metadata.media_type == "AUDIO":
                    reasons.append("Visual facial manipulation detection is not applicable for audio-only media.")
                else:
                    reasons.append("Visual facial manipulation detection was not applicable (no faces detected or detector unavailable).")

        # 3. Audio Modality
        if matrix.audio.level == "HIGH":
            reasons.append("Audio detector identified high-confidence synthetic voice or spoofing anomalies in audio windows.")
        elif matrix.audio.level == "MEDIUM":
            reasons.append("Audio detector observed moderate synthetic voice characteristics in audio windows.")
        elif matrix.audio.level == "LOW":
            reasons.append("Audio anti-spoofing detector found no substantial synthetic speech characteristics.")
        elif matrix.audio.level == "N/A":
            reasons.append("Audio anti-spoofing was not applicable (no audio stream present or detector unavailable).")

        # 3b. Modality Synthesis
        if matrix.visual.level == "HIGH" and matrix.audio.level == "HIGH" and media_verdict == "LIKELY_MANIPULATED":
            reasons.append("Multi-modal synthesis detected: both visual and audio evidence independently indicate manipulation or synthesis.")
        elif media_verdict == "NO_STRONG_EVIDENCE":
            reasons.append("No strong indicators of manipulation or synthetic alteration were found across available modalities.")

        # 4. Provenance Note
        reasons.append(f"Provenance status: {matrix.provenance.note}")

        # 5. Timeline Context
        high_timeline_events = [ev for ev in timeline if ev.level == "HIGH"]
        if high_timeline_events:
            consolidated_ranges = self._consolidate_event_ranges(high_timeline_events)
            windows_str = ", ".join(f"[{start:.1f}s - {end:.1f}s]" for start, end in consolidated_ranges)
            reasons.append(f"High-severity anomalies concentrated in time window(s): {windows_str}.")

        # 6. Stage 3 Fraud Intent Findings
        if fraud and fraud.level != "NOT_ASSESSABLE":
            if fraud.requested_actions:
                for req in fraud.requested_actions:
                    reasons.append(
                        f"Direct request detected: {req.action} ('{req.phrase}' at {req.start_s:.1f}s–{req.end_s:.1f}s)."
                    )
            if fraud.categories:
                cats_str = ", ".join(c.category for c in fraud.categories)
                reasons.append(f"Social engineering risk indicators identified: {cats_str}.")

            if fraud.news_context_downgrade:
                reasons.append(
                    "The transcript may describe or report a scam rather than directly instructing the viewer."
                )

        # 7. Final Action Advice
        if action == "STOP_AND_VERIFY":
            reasons.append(
                "High-risk social engineering or financial extraction patterns detected. "
                "Do not act on the request until you independently verify the person's identity using a trusted channel."
            )
        elif action == "CAUTION":
            reasons.append(
                "Media shows signs of manipulation or synthesis; exercise caution and verify source authenticity before sharing or acting."
            )
        elif action == "VERIFY":
            if media_verdict == "UNCERTAIN" and (fraud is None or fraud.level == "LOW"):
                reasons.append(
                    "The verification recommendation is due to uncertainty in media authenticity, not because a fraud request was detected."
                )
            else:
                reasons.append(
                    "Moderate anomalies observed; verify sender identity through an established secondary channel."
                )
        elif action == "NO_ACTION_FLAGGED":
            reasons.append(
                "No strong manipulation or fraudulent intent was identified in the analyzed content."
            )

        return reasons

    @staticmethod
    def _consolidate_event_ranges(events: List[TimelineEvent], max_gap_s: float = 0.1) -> List[Tuple[float, float]]:
        """
        Consolidates adjacent or overlapping timeline events into continuous time ranges.
        """
        if not events:
            return []

        sorted_events = sorted(events, key=lambda ev: (ev.start_s, ev.end_s))
        merged: List[List[float]] = []

        for ev in sorted_events:
            if not merged:
                merged.append([ev.start_s, ev.end_s])
            else:
                prev = merged[-1]
                if ev.start_s <= prev[1] + max_gap_s:
                    prev[1] = max(prev[1], ev.end_s)
                else:
                    merged.append([ev.start_s, ev.end_s])

        return [(round(m[0], 2), round(m[1], 2)) for m in merged]
