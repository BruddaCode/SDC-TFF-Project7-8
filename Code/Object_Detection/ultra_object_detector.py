"""
ultra_object_detector.py
Object Detection Script
Uses Ultralytics YOLO with a .pt or .onnx model.
Supports both camera input (by ID) and video file input.
"""

import cv2
import time
from pathlib import Path
from ultralytics.models.yolo.model import YOLO


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

# ── Configuration ─────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
# MODEL_PATH  = SCRIPT_DIR / "OriginalDetection" / "ultra_object_detector_3000.pt"
# MODEL_PATH  = SCRIPT_DIR / "TheNewModel" / "sdc_yolov8n3-5" / "weights" / "best.pt"
MODEL_PATH  = SCRIPT_DIR / "TheNewModel" / "sdc_yolov8n3-5" / "weights" / "best_openvino_model"

# Set VIDEO_SOURCE to:
#   0, 1, 2 ...  for a camera (0 = default/built-in, 1 = first external, etc.)
#   "path/to/video.mp4"  for a video file
# VIDEO_SOURCE = 0
# VIDEO_SOURCE = SCRIPT_DIR / "UselessVideos" / "corne.mp4"
VIDEO_SOURCE = SCRIPT_DIR / "middle.mp4"
OUTPUT_FILE = SCRIPT_DIR / "UselessVideos" / "NewModelTesting2" / "NewModelSecondTest.mp4"
# Set OUTPUT_FILE = None to disable saving

CONF_THRESH = 0.05

CAMERA_RESOLUTION = (1280, 720)  # (width, height) for camera capture
# ─────────────────────────────────────────────────────────────────────────────


# ── Drawing helper ────────────────────────────────────────────────────────────

def draw_detections(frame, results, model):
    boxes = results[0].boxes
    for box in boxes:
        cls          = int(box.cls[0])
        conf         = float(box.conf[0])
        x1,y1,x2,y2 = map(int, box.xyxy[0])
        label        = model.names[cls]
        color        = CLASS_COLORS.get(label, DEFAULT_COLOR)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        text = f"{label} {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 2, y1), color, -1)
        cv2.putText(frame, text, (x1 + 1, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return frame, len(boxes)


def main():
    # ── Validate model path ───────────────────────────────────────────────────
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    # ── Validate video source ─────────────────────────────────────────────────
    is_camera = isinstance(VIDEO_SOURCE, int)

    if not is_camera:
        video_path = Path(VIDEO_SOURCE)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        source_label = video_path.name
    else:
        source_label = f"Camera ID {VIDEO_SOURCE}"

    # ── Load model ────────────────────────────────────────────────────────────
    print(f"[INFO] Loading model from: {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))
    print(f"[INFO] Classes: {list(model.names.values())}")

    # ── Open capture ──────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_RESOLUTION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_RESOLUTION[1])
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open source: {source_label}")

    src_fps      = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if not is_camera else -1

    if is_camera:
        print(f"[INFO] Source: {source_label}")
    else:
        print(f"[INFO] Source: {source_label}  |  {total_frames} frames @ {src_fps:.1f} fps")

    # ── Ensure output folder exists ───────────────────────────────────────────
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

            t0      = time.perf_counter()
            results = model(frame, conf=CONF_THRESH, verbose=False, task="detect")
            elapsed = time.perf_counter() - t0

            fps        = 1.0 / elapsed if elapsed > 0 else 0
            fps_accum += fps
            frame_count += 1

            result, n_det = draw_detections(frame.copy(), results, model)
            cv2.putText(result, f"FPS: {fps:.1f}  Objects: {n_det}",
                        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Initialise writer on first frame
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


if __name__ == "__main__":
    main()
