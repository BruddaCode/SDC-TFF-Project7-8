# lijpe handel voor een custom roi

import os
import cv2
import numpy as np

video_path = "2026-04-02-test3-720/left.mp4"


def has_display() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


show_preview = has_display()
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Could not open video file: {video_path}")
    raise SystemExit(1)

if not show_preview:
    print("No graphical display detected. Running in headless mode (no cv2.imshow).")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    height, width = frame.shape[:2]
    roi = np.array([[100, 100], [300, 100], [300, 300], [100, 300]], np.int32)
    roi = roi.reshape((-1, 1, 2))
    
    mask = np.zeros((height, width), dtype=np.uint8)
    
    cv2.fillPoly(mask, [roi], 255)
    
    result = cv2.bitwise_and(frame, frame, mask=mask)
    
    x,y,w,h = cv2.boundingRect(roi)
    roi_crop = result[y:y+h, x:x+w]

    if show_preview:
        cv2.imshow('ROI Crop', roi_crop)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    else:
        output_path = "roi_crop_headless.png"
        cv2.imwrite(output_path, roi_crop)
        print(f"Saved ROI preview to {output_path}")
        break

cap.release()

if show_preview:
    cv2.destroyAllWindows()
