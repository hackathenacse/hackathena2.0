import math
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.schemas.analysis import VisualFrameResult


def classify_score(
    score: Optional[float],
    low_thresh: float = settings.VISUAL_LOW_THRESHOLD,
    high_thresh: float = settings.VISUAL_HIGH_THRESHOLD,
) -> str:
    """
    Centralized Single Source of Truth for discrete score-to-level classification.
    Returns: 'HIGH' | 'MEDIUM' | 'LOW' | 'N/A'
    """
    if score is None:
        return "N/A"
    if score >= high_thresh:
        return "HIGH"
    if score >= low_thresh:
        return "MEDIUM"
    return "LOW"


def classify_visual_score(score: Optional[float]) -> str:
    """Classifies a visual model score into LOW / MEDIUM / HIGH / N/A."""
    return classify_score(score, settings.VISUAL_LOW_THRESHOLD, settings.VISUAL_HIGH_THRESHOLD)


def classify_audio_score(score: Optional[float]) -> str:
    """Classifies an audio anti-spoofing score into LOW / MEDIUM / HIGH / N/A."""
    return classify_score(score, settings.AUDIO_LOW_THRESHOLD, settings.AUDIO_HIGH_THRESHOLD)


def classify_visual_window_level(
    mean_score: Optional[float],
    max_score: Optional[float],
    high_count: int,
    n_frames: int,
    visual_low: float = settings.VISUAL_LOW_THRESHOLD,
    visual_high: float = settings.VISUAL_HIGH_THRESHOLD,
) -> str:
    """
    Classifies a temporal visual window bin.
    
    A window is HIGH only if:
      - mean_score >= visual_high (0.70), OR
      - n_frames == 1 and max_score >= visual_high (0.70), OR
      - high_count >= 2 and mean_score >= visual_high.
    
    A window is MEDIUM if:
      - mean_score >= visual_low (0.30), OR
      - high_count >= 1, OR
      - max_score >= visual_high.
      
    Otherwise LOW (or N/A if n_frames == 0).
    """
    if n_frames == 0 or mean_score is None:
        return "N/A"

    if (
        mean_score >= visual_high
        or (n_frames == 1 and max_score is not None and max_score >= visual_high)
        or (high_count >= 2 and mean_score >= visual_high)
    ):
        return "HIGH"
    elif mean_score >= visual_low or high_count >= 1 or (max_score is not None and max_score >= visual_high):
        return "MEDIUM"
    else:
        return "LOW"


def score_to_clipped_logit(p: float, clip_range: float = 6.0) -> float:
    """Clips score to avoid inf and converts to logit space within [-clip_range, clip_range]."""
    eps = 1.0 / (1.0 + math.exp(clip_range))
    p_clamped = min(max(p, eps), 1.0 - eps)
    logit = math.log(p_clamped / (1.0 - p_clamped))
    return max(-clip_range, min(clip_range, logit))


def logit_to_score(logit: float) -> float:
    """Converts logit back to probability score space [0.0, 1.0]."""
    return 1.0 / (1.0 + math.exp(-logit))


def aggregate_visual_window_bins(
    results: List[VisualFrameResult],
    video_duration_s: float,
    window_duration_s: float = settings.TIMELINE_WINDOW_DURATION_S,
    visual_low: float = settings.VISUAL_LOW_THRESHOLD,
    visual_high: float = settings.VISUAL_HIGH_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    Robust temporal window partitioner and evaluator used identically by EvidenceService and TimelineService.
    Operates internally with logit-space clipping [-6, 6] and window medians to prevent single-frame anomalies
    from dominating while preserving genuine sustained high regions.
    """
    if not results:
        return []

    detected_frames = [
        f for f in results
        if f.face_detected is True and f.fake_score is not None
    ]

    max_t = max([f.timestamp_s for f in detected_frames], default=video_duration_s)
    effective_dur = max(video_duration_s, max_t, 1.0)
    num_windows = max(1, math.ceil(effective_dur / window_duration_s))

    raw_windows: List[Dict[str, Any]] = []

    for w_idx in range(num_windows):
        w_start = round(w_idx * window_duration_s, 2)
        w_end = round(min((w_idx + 1) * window_duration_s, effective_dur), 2)

        if w_idx == num_windows - 1:
            frames_in_win = [f for f in detected_frames if w_start <= f.timestamp_s <= w_end]
        else:
            frames_in_win = [f for f in detected_frames if w_start <= f.timestamp_s < w_end]

        w_scores = [f.fake_score for f in frames_in_win if f.fake_score is not None]

        if w_scores:
            w_n = len(w_scores)
            sorted_scores = sorted(w_scores)
            w_mean = round(sum(w_scores) / w_n, 4)
            
            # Robust median computed via logit-space clipping [-6.0, 6.0]
            w_logits = [score_to_clipped_logit(s) for s in sorted_scores]
            mid_logit = w_logits[w_n // 2] if w_n % 2 == 1 else (w_logits[w_n // 2 - 1] + w_logits[w_n // 2]) / 2.0
            w_median = round(logit_to_score(mid_logit), 4)

            w_max = round(max(w_scores), 4)
            w_high_count = len([s for s in w_scores if s >= visual_high])

            # Detect isolated single-frame spike anomaly within the window
            is_window_spike = (w_max >= visual_high and w_median < visual_low)

            raw_level = classify_visual_window_level(
                mean_score=w_mean,
                max_score=w_max,
                high_count=w_high_count,
                n_frames=w_n,
                visual_low=visual_low,
                visual_high=visual_high,
            )

            raw_windows.append({
                "start_s": w_start,
                "end_s": w_end,
                "score": w_median,  # Robust median is representative window score
                "mean_score": w_mean,
                "median_score": w_median,
                "max_score": w_max,
                "high_count": w_high_count,
                "level": raw_level,
                "raw_level": raw_level,
                "frame_count": w_n,
                "isolated_anomaly": is_window_spike,
            })
        else:
            raw_windows.append({
                "start_s": w_start,
                "end_s": w_end,
                "score": None,
                "mean_score": None,
                "median_score": None,
                "max_score": None,
                "high_count": 0,
                "level": "N/A",
                "raw_level": "N/A",
                "frame_count": 0,
                "isolated_anomaly": False,
            })

    # Across-window isolated spike attenuation: keep anomaly visible without dominating whole video
    total_windows = len(raw_windows)
    observed_windows = [w for w in raw_windows if w["score"] is not None]
    total_observed = len(observed_windows)
    if total_observed > 1:
        for i, win in enumerate(raw_windows):
            if win["level"] == "HIGH":
                # Find previous observed window
                prev_obs = None
                for p in range(i - 1, -1, -1):
                    if raw_windows[p]["score"] is not None:
                        prev_obs = raw_windows[p]
                        break
                # Find next observed window
                next_obs = None
                for nxt in range(i + 1, total_windows):
                    if raw_windows[nxt]["score"] is not None:
                        next_obs = raw_windows[nxt]
                        break

                has_prev_qualifying = prev_obs is not None and prev_obs["score"] >= visual_low
                has_next_qualifying = next_obs is not None and next_obs["score"] >= visual_low

                # If isolated spike surrounded or bounded by observed low windows:
                # Mark as isolated anomaly and calibrate window level to MEDIUM
                if not (has_prev_qualifying or has_next_qualifying):
                    win["level"] = "MEDIUM"
                    win["isolated_anomaly"] = True

    return raw_windows

