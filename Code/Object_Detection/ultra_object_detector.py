"""
ultra_object_detector.py
Object Detection Script
Uses Ultralytics YOLO with a .pt or .onnx model.
Supports both camera input (by ID) and video file input.
"""

import cv2
import time
import numpy as np
from pathlib import Path
from ultralytics.models.yolo.model import YOLO
from line_detection.StereoCamera import StereoCamera
import threading


# ── Custom class colours (BGR) ────────────────────────────────────────────────
CLASS_COLORS = {
    "car":                  (200, 100,   0),
    "one-way-left":         (255, 200,   0),
    "sign-left-only":       (255, 150,   0),
    "speed-sign-20":        (  0, 200, 255),
    "speed-sign-30":        (  0, 150, 255),
    "stop-sign":            (  0,   0, 220),
    "traffic-light-green":  (  0, 200,   0),
    "traffic-light-red":    (  0,   0, 255),
    "traffic-light-off":    (100, 100, 100),
    "zebra-crossing":       (255, 255,   0),
    "person":               ( 50, 200,  50),
}
DEFAULT_COLOR = (200, 200, 200)

# ── Calibration data (from your calibration run) ──────────────────────────────
CAMERA_MATRIX = np.array([
    [1.42576401e+03, 0.00000000e+00, 9.48147834e+02],
    [0.00000000e+00, 1.42099141e+03, 5.91695278e+02],
    [0.00000000e+00, 0.00000000e+00, 1.00000000e+00],
], dtype=np.float64)

DIST_COEFFS = np.array(
    [[ 0.0284335, -0.15193021, 0.00601368, 0.00274577, 0.13006665]],
    dtype=np.float64
)

# Focal lengths in pixels (directly from camera matrix — no sensor guesswork)
# Calibration was done at 1920x1080 but we capture at 1280x720.
# Focal lengths must be scaled down proportionally otherwise distances
# read ~1.5x too far (which is exactly the bug we were seeing).
CALIB_WIDTH  = 1920
CALIB_HEIGHT = 1080
CAMERA_RESOLUTION = (1280, 720)
CAPTURE_WIDTH, CAPTURE_HEIGHT = CAMERA_RESOLUTION  # 1280, 720

FX = CAMERA_MATRIX[0, 0] * (CAPTURE_WIDTH  / CALIB_WIDTH)   # 1425.76 -> 950.5 px
FY = CAMERA_MATRIX[1, 1] * (CAPTURE_HEIGHT / CALIB_HEIGHT)  # 1420.99 -> 947.3 px

# ── Real-world object sizes (metres) ─────────────────────────────────────────
# (real_size_m, use_height)
#   use_height=False  →  use bbox width  + FX
#   use_height=True   →  use bbox height + FY
#
# Person: using average standing height 1.75m with FY gives reliable results
# when most of the body is in frame. Much better than shoulder width.
OBJECT_REAL_SIZE = {
    "car":                  (1.80, False),  # avg car width ~1.8m
    "one-way-left":         (0.45, False),  # road sign ~45cm wide
    "sign-left-only":       (0.45, False),
    "speed-sign-20":        (0.40, False),  # speed sign ~40cm diameter
    "speed-sign-30":        (0.40, False),
    "stop-sign":            (0.60, False),  # stop sign ~60cm
    "traffic-light-green":  (0.25, True),   # full light housing ~25cm tall
    "traffic-light-red":    (0.25, True),
    "traffic-light-off":    (0.25, True),
    "zebra-crossing":       (3.00, False),  # crossing ~3m wide
    "person":               (1.75, True),   # avg person height ~1.75m
}


def estimate_distance(label: str, bbox_w_px: int, bbox_h_px: int):
    """
    Estimate distance using the calibrated focal length (pixels):
        distance = (real_size_m * focal_length_px) / bbox_size_px

    Uses FX with bbox width for wide objects, FY with bbox height for tall ones.
    Returns None if class not in OBJECT_REAL_SIZE.
    """
    if label not in OBJECT_REAL_SIZE:
        return None
    real_size_m, use_height = OBJECT_REAL_SIZE[label]
    if use_height:
        bbox_size_px = bbox_h_px
        focal_px     = FY
    else:
        bbox_size_px = bbox_w_px
        focal_px     = FX
    if bbox_size_px <= 0:
        return None
    distance = (real_size_m * focal_px) / bbox_size_px
    return round(distance, 1)


# ── Configuration ─────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
# MODEL_PATH  = SCRIPT_DIR / "OriginalDetection" / "ultra_object_detector_3000.pt"
# MODEL_PATH  = SCRIPT_DIR / "TheNewModel" / "sdc_yolov8n3-5" / "weights" / "best.pt"
MODEL_PATH  = SCRIPT_DIR / "TheNewModel" / "sdc_yolov8n3-5" / "weights" / "best_openvino_model"

VIDEO_SOURCE = 4
# VIDEO_SOURCE = SCRIPT_DIR / "UselessVideos" / "corne.mp4"
OUTPUT_FILE  = SCRIPT_DIR / "UselessVideos" / "NewModelTesting2" / "NewModelMenTest.mp4"
# Set OUTPUT_FILE = None to disable saving

CONF_THRESH       = 0.05
CAMERA_RESOLUTION = (1280, 720)

CORNER_LEN   = 18  # corner tick length in pixels
CORNER_THICK = 3   # corner tick thickness
# ─────────────────────────────────────────────────────────────────────────────


# ── Undistort map (built once at startup) ─────────────────────────────────────
# Pre-computing the remap is much faster than calling undistort() per frame.
_UNDISTORT_MAP = None

def build_undistort_map(w: int, h: int):
    global _UNDISTORT_MAP
    new_mtx, roi = cv2.getOptimalNewCameraMatrix(
        CAMERA_MATRIX, DIST_COEFFS, (w, h), alpha=0, newImgSize=(w, h)
    )
    map1, map2 = cv2.initUndistortRectifyMap(
        CAMERA_MATRIX, DIST_COEFFS, None, new_mtx, (w, h), cv2.CV_16SC2
    )
    _UNDISTORT_MAP = (map1, map2)
    return new_mtx

def undistort_frame(frame: np.ndarray) -> np.ndarray:
    if _UNDISTORT_MAP is None:
        return frame
    return cv2.remap(frame, _UNDISTORT_MAP[0], _UNDISTORT_MAP[1], cv2.INTER_LINEAR)


# ── Drawing helpers ───────────────────────────────────────────────────────────

def draw_corner_box(frame, x1, y1, x2, y2, color,
                    thickness=CORNER_THICK, length=CORNER_LEN):
    """Draw corner-only bounding box edges instead of a full rectangle."""
    # Top-left
    cv2.line(frame, (x1, y1), (x1 + length, y1),         color, thickness)
    cv2.line(frame, (x1, y1), (x1,          y1 + length), color, thickness)
    # Top-right
    cv2.line(frame, (x2, y1), (x2 - length, y1),         color, thickness)
    cv2.line(frame, (x2, y1), (x2,          y1 + length), color, thickness)
    # Bottom-left
    cv2.line(frame, (x1, y2), (x1 + length, y2),         color, thickness)
    cv2.line(frame, (x1, y2), (x1,          y2 - length), color, thickness)
    # Bottom-right
    cv2.line(frame, (x2, y2), (x2 - length, y2),         color, thickness)
    cv2.line(frame, (x2, y2), (x2,          y2 - length), color, thickness)


def draw_detections(frame, results, model):
    boxes = results[0].boxes
    for box in boxes:
        cls          = int(box.cls[0])
        conf         = float(box.conf[0])
        x1,y1,x2,y2 = map(int, box.xyxy[0])
        label        = model.names[cls]
        color        = CLASS_COLORS.get(label, DEFAULT_COLOR)

        bbox_w = x2 - x1
        bbox_h = y2 - y1

        draw_corner_box(frame, x1, y1, x2, y2, color)

        dist     = estimate_distance(label, bbox_w, bbox_h)
        dist_str = f"  {dist}m" if dist is not None else ""
        text     = f"{label} {conf:.2f}{dist_str}"

        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 2, y1), color, -1)
        cv2.putText(frame, text, (x1 + 1, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return frame, len(boxes)


class ObjectDetector(threading.Thread):
    def __init__(self, model_path, conf_thresh=0.05, camera=None, video_path=None):
        super().__init__()
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        print(f"[INFO] Loading model from: {model_path}")
        self.model = YOLO(str(model_path))
        print(f"[INFO] Classes: {list(self.model.names.values())}")
        
        self.conf_thresh = conf_thresh
        
        if video_path is not None:
            self.cap = cv2.VideoCapture(video_path)
            print(f"[INFO] Video {video_path} initialized.")
        elif camera is not None:
            self.cam = camera
            print(f"[INFO] Camera initialized.")
        else:
            raise ValueError("Either camera or video_path must be provided.")
    
    def object_detector(self, frame):
        frame = undistort_frame(frame)
        results = self.model(frame, conf=self.conf_thresh, verbose=False, task="detect")
        result, n_det = draw_detections(frame.copy(), results, self.model)
        return result, n_det

def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    is_camera = isinstance(VIDEO_SOURCE, int)
    if not is_camera:
        video_path = Path(VIDEO_SOURCE)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        source_label = video_path.name
    else:
        source_label = f"Camera ID {VIDEO_SOURCE}"

    print(f"[INFO] Loading model from: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))
    print(f"[INFO] Classes: {list(model.names.values())}")
    print(f"[INFO] Calibrated focal lengths — fx: {FX:.1f}px  fy: {FY:.1f}px")

    cap = cv2.VideoCapture(VIDEO_SOURCE, cv2.CAP_V4L2)

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_RESOLUTION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_RESOLUTION[1])
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open source: {source_label}")

    src_fps      = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if not is_camera else -1

    # Build undistort maps at actual capture resolution
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    build_undistort_map(actual_w, actual_h)
    print(f"[INFO] Undistort map built for {actual_w}×{actual_h}")

    if is_camera:
        print(f"[INFO] Source: {source_label}")
    else:
        print(f"[INFO] Source: {source_label}  |  {total_frames} frames @ {src_fps:.1f} fps")

    if OUTPUT_FILE is not None:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    writer      = None
    frame_count = 0
    fps_accum   = 0.0

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Apply lens distortion correction using calibration data
            frame = undistort_frame(frame)

            t0      = time.perf_counter()
            results = model(frame, conf=CONF_THRESH, verbose=False, task="detect")
            elapsed = time.perf_counter() - t0

            fps        = 1.0 / elapsed if elapsed > 0 else 0
            fps_accum += fps
            frame_count += 1

            result, n_det = draw_detections(frame.copy(), results, model)
            cv2.putText(result, f"FPS: {fps:.1f}  Objects: {n_det}",
                        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            if OUTPUT_FILE is not None and writer is None:
                h, w   = result.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(str(OUTPUT_FILE), fourcc, src_fps, (w, h))

            if writer:
                writer.write(result)

            cv2.imshow(f"Object Detector — {source_label}  [q to quit]", result)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("[INFO] Quit key pressed.")
                break

            if frame_count % 50 == 0:
                if is_camera:
                    print(f"[INFO] Frame {frame_count}  |  FPS {fps:.1f}")
                else:
                    print(f"[INFO] Frame {frame_count}/{total_frames}  |  FPS {fps:.1f}")

    finally:
        cap.release()
        if writer:
            writer.release()
            print(f"[INFO] Saved output to: {OUTPUT_FILE}")
        cv2.destroyAllWindows()

    if frame_count:
        print(f"[INFO] Processed {frame_count} frames | Avg FPS: {fps_accum / frame_count:.1f}")


# if __name__ == "__main__":
#     main()
