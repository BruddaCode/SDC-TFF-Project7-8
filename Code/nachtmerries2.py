# lijpe handel voor een custom roi

import cv2
import numpy as np

video_path = "30-04-2026_beelden_Corne/left.mp4"

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Could not open video file: {video_path}")
    raise SystemExit(1)


def _noop(_):
    pass


trackbars_ready = False
controls_window = "Controls"
paused = False
current_frame = None

while True:
    if not paused:
        ret, frame = cap.read()
        if not ret:
            break
        current_frame = frame
    else:
        frame = current_frame

    height, width = frame.shape[:2]

    if not trackbars_ready:
        cv2.namedWindow(controls_window)

        cv2.createTrackbar("x1", controls_window, 100, width - 1, _noop)
        cv2.createTrackbar("y1", controls_window, 100, height - 1, _noop)
        cv2.createTrackbar("x2", controls_window, min(500, width - 1), width - 1, _noop)
        cv2.createTrackbar("y2", controls_window, min(200, height - 1), height - 1, _noop)
        cv2.createTrackbar("x3", controls_window, min(300, width - 1), width - 1, _noop)
        cv2.createTrackbar("y3", controls_window, min(300, height - 1), height - 1, _noop)
        cv2.createTrackbar("x4", controls_window, 100, width - 1, _noop)
        cv2.createTrackbar("y4", controls_window, min(300, height - 1), height - 1, _noop)
        cv2.createTrackbar("threshold", controls_window, 128, 255, _noop)

        trackbars_ready = True

    x1 = cv2.getTrackbarPos("x1", controls_window)
    y1 = cv2.getTrackbarPos("y1", controls_window)
    x2 = cv2.getTrackbarPos("x2", controls_window)
    y2 = cv2.getTrackbarPos("y2", controls_window)
    x3 = cv2.getTrackbarPos("x3", controls_window)
    y3 = cv2.getTrackbarPos("y3", controls_window)
    x4 = cv2.getTrackbarPos("x4", controls_window)
    y4 = cv2.getTrackbarPos("y4", controls_window)
    threshold_value = cv2.getTrackbarPos("threshold", controls_window)

    roi = np.array([[x1, y1], [x2, y2], [x3, y3], [x4, y4]], np.int32)
    roi = roi.reshape((-1, 1, 2))
    
    mask = np.zeros((height, width), dtype=np.uint8)
    
    cv2.fillPoly(mask, [roi], 255)
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # black and white filter
    _, filtered = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
    filtered = cv2.cvtColor(filtered, cv2.COLOR_GRAY2BGR)
    
    overlay = frame.copy()
    overlay[mask == 255] = filtered[mask == 255]
    cv2.polylines(overlay, [roi], isClosed=True, color=(0, 255, 0), thickness=2)
    cv2.line(overlay, (135, 0), (1130, 720), (255, 0, 0), 2)
    
    # Display pause status
    status_text = "PAUSED" if paused else "PLAYING"
    cv2.putText(overlay, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255 if paused else 0, 255 if paused else 0), 2)

    cv2.imshow('Overlay', overlay)
    
    key = cv2.waitKey(30) & 0xFF
    if key == ord('q'):
        break
    elif key == ord(' '):  # spacebar to toggle pause
        paused = not paused


cap.release()
cv2.destroyAllWindows()
