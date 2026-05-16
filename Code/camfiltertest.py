import cv2
import numpy as np
import time
import json
import os

# SOURCE_FOLDER = "30-04-2026_beelden_Corne"
# SOURCE_FOLDER = "30-04-2026_verlichte_baan"
SOURCE_FOLDER = "2026-04-02-test3-720"

SOURCE_L = f"{SOURCE_FOLDER}/left.mp4"
SOURCE_R = f"{SOURCE_FOLDER}/right.mp4"



camL = cv2.VideoCapture(SOURCE_L)
camR = cv2.VideoCapture(SOURCE_R)

# =========================
# PARAMETER EXPLANATION (provided by ChatGPT)
# =========================

# --- Blur ---
blur = (9, 9)
# Size of Gaussian kernel (must be odd numbers ideally, e.g. (9,9), (11,11))
# Larger = more smoothing → less noise BUT weaker / thicker edges
# Too large → lane lines get washed out

sigma = 15
# Standard deviation for Gaussian blur
# Higher = stronger blur effect
# Too high → destroys edge detail completely

# --- Thresholding (NOT for use with Canny) ---
contrast_thresholds = (200, 255)
# Binary threshold: pixels >200 → 255 (white), else 0
# Higher lower-bound → only very bright pixels kept
# Too high → dull lane lines disappear

# --- CLAHE (lighting correction) ---
clipLimit = 2.0
# Contrast limiting: higher = more aggressive contrast boost
# Too high → noise and artifacts get amplified

tileGridSize = (8, 8)
# Size of local regions for CLAHE
# Smaller tiles → more local contrast correction
# Too small → patchy / unnatural image

# --- Canny Edge Detection ---
canny_threshold1 = 50
# Lower threshold: sensitivity to weak edges
# Lower = more edges (including noise)

canny_threshold2 = 150
# Upper threshold: strong edge cutoff
# Higher = fewer but stronger edges
# Ratio between thresholds matters (usually ~1:2 or 1:3)

# --- Hough Transform ---
hough_threshold = 120
# Minimum number of votes to detect a line
# Higher = fewer, more confident lines
# Too high → misses real lines

minLineLength = 80
# Minimum length of a detected line (in pixels)
# Too high → short lane segments ignored

maxLineGap = 50
# Max gap between segments to connect into one line
# Too high → unrelated segments get merged

hough_pi = 180
# Angular resolution (np.pi / hough_pi)
# Higher value → finer angle precision but slower

# --- Region of Interest (ROI) ---
roi = (0, 225, 640, 255)
# Defines area of interest (likely bottom part of frame)
# Ignoring irrelevant regions improves stability

vertical_line_x = 320
horizontal_line_y = 225
# Likely reference lines (center / horizon)
# Used for filtering or splitting left/right lanes

# --- Morphological operations ---
canny_kernel = (3, 3)
# Kernel size for dilation/erosion
# Larger = stronger effect

canny_dilation_iterations = 1
# Expands edges (connects broken lines)
# Too much → thick, merged edges

canny_erosion_iterations = 1
# Shrinks edges (removes noise)
# Too much → deletes real edges

# --- HLS color filtering ---
hls_lower_bound = (0, 180, 0)
hls_upper_bound = (255, 255, 80)
# Filters "white-like" pixels:
# L (lightness) high → bright
# S (saturation) low → not colorful
# If lower L too high → dull lines disappear
# If upper S too high → non-white noise included

# --- Adaptive Threshold (alternative to Canny) ---
adaptive_range = 11
# Size of neighborhood used for thresholding (must be odd)
# Larger = more global behavior

adaptive_constant = 2
# Value subtracted from mean
# Higher → fewer white pixels

adaptive_threshold = 255
# Output value for pixels passing threshold

# =========================
# IMPORTANT WARNING
# =========================

# CANNY vs THRESHOLDING:
# ---------------------
# Canny already produces a binary edge image.
# Applying thresholding (adaptive or fixed) AFTER Canny:
#   → does nothing useful
#   → can even degrade edge quality
#
# So:
#   ✔ Use Canny OR thresholding
#   ❌ Do NOT use both in the same pipeline

enable_clahe = 0
enable_blur = 0
enable_canny = 0
enable_morph = 0
enable_threshold = 0
enable_adaptive_threshold = 0
enable_sobel = 0
# Sobel parameters
sobel_ksize = 5  # Kernel size for Sobel (must be odd: 1, 3, 5, 7...)
sobel_threshold = 100  # Threshold for Sobel output
roi_timing_total_ms = 0.0
roi_timing_call_count = 0
roi_timing_avg_ms = 0.0


def noop(_):
    pass


def is_video_file_source(source):
    return isinstance(source, str)


def read_synced_frames(left_capture, right_capture, sync_enabled):
    ret_left, frame_left = left_capture.read()
    ret_right, frame_right = right_capture.read()

    if not ret_left or not ret_right:
        return ret_left, frame_left, ret_right, frame_right

    if not sync_enabled:
        return ret_left, frame_left, ret_right, frame_right

    left_idx = int(left_capture.get(cv2.CAP_PROP_POS_FRAMES))
    right_idx = int(right_capture.get(cv2.CAP_PROP_POS_FRAMES))

    # Keep both file streams within 1 frame of each other.
    if left_idx > right_idx + 1:
        while left_idx > right_idx + 1:
            ret_right, frame_right = right_capture.read()
            if not ret_right:
                break
            right_idx = int(right_capture.get(cv2.CAP_PROP_POS_FRAMES))
    elif right_idx > left_idx + 1:
        while right_idx > left_idx + 1:
            ret_left, frame_left = left_capture.read()
            if not ret_left:
                break
            left_idx = int(left_capture.get(cv2.CAP_PROP_POS_FRAMES))

    return ret_left, frame_left, ret_right, frame_right

def ensure_odd(value):
    # Gaussian kernel size must be odd and at least 1.
    value = max(1, value)
    return value if value % 2 == 1 else value + 1


def ensure_odd_block_size(value):
    # Adaptive threshold block size must be odd and >= 3.
    value = max(3, value)
    return value if value % 2 == 1 else value + 1

def normalize_frame_size(frame, target_size):
    if frame.shape[1] == target_size[0] and frame.shape[0] == target_size[1]:
        return frame
    return cv2.resize(frame, target_size, interpolation=cv2.INTER_LINEAR)


def mirror_roi_x(roi_x, frame_width, roi_width):
    return max(0, frame_width - roi_x - roi_width)


def to_bgr(frame):
    if len(frame.shape) == 2:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    return frame


def add_label(frame, label):
    labeled = frame.copy()
    cv2.putText(labeled, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    return labeled

def filter_frame(frame):
        
    hls = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS)
    h, l, s = cv2.split(hls)
    
    # light normalization using histogram equalization
    if enable_clahe:
        l = cv2.createCLAHE(clipLimit=clipLimit, tileGridSize=tileGridSize).apply(l)
    
    hls = cv2.merge((h, l, s))
    frame = cv2.inRange(hls, hls_lower_bound, hls_upper_bound)
    frame = cv2.bitwise_and(l, l, mask=frame)
    
    # apply gaussian blur for less noise on the frame
    if enable_blur:
        frame = cv2.GaussianBlur(frame, blur, sigma)
    
    # canny edge detection to find edges in the frame
    if enable_canny:
        frame = cv2.Canny(frame, canny_threshold1, canny_threshold2)

    # sobel edge detection
    if enable_sobel:
        sobelx = cv2.Sobel(frame, cv2.CV_64F, 1, 0, ksize=sobel_ksize)
        sobely = cv2.Sobel(frame, cv2.CV_64F, 0, 1, ksize=sobel_ksize)
        sobelxy = np.sqrt(sobelx**2 + sobely**2)
        sobelxy = (sobelxy / sobelxy.max() * 255).astype(np.uint8)
        _, frame = cv2.threshold(sobelxy, sobel_threshold, 255, cv2.THRESH_BINARY)

    if enable_morph:
        kernel = np.ones(canny_kernel, np.uint8)
        frame = cv2.dilate(frame, kernel, iterations=canny_dilation_iterations)
        frame = cv2.erode(frame, kernel, iterations=canny_erosion_iterations)
    
    if enable_adaptive_threshold:
        frame = cv2.adaptiveThreshold(frame, adaptive_threshold, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, adaptive_range, adaptive_constant)

    # increase contrast by applying a binary threshold
    if enable_threshold:
        _, frame = cv2.threshold(frame, contrast_thresholds[0], contrast_thresholds[1], cv2.THRESH_BINARY)
    
    return frame
    
def intersect(A, B, x, y):
    if A[0] <= x <= B[0] or A[0]>= x >= B[0]:
        if A[0] == B[0]:
            return None
        a = (B[1]-A[1])/(B[0]-A[0])
        b = A[1] - a*A[0]
        if 0 <= a*x + b <= y:
            return (x, int(a*x + b))
    return None
    
def getIntersection(frame, line_x):
    x = max(0, min(frame.shape[1] - 1, line_x))
    y = horizontal_line_y
    
    intersections = []
    filtered = filter_frame(frame)
    filtered = cv2.filter2D(filtered, -1, np.array([[10, 5, 10],[5, 10, 5],[10, 5, 10]]))
    lines = cv2.HoughLinesP(filtered, 1, np.pi/hough_pi, hough_threshold, minLineLength=minLineLength, maxLineGap=maxLineGap)
    height, width, _ = frame.shape
    if lines is not None:
        for line in lines:  
            x1,y1,x2,y2 = line[0]  
            cv2.line(frame,(x1,y1),(x2,y2),(0,0,255),2)
            intersection = intersect((x1,y1), (x2,y2), x, height)
            if intersection is not None:    
                intersections.append(intersection)

    cv2.line(frame,(x,0),(x,height),(255,0,0),2)
    cv2.line(frame,(0,y),(width,y),(255,0,255),2)
    if intersections is not None and len(intersections) >= 2:
        lowest_intersection = max(intersections,)
        cv2.circle(frame, lowest_intersection, 10, (255,0,0), -1)
        return (lowest_intersection, frame)
    elif len(intersections) != 0:
        cv2.circle(frame, intersections[0], 10, (255,0,0), -1)
        return (intersections[0], frame)
    return (None, frame)


def apply_intersection_on_roi(main_frame, roi_rect, line_x):
    global roi_timing_total_ms, roi_timing_call_count, roi_timing_avg_ms
    start_time = time.perf_counter()

    x0, y0, w, h = roi_rect
    roi = main_frame[y0:y0 + h, x0:x0 + w]
    try:
        if roi.size == 0:
            return (None, main_frame)

        intersection, roi_with_detection = getIntersection(roi.copy(), line_x)

        # Place the processed ROI back onto the full-size frame for visualization.
        main_frame[y0:y0 + h, x0:x0 + w] = roi_with_detection
        cv2.rectangle(main_frame, (x0, y0), (x0 + w, y0 + h), (0, 255, 255), 2)

        if intersection is None:
            return (None, main_frame)

        global_intersection = (intersection[0] + x0, intersection[1] + y0)
        cv2.circle(main_frame, global_intersection, 10, (0, 255, 0), -1)
        return (global_intersection, main_frame)
    finally:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        roi_timing_total_ms += elapsed_ms
        roi_timing_call_count += 1
        roi_timing_avg_ms = roi_timing_total_ms / roi_timing_call_count

# Load saved parameters on startup BEFORE creating trackbars
def load_parameters(filename="parameters.json"):
    """Load trackbar parameters from a JSON file."""
    global enable_clahe, clipLimit, tileGridSize, hls_lower_bound, hls_upper_bound
    global enable_blur, blur, sigma, enable_canny, canny_threshold1, canny_threshold2
    global enable_morph, canny_kernel, canny_dilation_iterations, canny_erosion_iterations
    global enable_adaptive_threshold, adaptive_threshold, adaptive_range, adaptive_constant
    global enable_threshold, contrast_thresholds, hough_threshold, minLineLength, maxLineGap
    global hough_pi, vertical_line_x, horizontal_line_y, roi
    global enable_sobel, sobel_ksize, sobel_threshold
    
    if not os.path.exists(filename):
        print(f"No saved parameters found. Using defaults.")
        return
    
    try:
        with open(filename, 'r') as f:
            params = json.load(f)
        
        enable_clahe = params.get("enable_clahe", enable_clahe)
        clipLimit = params.get("clipLimit", clipLimit)
        tileGridSize = tuple(params.get("tileGridSize", tileGridSize))
        hls_lower_bound = tuple(params.get("hls_lower_bound", hls_lower_bound))
        hls_upper_bound = tuple(params.get("hls_upper_bound", hls_upper_bound))
        enable_blur = params.get("enable_blur", enable_blur)
        blur = tuple(params.get("blur", blur))
        sigma = params.get("sigma", sigma)
        enable_canny = params.get("enable_canny", enable_canny)
        canny_threshold1 = params.get("canny_threshold1", canny_threshold1)
        canny_threshold2 = params.get("canny_threshold2", canny_threshold2)
        enable_morph = params.get("enable_morph", enable_morph)
        canny_kernel = tuple(params.get("canny_kernel", canny_kernel))
        canny_dilation_iterations = params.get("canny_dilation_iterations", canny_dilation_iterations)
        canny_erosion_iterations = params.get("canny_erosion_iterations", canny_erosion_iterations)
        enable_adaptive_threshold = params.get("enable_adaptive_threshold", enable_adaptive_threshold)
        adaptive_threshold = params.get("adaptive_threshold", adaptive_threshold)
        adaptive_range = params.get("adaptive_range", adaptive_range)
        adaptive_constant = params.get("adaptive_constant", adaptive_constant)
        enable_threshold = params.get("enable_threshold", enable_threshold)
        contrast_thresholds = tuple(params.get("contrast_thresholds", contrast_thresholds))
        hough_threshold = params.get("hough_threshold", hough_threshold)
        minLineLength = params.get("minLineLength", minLineLength)
        maxLineGap = params.get("maxLineGap", maxLineGap)
        hough_pi = params.get("hough_pi", hough_pi)
        vertical_line_x = params.get("vertical_line_x", vertical_line_x)
        horizontal_line_y = params.get("horizontal_line_y", horizontal_line_y)
        roi = tuple(params.get("roi", roi))
        enable_sobel = params.get("enable_sobel", enable_sobel)
        sobel_ksize = params.get("sobel_ksize", sobel_ksize)
        sobel_threshold = params.get("sobel_threshold", sobel_threshold)
        
        print(f"Parameters loaded from {filename}")
    except Exception as e:
        print(f"Error loading parameters: {e}")

load_parameters()

cv2.namedWindow("Controls", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Controls", 520, 780)

cv2.createTrackbar("Enable CLAHE", "Controls", enable_clahe, 1, noop)
cv2.createTrackbar("Clip limit", "Controls", int(clipLimit*10), 100, noop)
cv2.createTrackbar("Tile grid size", "Controls", tileGridSize[0], 100, noop)
cv2.createTrackbar("HLS lower B", "Controls", hls_lower_bound[0], 255, noop)
cv2.createTrackbar("HLS lower G", "Controls", hls_lower_bound[1], 255, noop)
cv2.createTrackbar("HLS lower R", "Controls", hls_lower_bound[2], 255, noop)
cv2.createTrackbar("HLS upper B", "Controls", hls_upper_bound[0], 255, noop)
cv2.createTrackbar("HLS upper G", "Controls", hls_upper_bound[1], 255, noop)
cv2.createTrackbar("HLS upper R", "Controls", hls_upper_bound[2], 255, noop)

cv2.createTrackbar("Enable Blur", "Controls", enable_blur, 1, noop)
cv2.createTrackbar("Blur", "Controls", blur[0], 100, noop)
cv2.createTrackbar("Sigma", "Controls", sigma, 100, noop)

cv2.createTrackbar("Enable Canny", "Controls", enable_canny, 1, noop)
cv2.createTrackbar("Canny threshold1", "Controls", canny_threshold1, 255, noop)
cv2.createTrackbar("Canny threshold2", "Controls", canny_threshold2, 255, noop)

cv2.createTrackbar("Enable Sobel", "Controls", enable_sobel, 1, noop)
cv2.createTrackbar("Sobel ksize", "Controls", sobel_ksize, 10, noop)
cv2.createTrackbar("Sobel threshold", "Controls", sobel_threshold, 255, noop)

cv2.createTrackbar("Enable Morph", "Controls", enable_morph, 1, noop)
cv2.createTrackbar("Canny kernel", "Controls", canny_kernel[0], 10, noop)
cv2.createTrackbar("Canny dilation iterations", "Controls", canny_dilation_iterations, 10, noop)
cv2.createTrackbar("Canny erosion iterations", "Controls", canny_erosion_iterations, 10, noop)

cv2.createTrackbar("Enable Adaptive Threshold", "Controls", enable_adaptive_threshold, 1, noop)
cv2.createTrackbar("Adaptive threshold", "Controls", adaptive_threshold, 255, noop)
cv2.createTrackbar("Adaptive range", "Controls", adaptive_range, 100, noop)
cv2.createTrackbar("Adaptive constant", "Controls", adaptive_constant, 100, noop)

cv2.createTrackbar("Enable Threshold", "Controls", enable_threshold, 1, noop)
cv2.createTrackbar("Contrast threshold", "Controls", contrast_thresholds[0], 255, noop)

cv2.createTrackbar("Hough threshold", "Controls", hough_threshold, 500, noop)
cv2.createTrackbar("Min line length", "Controls", minLineLength, 500, noop)
cv2.createTrackbar("Max line gap", "Controls", maxLineGap, 500, noop)
cv2.createTrackbar("Hough pi", "Controls", hough_pi, 360, noop)
cv2.createTrackbar("Vertical line x", "Controls", vertical_line_x, 1280, noop)
cv2.createTrackbar("Horizontal line y", "Controls", horizontal_line_y, 720, noop)
cv2.createTrackbar("ROI y", "Controls", roi[1], 720, noop)
cv2.createTrackbar("ROI x", "Controls", roi[0], 1280, noop)
cv2.createTrackbar("ROI height", "Controls", roi[3], 720, noop)
cv2.createTrackbar("ROI width", "Controls", roi[2], 1280, noop)

cv2.namedWindow("Camera Dashboard", cv2.WINDOW_NORMAL)

def save_parameters(filename="parameters.json"):
    """Save all trackbar parameters to a JSON file."""
    params = {
        "enable_clahe": enable_clahe,
        "clipLimit": clipLimit,
        "tileGridSize": tileGridSize,
        "hls_lower_bound": hls_lower_bound,
        "hls_upper_bound": hls_upper_bound,
        "enable_blur": enable_blur,
        "blur": blur,
        "sigma": sigma,
        "enable_canny": enable_canny,
        "canny_threshold1": canny_threshold1,
        "canny_threshold2": canny_threshold2,
        "enable_morph": enable_morph,
        "canny_kernel": canny_kernel,
        "canny_dilation_iterations": canny_dilation_iterations,
        "canny_erosion_iterations": canny_erosion_iterations,
        "enable_adaptive_threshold": enable_adaptive_threshold,
        "adaptive_threshold": adaptive_threshold,
        "adaptive_range": adaptive_range,
        "adaptive_constant": adaptive_constant,
        "enable_threshold": enable_threshold,
        "contrast_thresholds": contrast_thresholds,
        "enable_sobel": enable_sobel,
        "sobel_ksize": sobel_ksize,
        "sobel_threshold": sobel_threshold,
        "hough_threshold": hough_threshold,
        "minLineLength": minLineLength,
        "maxLineGap": maxLineGap,
        "hough_pi": hough_pi,
        "vertical_line_x": vertical_line_x,
        "horizontal_line_y": horizontal_line_y,
        "roi": roi
    }
    with open(filename, 'w') as f:
        json.dump(params, f, indent=2)
    print(f"Parameters saved to {filename}")

sync_file_inputs = is_video_file_source(SOURCE_L) and is_video_file_source(SOURCE_R)

while True:
    retL, frameL, retR, frameR = read_synced_frames(camL, camR, sync_file_inputs)

    if not retL or not retR:
        break

    # Pick one shared display size so no stream appears smaller.
    target_width = max(frameL.shape[1], frameR.shape[1])
    target_height = max(frameL.shape[0], frameR.shape[0])
    target_size = (target_width, target_height)

    frameL = normalize_frame_size(frameL, target_size)
    frameR = normalize_frame_size(frameR, target_size)

    blur_value = ensure_odd(cv2.getTrackbarPos("Blur", "Controls"))
    sigma = cv2.getTrackbarPos("Sigma", "Controls")
    contrast_threshold = cv2.getTrackbarPos("Contrast threshold", "Controls")
    clipLimit = cv2.getTrackbarPos("Clip limit", "Controls") / 10.0
    tile_grid = max(1, cv2.getTrackbarPos("Tile grid size", "Controls"))
    tileGridSize = (tile_grid, tile_grid)
    canny_threshold1 = cv2.getTrackbarPos("Canny threshold1", "Controls")
    canny_threshold2 = cv2.getTrackbarPos("Canny threshold2", "Controls")
    enable_sobel = cv2.getTrackbarPos("Enable Sobel", "Controls")
    sobel_ksize = ensure_odd(cv2.getTrackbarPos("Sobel ksize", "Controls"))
    sobel_threshold = cv2.getTrackbarPos("Sobel threshold", "Controls")
    hough_threshold = cv2.getTrackbarPos("Hough threshold", "Controls")
    minLineLength = cv2.getTrackbarPos("Min line length", "Controls")
    maxLineGap = cv2.getTrackbarPos("Max line gap", "Controls")
    hough_pi = cv2.getTrackbarPos("Hough pi", "Controls")
    roi = (cv2.getTrackbarPos("ROI x", "Controls"), cv2.getTrackbarPos("ROI y", "Controls"), cv2.getTrackbarPos("ROI width", "Controls"), cv2.getTrackbarPos("ROI height", "Controls"))
    vertical_line_x = cv2.getTrackbarPos("Vertical line x", "Controls")
    horizontal_line_y = cv2.getTrackbarPos("Horizontal line y", "Controls")
    canny_kernel_size = max(1, cv2.getTrackbarPos("Canny kernel", "Controls"))
    canny_kernel = (canny_kernel_size, canny_kernel_size)
    canny_dilation_iterations = cv2.getTrackbarPos("Canny dilation iterations", "Controls")
    canny_erosion_iterations = cv2.getTrackbarPos("Canny erosion iterations", "Controls")
    enable_clahe = cv2.getTrackbarPos("Enable CLAHE", "Controls")
    enable_blur = cv2.getTrackbarPos("Enable Blur", "Controls")
    enable_canny = cv2.getTrackbarPos("Enable Canny", "Controls")
    enable_sobel = cv2.getTrackbarPos("Enable Sobel", "Controls")
    enable_morph = cv2.getTrackbarPos("Enable Morph", "Controls")
    enable_threshold = cv2.getTrackbarPos("Enable Threshold", "Controls")
    enable_adaptive_threshold = cv2.getTrackbarPos("Enable Adaptive Threshold", "Controls")
    adaptive_threshold = cv2.getTrackbarPos("Adaptive threshold", "Controls")
    adaptive_range = ensure_odd_block_size(cv2.getTrackbarPos("Adaptive range", "Controls"))
    adaptive_constant = cv2.getTrackbarPos("Adaptive constant", "Controls")
    hls_lower_bound = (cv2.getTrackbarPos("HLS lower B", "Controls"), cv2.getTrackbarPos("HLS lower G", "Controls"), cv2.getTrackbarPos("HLS lower R", "Controls"))
    hls_upper_bound = (cv2.getTrackbarPos("HLS upper B", "Controls"), cv2.getTrackbarPos("HLS upper G", "Controls"), cv2.getTrackbarPos("HLS upper R", "Controls"))
    
    roi_x, roi_y, roi_w, roi_h = roi
    left_roi = (roi_x, roi_y, roi_w, roi_h)
    right_roi = (mirror_roi_x(roi_x, target_width, roi_w), roi_y, roi_w, roi_h)

    left_line_x = vertical_line_x
    right_line_x = max(0, roi_w - vertical_line_x)
    
    frameLFiltered = filter_frame(frameL)
    frameRFiltered = filter_frame(frameR)

    frameL = apply_intersection_on_roi(frameL, left_roi, left_line_x)[1]
    frameR = apply_intersection_on_roi(frameR, right_roi, right_line_x)[1]

    left_main = add_label(frameL, "Left Camera")
    right_main = add_label(frameR, "Right Camera")
    left_filtered = add_label(to_bgr(frameLFiltered), "Left Filtered")
    right_filtered = add_label(to_bgr(frameRFiltered), "Right Filtered")

    top_row = np.hstack([left_main, right_main])
    bottom_row = np.hstack([left_filtered, right_filtered])
    dashboard = np.vstack([top_row, bottom_row])

    # Scale down for easier viewing on smaller screens.
    dashboard = cv2.resize(dashboard, (target_width, target_height), interpolation=cv2.INTER_AREA)

    timing_label = f"Avg apply_intersection_on_roi: {roi_timing_avg_ms:.2f} ms"
    cv2.putText(dashboard, timing_label, (12, target_height - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.resizeWindow("Camera Dashboard", target_width, target_height)
    cv2.imshow("Camera Dashboard", dashboard)

    key = cv2.waitKey(30) & 0xFF
    if key == ord('q'):
        break

    if key == ord('s'):
        save_parameters()

camL.release()
camR.release()
cv2.destroyAllWindows()