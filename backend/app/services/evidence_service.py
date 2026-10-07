from typing import List, Optional
import math

from app.core.config import settings
from app.core.logging import logger
from app.schemas.analysis import AudioMetadata, AudioResult, VideoInfo, VisualResult
from app.schemas.evidence import (
    EvidenceMatrix,
    EvidenceMetadata,
    EvidenceModalityResult,
    LocalizedRegion,
    ModalityStatistics,
    ModelEvidenceItem,
    ProvenanceResult,
)
from app.schemas.reliability import ReliabilityResult
from app.services.classification_rules import (
    aggregate_visual_window_bins,
    classify_audio_score,
    classify_score,
    classify_visual_score,
)


class EvidenceService:
    """
    Stage 2 Evidence Synthesis Service.
    Normalizes raw sensory model outputs into discrete evidence levels (LOW / MEDIUM / HIGH / N/A)
    and constructs the unified EvidenceMatrix with localized evidence preservation.
    
    All raw numeric outputs are explicitly annotated as 'model score (not a probability)'.
    """

    def __init__(
        self,
        visual_low: float = settings.VISUAL_LOW_THRESHOLD,
        visual_high: float = settings.VISUAL_HIGH_THRESHOLD,
        audio_low: float = settings.AUDIO_LOW_THRESHOLD,
        audio_high: float = settings.AUDIO_HIGH_THRESHOLD,
    ):
        self.visual_low = visual_low
        self.visual_high = visual_high
        self.audio_low = audio_low
        self.audio_high = audio_high

    def build_matrix(
        self,
        video_info: Optional[VideoInfo] = None,
        visual: Optional[VisualResult] = None,
        audio: Optional[AudioResult] = None,
        provenance: Optional[ProvenanceResult] = None,
        reliability: Optional[ReliabilityResult] = None,
        audio_metadata: Optional[AudioMetadata] = None,
        media_type: str = "VIDEO"
    ) -> EvidenceMatrix:
        """
        Constructs the comprehensive EvidenceMatrix combining all modalities and provenance.
        """
        duration = 0.0
        if media_type == "AUDIO":
            duration = audio_metadata.duration_s if audio_metadata else (video_info.duration_s if video_info else 0.0)
            metadata = EvidenceMetadata(
                media_type="AUDIO",
                width=None,
                height=None,
                duration_s=duration,
                fps=None,
                frames_sampled=0,
                audio_available=True,
            )
        else:
            duration = video_info.duration_s if video_info else 0.0
            metadata = EvidenceMetadata(
                media_type="VIDEO",
                width=video_info.width if video_info else 0,
                height=video_info.height if video_info else 0,
                duration_s=duration,
                fps=video_info.fps if video_info else 0.0,
                frames_sampled=video_info.frames_sampled if video_info else 0,
                audio_available=video_info.audio_available if video_info else False,
            )

        visual_modality = self._evaluate_visual_modality(visual or VisualResult(), video_duration_s=duration)
        audio_modality = self._evaluate_audio_modality(audio or AudioResult())
        prov = provenance or ProvenanceResult(state="NONE_FOUND", note="No provenance manifest found.")
        rel = reliability or ReliabilityResult(level="OK", reasons=[])

        matrix = EvidenceMatrix(
            visual=visual_modality,
            audio=audio_modality,
            provenance=prov,
            metadata=metadata,
            reliability=rel,
        )

        logger.info(
            f"Evidence Matrix Built ({media_type}): visual_level={visual_modality.level} | "
            f"audio_level={audio_modality.level} | provenance_state={prov.state} | "
            f"reliability={rel.level}"
        )
        return matrix

    def _evaluate_visual_modality(
        self,
        visual: VisualResult,
        video_duration_s: float = 0.0
    ) -> EvidenceModalityResult:
        """Evaluates visual detection results using robust whole-video and localized window statistics."""
        if not visual.available or visual.status != "completed" or visual.frames_analyzed == 0:
            return EvidenceModalityResult(
                level="N/A",
                models=[]
            )

        # Collect valid fake scores from frames where a face was detected
        detected_frames = [
            f for f in visual.results
            if f.face_detected is True and f.fake_score is not None
        ]
        detected_fake_scores = [f.fake_score for f in detected_frames]

        if not detected_fake_scores:
            return EvidenceModalityResult(
                level="N/A",
                models=[
                    ModelEvidenceItem(
                        name=visual.model or "VisualDetector",
                        score=None,
                        label="model score (not a probability)"
                    )
                ]
            )

        # 1. Whole-video robust frame statistics
        sorted_scores = sorted(detected_fake_scores)
        n = len(detected_fake_scores)
        mean_score = round(sum(detected_fake_scores) / n, 4)
        median_score = round(
            sorted_scores[n // 2] if n % 2 == 1 else (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2.0,
            4
        )
        max_score = round(max(detected_fake_scores), 4)
        high_frames = [s for s in detected_fake_scores if s >= self.visual_high]
        high_ratio = round(len(high_frames) / n, 4)

        # 2. Localized temporal window aggregation via shared single-source-of-truth partitioner
        window_records = aggregate_visual_window_bins(
            results=visual.results,
            video_duration_s=video_duration_s,
            window_duration_s=3.0,
            visual_low=self.visual_low,
            visual_high=self.visual_high,
        )

        # 3. Analyze consecutive HIGH windows and localized regions
        total_eval_windows = len(window_records)
        high_windows = [w for w in window_records if w["level"] == "HIGH"]
        high_window_ratio = round(len(high_windows) / max(1, total_eval_windows), 4) if total_eval_windows > 0 else 0.0

        consecutive_high_count = 0
        current_consecutive = 0
        current_run_windows = []
        localized_high_regions: List[LocalizedRegion] = []
        persistent_windows_count = 0

        for w in window_records:
            if w["level"] == "HIGH":
                current_consecutive += 1
                current_run_windows.append(w)
                if current_consecutive > consecutive_high_count:
                    consecutive_high_count = current_consecutive
            else:
                if len(current_run_windows) >= 2:
                    run_start = current_run_windows[0]["start_s"]
                    run_end = current_run_windows[-1]["end_s"]
                    run_mean = round(sum(rw["mean_score"] for rw in current_run_windows) / len(current_run_windows), 4)
                    localized_high_regions.append(LocalizedRegion(
                        start_s=run_start,
                        end_s=run_end,
                        level="HIGH",
                        mean_score=run_mean
                    ))
                    persistent_windows_count += len(current_run_windows)
                current_consecutive = 0
                current_run_windows = []

        # Flush trailing run (requires >= 2 contiguous windows)
        if len(current_run_windows) >= 2:
            run_start = current_run_windows[0]["start_s"]
            run_end = current_run_windows[-1]["end_s"]
            run_mean = round(sum(rw["mean_score"] for rw in current_run_windows) / len(current_run_windows), 4)
            localized_high_regions.append(LocalizedRegion(
                start_s=run_start,
                end_s=run_end,
                level="HIGH",
                mean_score=run_mean
            ))
            persistent_windows_count += len(current_run_windows)

        persistent_high_window_ratio = round(persistent_windows_count / max(1, total_eval_windows), 4) if total_eval_windows > 0 else 0.0

        # Calibrated whole-video + localized evidence decision:
        # HIGH requires persistent manipulation across multiple windows (>=2), high global mean (>=0.70) with at least 1 non-attenuated HIGH window, or localized high regions
        has_high_windows = any(w["level"] == "HIGH" for w in window_records)
        if (
            (mean_score >= self.visual_high and has_high_windows)
            or (consecutive_high_count >= 2)
            or (len(localized_high_regions) > 0 and max_score >= 0.85)
        ):
            level = "HIGH"
        elif (mean_score >= self.visual_low) or (high_ratio >= 0.20) or (high_window_ratio >= 0.25) or (len(high_windows) > 0):
            level = "MEDIUM"
        else:
            level = "LOW"

        rep_score = mean_score

        stats = ModalityStatistics(
            valid_frame_count=n,
            mean_score=mean_score,
            median_score=median_score,
            max_score=max_score,
            high_ratio=high_ratio,
            consecutive_high_count=consecutive_high_count,
            high_window_ratio=high_window_ratio,
            persistent_high_window_ratio=persistent_high_window_ratio,
            localized_high_regions=localized_high_regions,
        )

        return EvidenceModalityResult(
            level=level,
            models=[
                ModelEvidenceItem(
                    name=visual.model or "EfficientNet-B0-FFPP-C23",
                    score=rep_score,
                    label="model score (not a probability)"
                )
            ],
            statistics=stats
        )

    def _evaluate_audio_modality(self, audio: AudioResult) -> EvidenceModalityResult:
        """Evaluates audio anti-spoofing results using robust whole-clip and localized window statistics."""
        if not audio.available or audio.status != "completed" or not audio.results:
            return EvidenceModalityResult(
                level="N/A",
                models=[]
            )

        valid_windows = [
            win for win in audio.results
            if win.spoof_score is not None
        ]
        valid_spoof_scores = [win.spoof_score for win in valid_windows]

        if not valid_spoof_scores:
            return EvidenceModalityResult(
                level="N/A",
                models=[
                    ModelEvidenceItem(
                        name=audio.model or "AudioDetector",
                        score=None,
                        label="model score (not a probability)"
                    )
                ]
            )

        sorted_scores = sorted(valid_spoof_scores)
        n = len(valid_spoof_scores)
        mean_score = round(sum(valid_spoof_scores) / n, 4)
        median_score = round(
            sorted_scores[n // 2] if n % 2 == 1 else (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2.0,
            4
        )
        max_score = round(max(valid_spoof_scores), 4)
        high_windows = [s for s in valid_spoof_scores if s >= self.audio_high]
        high_ratio = round(len(high_windows) / n, 4)

        # Analyze consecutive high audio windows
        consecutive_high_count = 0
        current_consecutive = 0
        current_run_windows = []
        localized_high_regions: List[LocalizedRegion] = []
        persistent_windows_count = 0

        for win in valid_windows:
            score = win.spoof_score or 0.0
            if score >= self.audio_high:
                current_consecutive += 1
                current_run_windows.append(win)
                if current_consecutive > consecutive_high_count:
                    consecutive_high_count = current_consecutive
            else:
                if len(current_run_windows) >= 2:
                    run_start = round(current_run_windows[0].start_s, 2)
                    run_end = round(current_run_windows[-1].end_s, 2)
                    run_mean = round(sum((w.spoof_score or 0.0) for w in current_run_windows) / len(current_run_windows), 4)
                    localized_high_regions.append(LocalizedRegion(
                        start_s=run_start,
                        end_s=run_end,
                        level="HIGH",
                        mean_score=run_mean
                    ))
                    persistent_windows_count += len(current_run_windows)
                current_consecutive = 0
                current_run_windows = []

        if len(current_run_windows) >= 2:
            run_start = round(current_run_windows[0].start_s, 2)
            run_end = round(current_run_windows[-1].end_s, 2)
            run_mean = round(sum((w.spoof_score or 0.0) for w in current_run_windows) / len(current_run_windows), 4)
            localized_high_regions.append(LocalizedRegion(
                start_s=run_start,
                end_s=run_end,
                level="HIGH",
                mean_score=run_mean
            ))
            persistent_windows_count += len(current_run_windows)

        high_window_ratio = high_ratio
        persistent_high_window_ratio = round(persistent_windows_count / max(1, n), 4)

        # Calibrated decision logic:
        # HIGH requires persistent spoofing across multiple windows (>=2) or high global mean (>=0.70 with n>=2)
        if (
            (mean_score >= self.audio_high and n >= 2)
            or (consecutive_high_count >= 2)
            or (len(localized_high_regions) > 0 and max_score >= 0.85)
        ):
            level = "HIGH"
        elif (mean_score >= self.audio_low) or (high_ratio >= 0.20) or (max_score >= self.audio_high):
            level = "MEDIUM"
        else:
            level = "LOW"

        rep_score = mean_score

        stats = ModalityStatistics(
            valid_frame_count=n,
            mean_score=mean_score,
            median_score=median_score,
            max_score=max_score,
            high_ratio=high_ratio,
            consecutive_high_count=consecutive_high_count,
            high_window_ratio=high_window_ratio,
            persistent_high_window_ratio=persistent_high_window_ratio,
            localized_high_regions=localized_high_regions,
        )

        return EvidenceModalityResult(
            level=level,
            models=[
                ModelEvidenceItem(
                    name=audio.model or "AASIST-ASVspoof2019-LA",
                    score=rep_score,
                    label="model score (not a probability)"
                )
            ],
            statistics=stats
        )
