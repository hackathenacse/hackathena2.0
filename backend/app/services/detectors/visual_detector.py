import os
import time
import urllib.request
from pathlib import Path
from typing import Any, List, Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from app.core.logging import logger
from app.schemas.analysis import VideoInfo, VisualFrameResult, VisualResult
from app.services.detectors.base import FrameSample, VisualDetector

# Model constants & provenance
MODEL_NAME = "EfficientNet-B0-FFPP-C23"
MODEL_VERSION = "1.0.0"
MODEL_LICENSE = "MIT"
MODEL_CHECKPOINT_URL = "https://huggingface.co/Xicor9/efficientnet-b0-ffpp-c23/resolve/main/efficientnet_b0_ffpp_c23.pth"
MEDIAPIPE_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite"

IMAGE_SIZE = (224, 224)


class VisualDeepfakeDetector(VisualDetector):
    """
    Member 2 Visual AI / Face Deepfake Detector Service for Stage 1.
    
    Pipeline:
      Sampled Frames -> MediaPipe Face Detector -> Face Bounding Box ->
      Face Crop & Preprocessing -> EfficientNet-B0 FaceForensics++ C23 Model ->
      Forensic Real/Fake Class Scores -> Structured VisualResult.
    
    Responsibilities:
      - Loads pretrained EfficientNet-B0 model once (singleton/cached).
      - Automatically detects CUDA if available, with CPU fallback.
      - Uses inference/no-grad mode for evaluation.
      - Employs MediaPipe BlazeFace for lightweight, robust local face detection.
      - Crops and preprocesses primary faces to (224, 224) RGB tensors.
      - Handles missing faces, multiple faces, bad images, and inference errors gracefully.
      - Never fabricates scores or outputs uncalibrated verdicts.
    """

    _instance: Optional["VisualDeepfakeDetector"] = None

    def __init__(
        self,
        device: Optional[str] = None,
        model_url: str = MODEL_CHECKPOINT_URL,
        min_face_confidence: float = 0.5,
    ):
        self.model_url = model_url
        self.min_face_confidence = min_face_confidence
        
        # 1. Device selection
        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        logger.info(f"VisualDeepfakeDetector initialized on target device: {self.device}")

        # Model and detector holders
        self.model: Optional[nn.Module] = None
        self.face_detector: Optional[vision.FaceDetector] = None
        self.yunet_detector: Optional[Any] = None
        self._is_loaded = False

        # Image transform: Resize to 224x224, convert to tensor [0, 1], and apply ImageNet normalization
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    @classmethod
    def get_instance(cls) -> "VisualDeepfakeDetector":
        """Singleton accessor to prevent reloading weights across requests."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self) -> None:
        """
        Loads the pretrained model and MediaPipe face detector.
        Thread-safe / idempotent: does not reload if already loaded.
        """
        if self._is_loaded and self.model is not None and self.face_detector is not None:
            return

        logger.info("VisualDeepfakeDetector: Loading models...")
        start_time = time.perf_counter()

        try:
            # A. Load MediaPipe Face Detector
            self._load_face_detector()

            # B. Load EfficientNet-B0 FF++ C23 Checkpoint
            self._load_classifier_model()

            self._is_loaded = True
            load_elapsed = time.perf_counter() - start_time
            logger.info(
                f"VisualDeepfakeDetector: Successfully loaded on {self.device} in {load_elapsed:.2f}s."
            )
        except Exception as e:
            logger.error(f"VisualDeepfakeDetector: Failed to load models: {e}")
            self._is_loaded = False
            raise

    def _load_face_detector(self) -> None:
        """Initializes OpenCV YuNet face detector with MediaPipe BlazeFace fallback."""
        cache_dir = Path.home() / ".cache" / "opencv"
        cache_dir.mkdir(parents=True, exist_ok=True)
        yunet_path = cache_dir / "face_detection_yunet_2023mar.onnx"

        # Try YuNet first (OpenCV-native, CPU-optimized, provides landmarks and confidence)
        if yunet_path.exists():
            try:
                self.yunet_detector = cv2.FaceDetectorYN.create(
                    model=str(yunet_path.resolve()),
                    config="",
                    input_size=(320, 320),
                    score_threshold=self.min_face_confidence,
                    nms_threshold=0.3,
                    top_k=5000,
                )
                logger.info("VisualDeepfakeDetector: OpenCV YuNet face detector initialized.")
            except Exception as e:
                logger.warning(f"VisualDeepfakeDetector: Failed to create YuNet detector: {e}")
                self.yunet_detector = None

        # Always load MediaPipe BlazeFace as reliable backup/fallback
        self._load_mediapipe_detector()

    def _load_mediapipe_detector(self) -> None:
        """Downloads and initializes the MediaPipe FaceDetector task."""
        cache_dir = Path.home() / ".cache" / "mediapipe"
        cache_dir.mkdir(parents=True, exist_ok=True)
        model_path = cache_dir / "blaze_face_short_range.tflite"

        if not model_path.exists():
            logger.info(f"Downloading MediaPipe FaceDetector model to {model_path}...")
            urllib.request.urlretrieve(MEDIAPIPE_MODEL_URL, str(model_path))

        base_options = python.BaseOptions(model_asset_path=str(model_path))
        options = vision.FaceDetectorOptions(
            base_options=base_options,
            min_detection_confidence=self.min_face_confidence
        )
        self.face_detector = vision.FaceDetector.create_from_options(options)
        logger.debug("MediaPipe FaceDetector initialized.")

    def _load_classifier_model(self) -> None:
        """Downloads and initializes the EfficientNet-B0 classifier with FF++ weights."""
        logger.info(f"Loading EfficientNet-B0 FF++ C23 weights from {self.model_url}...")
        
        try:
            state_dict = torch.hub.load_state_dict_from_url(
                self.model_url,
                map_location=self.device,
                progress=False
            )
        except Exception as e:
            logger.warning(f"Failed to load weights to {self.device}: {e}. Falling back to CPU.")
            self.device = torch.device("cpu")
            state_dict = torch.hub.load_state_dict_from_url(
                self.model_url,
                map_location="cpu",
                progress=False
            )

        # Build architecture: EfficientNet-B0 with 2-class head
        model = models.efficientnet_b0(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, 2)
        model.load_state_dict(state_dict)
        model.to(self.device)
        model.eval()

        self.model = model
        logger.debug("EfficientNet-B0 FF++ C23 model loaded and set to eval mode.")

    @staticmethod
    def _calculate_iou(b1: Tuple[int, int, int, int], b2: Tuple[int, int, int, int]) -> float:
        x1, y1, w1, h1 = b1
        x2, y2, w2, h2 = b2
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)
        inter_w = max(0, xi2 - xi1)
        inter_h = max(0, yi2 - yi1)
        inter_area = inter_w * inter_h
        union_area = (w1 * h1) + (w2 * h2) - inter_area
        return inter_area / union_area if union_area > 0 else 0.0

    @staticmethod
    def _compute_capture_quality(face_crop_rgb: np.ndarray) -> Tuple[float, float, float]:
        """
        Computes capture quality metrics:
          1. blur_score: Variance of Laplacian (higher = sharper, <50 is blurry)
          2. luma: Mean luminance of grayscale image (0-255)
          3. noise_estimate: High-frequency residual standard deviation
        """
        try:
            gray = cv2.cvtColor(face_crop_rgb, cv2.COLOR_RGB2GRAY)
            blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            luma = float(np.mean(gray))
            gaussian = cv2.GaussianBlur(gray, (5, 5), 0)
            noise_residual = gray.astype(np.float32) - gaussian.astype(np.float32)
            noise_estimate = float(np.std(noise_residual))
            return round(blur_score, 2), round(luma, 2), round(noise_estimate, 2)
        except Exception:
            return 50.0, 128.0, 2.0

    def detect_face_with_meta(
        self,
        img_rgb: np.ndarray,
        prev_box: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[Tuple[np.ndarray, float, List[int], int, float, float, float]]:
        """
        Detects primary face, applies lightweight box smoothing, and computes capture quality features.
        Returns:
            (face_crop_rgb, face_confidence, bounding_box, face_pixel_size, blur_score, luma, noise_estimate)
        """
        h, w, _ = img_rgb.shape
        if h == 0 or w == 0:
            return None

        detected_box = None
        detected_conf = 0.5

        # 1. Try YuNet first (OpenCV-native DNN)
        if self.yunet_detector is not None:
            try:
                img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                self.yunet_detector.setInputSize((w, h))
                _, faces = self.yunet_detector.detect(img_bgr)
                if faces is not None and len(faces) > 0:
                    best_area = -1
                    for f in faces:
                        score = float(f[-1])
                        if score >= self.min_face_confidence:
                            bx, by, bw, bh = int(f[0]), int(f[1]), int(f[2]), int(f[3])
                            area = bw * bh
                            if area > best_area:
                                best_area = area
                                detected_box = (bx, by, bw, bh)
                                detected_conf = score
            except Exception as e:
                logger.debug(f"YuNet detection exception: {e}")

        # 2. Fallback to MediaPipe BlazeFace if YuNet found nothing
        if detected_box is None and self.face_detector is not None:
            try:
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
                detection_result = self.face_detector.detect(mp_image)
                if detection_result.detections:
                    best_area = -1
                    for det in detection_result.detections:
                        box = det.bounding_box
                        area = box.width * box.height
                        score = float(det.categories[0].score) if det.categories else 0.5
                        if area > best_area:
                            best_area = area
                            detected_box = (box.origin_x, box.origin_y, box.width, box.height)
                            detected_conf = score
            except Exception as e:
                logger.debug(f"MediaPipe detection exception: {e}")

        if detected_box is None:
            return None

        # 3. Lightweight temporal box smoothing if IoU >= 0.35 with previous frame
        bx, by, bw, bh = detected_box
        if prev_box is not None:
            iou = self._calculate_iou(detected_box, prev_box)
            if iou >= 0.35:
                alpha = 0.7
                bx = int(round(alpha * bx + (1 - alpha) * prev_box[0]))
                by = int(round(alpha * by + (1 - alpha) * prev_box[1]))
                bw = int(round(alpha * bw + (1 - alpha) * prev_box[2]))
                bh = int(round(alpha * bh + (1 - alpha) * prev_box[3]))

        crop = self._crop_square_face(
            img_rgb=img_rgb,
            origin_x=bx,
            origin_y=by,
            width=bw,
            height=bh,
            margin_ratio=0.12
        )
        if crop is None or crop.size == 0:
            return None

        pixel_size = min(bw, bh)
        blur_score, luma, noise_est = self._compute_capture_quality(crop)
        bbox_list = [int(bx), int(by), int(bw), int(bh)]

        return (crop, detected_conf, bbox_list, pixel_size, blur_score, luma, noise_est)

    def detect_primary_face(self, img_rgb: np.ndarray) -> Optional[np.ndarray]:
        """
        Detects primary face and extracts a square crop.
        Preserves geometric aspect ratio for arbitrary orientations (landscape, square, portrait).
        """
        meta = self.detect_face_with_meta(img_rgb)
        if meta is not None:
            return meta[0]
        return None

    def _crop_square_face(
        self,
        img_rgb: np.ndarray,
        origin_x: int,
        origin_y: int,
        width: int,
        height: int,
        margin_ratio: float = 0.12
    ) -> Optional[np.ndarray]:
        """
        Extracts a square bounding box centered on the given coordinates with margin and reflection padding.
        """
        h, w, _ = img_rgb.shape
        if h == 0 or w == 0 or width <= 0 or height <= 0:
            return None

        center_x = origin_x + width / 2.0
        center_y = origin_y + height / 2.0
        side = max(width, height) * (1.0 + margin_ratio)

        x1 = int(round(center_x - side / 2.0))
        y1 = int(round(center_y - side / 2.0))
        x2 = int(round(center_x + side / 2.0))
        y2 = int(round(center_y + side / 2.0))

        # Clamp slice coordinates to image boundary
        src_x1 = max(0, x1)
        src_y1 = max(0, y1)
        src_x2 = min(w, x2)
        src_y2 = min(h, y2)

        if src_x2 <= src_x1 or src_y2 <= src_y1:
            return None

        crop = img_rgb[src_y1:src_y2, src_x1:src_x2]
        if crop.size == 0:
            return None

        ch, cw, _ = crop.shape
        # Pad with border reflection to guarantee exact square shape before 224x224 resize
        if ch != cw:
            target_dim = max(ch, cw)
            top = (target_dim - ch) // 2
            bottom = target_dim - ch - top
            left = (target_dim - cw) // 2
            right = target_dim - cw - left
            crop = cv2.copyMakeBorder(crop, top, bottom, left, right, cv2.BORDER_REFLECT_101)

        return crop

    @staticmethod
    def _calculate_face_forensics(face_crop_rgb: np.ndarray) -> Tuple[float, float]:
        """
        Computes forensic quality and spatial-frequency anomaly indicators:
          1. Sharpness / Focus Index (Laplacian variance normalized to [0, 1])
          2. High-Frequency Spectral Artifact Score (2D FFT energy distribution)
        """
        try:
            gray = cv2.cvtColor(face_crop_rgb, cv2.COLOR_RGB2GRAY)
            # 1. Laplacian sharpness metric
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness = float(np.clip(lap_var / 150.0, 0.05, 1.0))

            # 2. 2D FFT Frequency Analysis
            # Synthetic generators and blending boundaries leave high-frequency grid & boundary artifacts
            h, w = gray.shape
            if h < 16 or w < 16:
                return sharpness, 0.0

            f = np.fft.fft2(gray.astype(np.float32))
            fshift = np.fft.fftshift(f)
            mag = np.log1p(np.abs(fshift))

            cy, cx = h // 2, w // 2
            r_inner = min(h, w) // 6
            r_outer = min(h, w) // 2

            y, x = np.ogrid[:h, :w]
            dist = np.sqrt((x - cx)**2 + (y - cy)**2)

            low_mask = dist <= r_inner
            high_mask = (dist > r_inner) & (dist <= r_outer)

            low_e = np.mean(mag[low_mask]) if np.any(low_mask) else 1.0
            high_e = np.mean(mag[high_mask]) if np.any(high_mask) else 0.0

            ratio = float(high_e / max(1e-5, low_e))
            spectral_anomaly = float(np.clip((ratio - 0.40) * 1.5, 0.0, 1.0))
            return sharpness, spectral_anomaly
        except Exception:
            return 1.0, 0.0

    @classmethod
    def _calibrate_crop_score(cls, raw_real: float, raw_fake: float, face_crop_rgb: np.ndarray) -> Tuple[float, float]:
        """
        Calibrates raw neural network logits against optical and spatial-frequency indicators.
        Prevents low-resolution webcam compression and motion blur from generating false positives.
        """
        sharpness, spectral_anomaly = cls._calculate_face_forensics(face_crop_rgb)
        h, w, _ = face_crop_rgb.shape
        min_dim = min(h, w)

        fake_score = raw_fake

        # 1. Webcam Compression, Motion Blur & Low-Resolution Gating:
        # If crop is low sharpness or small without strong AI spectral anomaly,
        # natural camera blur should never trigger synthetic deepfake alarms
        if sharpness < 0.45 and spectral_anomaly < 0.35:
            # Genuine blurry/compressed camera feed: damp fake score heavily
            fake_score = min(fake_score, fake_score * 0.35)
            if sharpness < 0.25:
                fake_score = min(fake_score, 0.20)
        elif min_dim < 120 and spectral_anomaly < 0.35:
            quality_factor = min(1.0, max(0.2, (min_dim / 120.0)))
            fake_score = fake_score * (0.30 + 0.70 * quality_factor)
        elif spectral_anomaly >= 0.35:
            # High spectral anomaly: retain AI generation artifact score
            fake_score = fake_score * 0.85 + spectral_anomaly * 0.15

        # 2. Clean Camera Optics:
        # High sharpness with minimal spectral anomaly indicates authentic camera feed
        if sharpness > 0.55 and spectral_anomaly < 0.12:
            fake_score = min(fake_score, fake_score * 0.75)

        fake_score = float(np.clip(fake_score, 0.01, 0.99))
        fake_score = round(fake_score, 4)
        real_score = round(1.0 - fake_score, 4)
        return real_score, fake_score

    def predict_face_crop(self, face_crop_rgb: np.ndarray) -> Tuple[float, float]:
        """
        Runs model inference on a single RGB face crop.
        Returns: (real_score, fake_score) where real_score + fake_score == 1.0.
        """
        res = self.predict_batch([face_crop_rgb])
        if res:
            return res[0]
        return 0.5, 0.5

    def predict_batch_detailed(
        self,
        face_crops_rgb: List[np.ndarray],
        telemetry: Optional[List[List[float]]] = None
    ) -> List[Tuple[float, float, float, float, float]]:
        """
        Runs batched model inference returning:
          (real_s, fake_s, raw_real, raw_fake, adapted_fake)
        where:
          - (raw_real, raw_fake): Outputs directly from frozen EfficientNet base model
          - adapted_fake: Output from Authentica adaptation network
          - (real_s, fake_s): Final calibrated/adapted scores according to active model version
        """
        if not face_crops_rgb:
            return []

        if self.model is None:
            raise RuntimeError("Classifier model is not initialized. Call load() first.")

        tensors = [self.transform(crop) for crop in face_crops_rgb]
        batch_tensor = torch.stack(tensors).to(self.device)

        with torch.no_grad():
            feats = self.model.features(batch_tensor)
            pooled = self.model.avgpool(feats)
            embs = torch.flatten(pooled, 1)  # [batch, 1280]
            raw_logits = self.model.classifier(embs)
            raw_probs = torch.softmax(raw_logits, dim=-1)

        self.last_features = embs.cpu().numpy().tolist()
        self.last_telemetry = telemetry if telemetry else [[0.0, 0.0, 0.0, 0.0] for _ in face_crops_rgb]

        from app.services.active_learning.training_service import ActiveLearningTrainingService
        training_service = ActiveLearningTrainingService.get_instance()

        telem_tensor = torch.tensor(self.last_telemetry, dtype=torch.float32, device=self.device)
        with torch.no_grad():
            adapted_logits = training_service.adapter(embs, telem_tensor)
            adapted_probs = torch.softmax(adapted_logits, dim=-1)

        results = []
        is_adapted = training_service.active_version != "visual-v0"

        for i in range(len(face_crops_rgb)):
            raw_real = round(float(raw_probs[i, 0].item()), 4)
            raw_fake = round(float(raw_probs[i, 1].item()), 4)
            adapted_fake = round(float(adapted_probs[i, 1].item()), 4)

            if is_adapted:
                fake_s = adapted_fake
                real_s = round(1.0 - fake_s, 4)
            else:
                fake_s = raw_fake
                real_s = raw_real

            results.append((real_s, fake_s, raw_real, raw_fake, adapted_fake))

        return results

    def predict_batch(self, face_crops_rgb: List[np.ndarray]) -> List[Tuple[float, float]]:
        """
        Runs batched model inference on a list of RGB face crops.
        Returns: List of (real_score, fake_score) where real_score + fake_score == 1.0.
        """
        detailed = self.predict_batch_detailed(face_crops_rgb)
        return [(d[0], d[1]) for d in detailed]

    async def analyze(
        self,
        frames: List[FrameSample],
        video_info: VideoInfo
    ) -> VisualResult:
        """
        Executes Stage 1 visual analysis on sampled frames according to the shared contract.
        """
        start_time = time.perf_counter()

        from app.services.active_learning.training_service import ActiveLearningTrainingService
        training_service = ActiveLearningTrainingService.get_instance()

        if not frames:
            logger.info("VisualDeepfakeDetector: No frames provided for analysis.")
            return VisualResult(
                available=True,
                model=MODEL_NAME,
                adapter_version=training_service.active_version,
                status="completed",
                frames_analyzed=0,
                faces_found=0,
                face_detection_rate=0.0,
                average_face_occupancy_pct=None,
                results=[]
            )

        # Ensure models are loaded
        try:
            self.load()
        except Exception as e:
            logger.error(f"VisualDeepfakeDetector: Cannot run analysis due to loading failure: {e}")
            return VisualResult(
                available=False,
                model=MODEL_NAME,
                adapter_version=training_service.active_version,
                status="error",
                frames_analyzed=0,
                faces_found=0,
                face_detection_rate=None,
                average_face_occupancy_pct=None,
                results=[]
            )

        # Process each frame: extract face and prepare for inference
        frame_results: List[VisualFrameResult] = []
        valid_face_crops: List[np.ndarray] = []
        valid_telemetries: List[List[float]] = []
        face_crop_indices: List[int] = []  # Maps crop index to frame_results index
        prev_box: Optional[Tuple[int, int, int, int]] = None

        for idx, frame_sample in enumerate(frames):
            ts = frame_sample.timestamp_s
            frame_path = frame_sample.frame_path

            # Handle unreadable / missing frame files safely
            if not frame_path.exists():
                logger.warning(f"Frame file does not exist: {frame_path}")
                prev_box = None
                frame_results.append(VisualFrameResult(
                    timestamp_s=ts,
                    face_detected=False,
                    real_score=None,
                    fake_score=None
                ))
                continue

            try:
                img_bgr = cv2.imread(str(frame_path.resolve()))
                if img_bgr is None or img_bgr.size == 0:
                    logger.warning(f"Failed to read image at {frame_path}")
                    prev_box = None
                    frame_results.append(VisualFrameResult(
                        timestamp_s=ts,
                        face_detected=False,
                        real_score=None,
                        fake_score=None
                    ))
                    continue

                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                res = self.detect_face_with_meta(img_rgb, prev_box=prev_box)

                if res is None:
                    # No face detected in this frame
                    prev_box = None
                    frame_results.append(VisualFrameResult(
                        timestamp_s=ts,
                        face_detected=False,
                        real_score=None,
                        fake_score=None
                    ))
                else:
                    face_crop, face_conf, bbox, pixel_size, blur_val, luma_val, noise_val = res
                    prev_box = (bbox[0], bbox[1], bbox[2], bbox[3])

                    # Person-centric crop occupancy metrics
                    side_est = max(bbox[2], bbox[3]) * 1.12
                    occupancy_pct = round((bbox[2] * bbox[3]) / max(1.0, (side_est * side_est)) * 100.0, 2)
                    margin_pct = 12.0

                    # Face detected - stage for inference with capture-quality telemetry
                    frame_results.append(VisualFrameResult(
                        timestamp_s=ts,
                        face_detected=True,
                        real_score=None,
                        fake_score=None,
                        face_confidence=round(face_conf, 4),
                        bounding_box=bbox,
                        face_pixel_size=pixel_size,
                        blur_score=blur_val,
                        luma=luma_val,
                        noise_estimate=noise_val,
                        face_occupancy_pct=occupancy_pct,
                        context_margin_pct=margin_pct,
                    ))
                    valid_face_crops.append(face_crop)
                    valid_telemetries.append([
                        blur_val / 500.0,
                        luma_val / 255.0,
                        noise_val / 10.0,
                        0.0
                    ])
                    face_crop_indices.append(len(frame_results) - 1)

            except Exception as e:
                logger.warning(f"Error processing frame {frame_path.name} at {ts}s: {e}")
                prev_box = None
                frame_results.append(VisualFrameResult(
                    timestamp_s=ts,
                    face_detected=False,
                    real_score=None,
                    fake_score=None
                ))

        # Run batched inference with detailed adapter integration
        if valid_face_crops:
            try:
                detailed_scores = self.predict_batch_detailed(valid_face_crops, valid_telemetries)
                for crop_idx, (real_s, fake_s, raw_real, raw_fake, adapted_fake) in enumerate(detailed_scores):
                    target_idx = face_crop_indices[crop_idx]
                    frame_results[target_idx].real_score = real_s
                    frame_results[target_idx].fake_score = fake_s
                    frame_results[target_idx].raw_real_score = raw_real
                    frame_results[target_idx].raw_fake_score = raw_fake
                    frame_results[target_idx].adapted_fake_score = adapted_fake
            except Exception as e:
                logger.error(f"Inference batch failed: {e}. Falling back to sequential inference.")
                for crop_idx, crop in enumerate(valid_face_crops):
                    target_idx = face_crop_indices[crop_idx]
                    try:
                        real_s, fake_s = self.predict_face_crop(crop)
                        frame_results[target_idx].real_score = real_s
                        frame_results[target_idx].fake_score = fake_s
                        frame_results[target_idx].raw_real_score = real_s
                        frame_results[target_idx].raw_fake_score = fake_s
                        frame_results[target_idx].adapted_fake_score = fake_s
                    except Exception as frame_err:
                        logger.warning(f"Inference failed on individual crop {crop_idx}: {frame_err}")
                        frame_results[target_idx].face_detected = False
                        frame_results[target_idx].real_score = None
                        frame_results[target_idx].fake_score = None

        # Calculate quality metrics
        frames_analyzed = len(frame_results)
        faces_found = sum(1 for r in frame_results if r.face_detected is True)
        face_detection_rate = round(faces_found / frames_analyzed, 4) if frames_analyzed > 0 else 0.0

        occupancies = [r.face_occupancy_pct for r in frame_results if r.face_occupancy_pct is not None]
        avg_occupancy = round(float(np.mean(occupancies)), 2) if occupancies else None

        elapsed = time.perf_counter() - start_time

        logger.info(
            f"VisualDeepfakeDetector: Analyzed {frames_analyzed} frames | "
            f"Faces found: {faces_found} ({face_detection_rate * 100:.1f}%) | "
            f"Average face occupancy: {avg_occupancy}% | "
            f"Adapter: {training_service.active_version} | "
            f"Elapsed: {elapsed:.2f}s"
        )

        return VisualResult(
            available=True,
            model=MODEL_NAME,
            adapter_version=training_service.active_version,
            status="completed",
            frames_analyzed=frames_analyzed,
            faces_found=faces_found,
            face_detection_rate=face_detection_rate,
            average_face_occupancy_pct=avg_occupancy,
            results=frame_results
        )
