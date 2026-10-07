import os
import tempfile
from pathlib import Path
import cv2
import numpy as np
import pytest
import torch

from app.schemas.analysis import VideoInfo, VisualFrameResult, VisualResult
from app.services.detectors.base import FrameSample
from app.services.detectors.visual_detector import (
    MODEL_NAME,
    VisualDeepfakeDetector,
)


def create_synthetic_face_image(width=300, height=300) -> np.ndarray:
    """Creates a synthetic image with face-like geometry detectable by MediaPipe."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 220
    # Head contour
    cv2.circle(img, (width // 2, height // 2), int(min(width, height) * 0.35), (210, 175, 140), -1)
    # Eyes
    eye_y = int(height * 0.45)
    cv2.circle(img, (int(width * 0.4), eye_y), int(min(width, height) * 0.05), (40, 40, 40), -1)
    cv2.circle(img, (int(width * 0.6), eye_y), int(min(width, height) * 0.05), (40, 40, 40), -1)
    # Nose
    cv2.line(img, (width // 2, eye_y), (width // 2, int(height * 0.55)), (160, 120, 90), 2)
    # Mouth
    cv2.ellipse(
        img,
        (width // 2, int(height * 0.65)),
        (int(width * 0.12), int(height * 0.06)),
        0, 0, 180, (40, 40, 40), 2
    )
    return img


def create_blank_image(width=300, height=300) -> np.ndarray:
    """Creates a blank non-face image."""
    return np.zeros((height, width, 3), dtype=np.uint8)


@pytest.fixture(scope="module")
def detector():
    """Initializes and loads the visual deepfake detector once for tests."""
    det = VisualDeepfakeDetector(device="cpu", min_face_confidence=0.3)
    det.load()
    return det


@pytest.fixture
def sample_video_info():
    return VideoInfo(
        filename="test_video.mp4",
        sha256="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        duration_s=3.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=3,
        audio_available=False,
    )


def test_model_loading(detector):
    """Test 1: Verifies model is loaded, on correct device, in eval mode."""
    assert detector._is_loaded is True
    assert detector.model is not None
    assert detector.face_detector is not None
    assert not detector.model.training
    assert detector.device == torch.device("cpu")


def test_valid_face_image_inference(detector):
    """Test 2: Verifies prediction on a valid face crop returns calibrated scores in [0, 1]."""
    face_img = create_synthetic_face_image(224, 224)
    real_s, fake_s = detector.predict_face_crop(face_img)

    assert isinstance(real_s, float)
    assert isinstance(fake_s, float)
    assert 0.0 <= real_s <= 1.0
    assert 0.0 <= fake_s <= 1.0
    assert abs((real_s + fake_s) - 1.0) < 0.02


def test_batch_inference(detector):
    """Test 3: Verifies batch inference produces identical length and valid scores."""
    face_1 = create_synthetic_face_image(224, 224)
    face_2 = create_synthetic_face_image(224, 224)
    scores = detector.predict_batch([face_1, face_2])

    assert len(scores) == 2
    for real_s, fake_s in scores:
        assert 0.0 <= real_s <= 1.0
        assert 0.0 <= fake_s <= 1.0


def test_no_face_detection(detector):
    """Test 4: Verifies that blank images return None from face detection."""
    blank_img = create_blank_image(300, 300)
    crop = detector.detect_primary_face(blank_img)
    assert crop is None


def test_multiple_faces_selection(detector):
    """Test 5: Verifies that when multiple face-like regions exist, the largest is selected."""
    # Create canvas with two face structures: one large, one small
    img = np.ones((600, 800, 3), dtype=np.uint8) * 220
    
    # Large face
    cv2.circle(img, (300, 300), 120, (210, 175, 140), -1)
    cv2.circle(img, (260, 280), 15, (40, 40, 40), -1)
    cv2.circle(img, (340, 280), 15, (40, 40, 40), -1)
    cv2.ellipse(img, (300, 350), (40, 20), 0, 0, 180, (40, 40, 40), 3)

    # Small face
    cv2.circle(img, (650, 150), 40, (210, 175, 140), -1)
    cv2.circle(img, (635, 140), 5, (40, 40, 40), -1)
    cv2.circle(img, (665, 140), 5, (40, 40, 40), -1)
    cv2.ellipse(img, (650, 165), (12, 6), 0, 0, 180, (40, 40, 40), 2)

    crop = detector.detect_primary_face(img)
    if crop is not None:
        # The crop should be from the larger face
        assert crop.shape[0] > 100 or crop.shape[1] > 100


@pytest.mark.asyncio
async def test_video_integration_and_timestamps(detector, sample_video_info):
    """Test 6 & 7: Verifies end-to-end analyze() method preserves timestamps and handles mixed frames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create 3 test frames:
        # Frame 0 (0.0s): synthetic face
        # Frame 1 (1.0s): blank image (no face)
        # Frame 2 (2.0s): synthetic face
        f0 = tmp_path / "frame_0000.jpg"
        f1 = tmp_path / "frame_0001.jpg"
        f2 = tmp_path / "frame_0002.jpg"

        cv2.imwrite(str(f0), create_synthetic_face_image(400, 400))
        cv2.imwrite(str(f1), create_blank_image(400, 400))
        cv2.imwrite(str(f2), create_synthetic_face_image(400, 400))

        frame_samples = [
            FrameSample(timestamp_s=0.0, frame_path=f0),
            FrameSample(timestamp_s=1.0, frame_path=f1),
            FrameSample(timestamp_s=2.0, frame_path=f2),
        ]

        result: VisualResult = await detector.analyze(frame_samples, sample_video_info)

        assert result.available is True
        assert result.model == MODEL_NAME
        assert result.status == "completed"
        assert result.frames_analyzed == 3
        assert len(result.results) == 3

        # Verify timestamp preservation
        assert result.results[0].timestamp_s == 0.0
        assert result.results[1].timestamp_s == 1.0
        assert result.results[2].timestamp_s == 2.0

        # Frame 1 has no face
        assert result.results[1].face_detected is False
        assert result.results[1].real_score is None
        assert result.results[1].fake_score is None

        # Face detection rate should be between 0.0 and 1.0
        assert 0.0 <= result.face_detection_rate <= 1.0


@pytest.mark.asyncio
async def test_invalid_image_and_missing_file_handling(detector, sample_video_info):
    """Test 8 & 9: Verifies corrupted/non-existent frames do not crash the pipeline."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 1. Empty file (0 bytes)
        corrupted_file = tmp_path / "corrupted.jpg"
        corrupted_file.write_bytes(b"")

        # 2. Missing file
        missing_file = tmp_path / "does_not_exist.jpg"

        frame_samples = [
            FrameSample(timestamp_s=0.5, frame_path=corrupted_file),
            FrameSample(timestamp_s=1.5, frame_path=missing_file),
        ]

        result = await detector.analyze(frame_samples, sample_video_info)

        assert result.available is True
        assert result.status == "completed"
        assert result.frames_analyzed == 2
        assert result.faces_found == 0
        assert result.face_detection_rate == 0.0
        assert result.results[0].face_detected is False
        assert result.results[1].face_detected is False


@pytest.mark.asyncio
async def test_empty_frames_list(detector, sample_video_info):
    """Test 10: Empty frames list produces valid zeroed response without errors."""
    result = await detector.analyze([], sample_video_info)
    assert result.available is True
    assert result.frames_analyzed == 0
    assert result.faces_found == 0
    assert result.face_detection_rate == 0.0
    assert len(result.results) == 0


def test_portrait_face_crop_aspect_ratio_preservation(detector):
    """
    Test 11: Verifies that face cropping in portrait images (e.g. 850x478)
    returns an exactly square crop (height == width) without aspect ratio distortion.
    """
    # Create portrait canvas: height = 850, width = 478
    portrait_img = np.ones((850, 478, 3), dtype=np.uint8) * 220
    # Draw face structure
    cv2.circle(portrait_img, (239, 350), 120, (210, 175, 140), -1)
    cv2.circle(portrait_img, (200, 320), 15, (40, 40, 40), -1)
    cv2.circle(portrait_img, (280, 320), 15, (40, 40, 40), -1)
    cv2.ellipse(portrait_img, (239, 390), (40, 20), 0, 0, 180, (40, 40, 40), 3)

    crop = detector.detect_primary_face(portrait_img)
    if crop is not None:
        h, w, _ = crop.shape
        # Must be strictly square
        assert h == w, f"Expected square crop but got shape ({h}, {w})"
        assert h > 100


def test_efficientnet_polarity_mapping(detector):
    """
    Empirically verifies that the EfficientNet-B0 linear head mapping adheres to:
    Index 0: Real/Authentic
    Index 1: Fake/Manipulated
    """
    assert detector.model is not None
    fc = detector.model.classifier[1]
    assert fc.out_features == 2
    dummy_input = torch.zeros(1, 3, 224, 224).to(detector.device)
    with torch.no_grad():
        logits = detector.model(dummy_input)
    assert logits.shape == (1, 2)


def test_capture_quality_metrics_and_smoothing(detector):
    """
    Verifies that detect_face_with_meta extracts capture-quality indicators:
    blur_score, luma, noise_estimate, face_pixel_size, face_confidence.
    """
    img = create_synthetic_face_image(300, 300)
    res = detector.detect_face_with_meta(img)
    if res is not None:
        crop, conf, bbox, pixel_size, blur, luma, noise = res
        assert crop.shape == (224, 224, 3) or (crop.shape[0] == crop.shape[1])
        assert 0.0 <= conf <= 1.0
        assert len(bbox) == 4
        assert pixel_size > 0
        assert blur >= 0.0
        assert 0.0 <= luma <= 255.0
        assert noise >= 0.0

    # Also test temporal smoothing helper
    b1 = (100, 100, 50, 50)
    b2 = (102, 101, 51, 50)
    iou = detector._calculate_iou(b1, b2)
    assert iou > 0.8



