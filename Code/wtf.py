import cv2
import numpy as np
import os
import time


# Image paths (change these to your image files)
leftImagePath = "Left_screenshot_12.05.2026.png"
rightImagePath = "Right_screenshot_12.05.2026.png"


TRACKBAR_L_WINDOW = "SrcL Controls"
TRACKBAR_R_WINDOW = "SrcR Controls"


def _create_point_trackbars(window_name, width, height, prefix, initial_points):
    cv2.createTrackbar(f"{prefix}1 x", window_name, int(initial_points[0][0]), width - 1, lambda v: None)
    cv2.createTrackbar(f"{prefix}1 y", window_name, int(initial_points[0][1]), height - 1, lambda v: None)
    cv2.createTrackbar(f"{prefix}2 x", window_name, int(initial_points[1][0]), width - 1, lambda v: None)
    cv2.createTrackbar(f"{prefix}2 y", window_name, int(initial_points[1][1]), height - 1, lambda v: None)
    cv2.createTrackbar(f"{prefix}3 x", window_name, int(initial_points[2][0]), width - 1, lambda v: None)
    cv2.createTrackbar(f"{prefix}3 y", window_name, int(initial_points[2][1]), height - 1, lambda v: None)
    cv2.createTrackbar(f"{prefix}4 x", window_name, int(initial_points[3][0]), width - 1, lambda v: None)
    cv2.createTrackbar(f"{prefix}4 y", window_name, int(initial_points[3][1]), height - 1, lambda v: None)


def _read_points(window_name, prefix):
    return np.array(
        [
            [cv2.getTrackbarPos(f"{prefix}1 x", window_name), cv2.getTrackbarPos(f"{prefix}1 y", window_name)],
            [cv2.getTrackbarPos(f"{prefix}2 x", window_name), cv2.getTrackbarPos(f"{prefix}2 y", window_name)],
            [cv2.getTrackbarPos(f"{prefix}3 x", window_name), cv2.getTrackbarPos(f"{prefix}3 y", window_name)],
            [cv2.getTrackbarPos(f"{prefix}4 x", window_name), cv2.getTrackbarPos(f"{prefix}4 y", window_name)],
        ],
        dtype=np.float32,
    )





def platslaan(frame, src_points, dst_points=None):
    w = frame.shape[1]
    h = frame.shape[0]

    if dst_points is None:
        dst_points = np.array([
            [0, 0],
            [w, 0],
            [0, h],
            [w, h]
        ], dtype=np.float32)

    matrix = cv2.getPerspectiveTransform(src_points, dst_points)
    warped_frame = cv2.warpPerspective(frame, matrix, (w, h))
    return warped_frame


if __name__ == "__main__":
    # Load images
    frameL = cv2.imread(leftImagePath)
    frameR = cv2.imread(rightImagePath)
    
    if frameL is None or frameR is None:
        print(f"Error: Could not load images. Check paths:")
        print(f"  Left: {leftImagePath}")
        print(f"  Right: {rightImagePath}")
        exit(1)

    src_controls_ready = False

    while True:
        if frameL is not None and frameR is not None:
            # Create working copies to avoid modifying originals
            rotatedL = cv2.rotate(frameL, cv2.ROTATE_90_COUNTERCLOCKWISE)
            rotatedR = cv2.rotate(frameR, cv2.ROTATE_90_CLOCKWISE)
            
            if not src_controls_ready:
                # defaults used to initialize trackbars
                defaultL = np.array([
                    [250, 180],
                    [1030, 180],
                    [80, 700],
                    [1200, 700],
                ], dtype=np.float32)
                defaultR = np.array([
                    [260, 180],
                    [1020, 180],
                    [70, 700],
                    [1210, 700],
                ], dtype=np.float32)
                lh, lw = rotatedL.shape[:2]
                rh, rw = rotatedR.shape[:2]
                cv2.namedWindow(TRACKBAR_L_WINDOW, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(TRACKBAR_L_WINDOW, 900, 320)
                _create_point_trackbars(TRACKBAR_L_WINDOW, lw, lh, "L", defaultL)
                # dst defaults map to full image corners
                dst_defaultL = np.array([[0,0],[lw-1,0],[0,lh-1],[lw-1,lh-1]], dtype=np.float32)
                _create_point_trackbars(TRACKBAR_L_WINDOW, lw, lh, "Ld", dst_defaultL)
                cv2.namedWindow(TRACKBAR_R_WINDOW, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(TRACKBAR_R_WINDOW, 900, 320)
                _create_point_trackbars(TRACKBAR_R_WINDOW, rw, rh, "R", defaultR)
                dst_defaultR = np.array([[0,0],[rw-1,0],[0,rh-1],[rw-1,rh-1]], dtype=np.float32)
                _create_point_trackbars(TRACKBAR_R_WINDOW, rw, rh, "Rd", dst_defaultR)
                src_controls_ready = True

            srcL = _read_points(TRACKBAR_L_WINDOW, "L")
            dstL = _read_points(TRACKBAR_L_WINDOW, "Ld")
            srcR = _read_points(TRACKBAR_R_WINDOW, "R")
            dstR = _read_points(TRACKBAR_R_WINDOW, "Rd")

            warpedL = platslaan(rotatedL, srcL, dstL)
            warpedR = platslaan(rotatedR, srcR, dstR)


            combinedWarped = np.hstack((warpedL, warpedR))
            cv2.imshow("Combined", combinedWarped)
            
            combinedNormal = np.hstack((frameL, frameR))
            cv2.imshow("Combined Normal", combinedNormal)
            
            
            

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()