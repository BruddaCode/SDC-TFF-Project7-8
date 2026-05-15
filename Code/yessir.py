import cv2
from line_detection.StereoCamera import StereoCamera
import os
import numpy as np

if __name__ == "__main__":
    camM = StereoCamera(videoPath="30-04-2026_verlichte_baan/middle.mp4", camPos="middle")
    
    while True:
        frameM = camM.getFrame()
        
        if frameM is None:
            print("End of video reached or failed to grab frame.")
            break
        
        # setup trackbars once using frame size
        try:
            _trackbars_ready
        except NameError:
            _trackbars_ready = False

        BEV_W, BEV_H = 800, 800
        SRC_WINDOW = "SrcM Controls"

        def _create_point_trackbars(win, w, h, defaults):
            cv2.createTrackbar('p1 x', win, int(defaults[0][0]), w-1, lambda v: None)
            cv2.createTrackbar('p1 y', win, int(defaults[0][1]), h-1, lambda v: None)
            cv2.createTrackbar('p2 x', win, int(defaults[1][0]), w-1, lambda v: None)
            cv2.createTrackbar('p2 y', win, int(defaults[1][1]), h-1, lambda v: None)
            cv2.createTrackbar('p3 x', win, int(defaults[2][0]), w-1, lambda v: None)
            cv2.createTrackbar('p3 y', win, int(defaults[2][1]), h-1, lambda v: None)
            cv2.createTrackbar('p4 x', win, int(defaults[3][0]), w-1, lambda v: None)
            cv2.createTrackbar('p4 y', win, int(defaults[3][1]), h-1, lambda v: None)

        def _read_points(win):
            return np.array([
                [cv2.getTrackbarPos('p1 x', win), cv2.getTrackbarPos('p1 y', win)],
                [cv2.getTrackbarPos('p2 x', win), cv2.getTrackbarPos('p2 y', win)],
                [cv2.getTrackbarPos('p3 x', win), cv2.getTrackbarPos('p3 y', win)],
                [cv2.getTrackbarPos('p4 x', win), cv2.getTrackbarPos('p4 y', win)],
            ], dtype=np.float32)

        h, w = frameM.shape[:2]
        if not _trackbars_ready:
            default = np.array([[w*0.2, h*0.2], [w*0.8, h*0.2], [w*0.8, h*0.8], [w*0.2, h*0.8]], dtype=np.float32)
            cv2.namedWindow(SRC_WINDOW, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(SRC_WINDOW, 800, 240)
            _create_point_trackbars(SRC_WINDOW, w, h, default)
            _trackbars_ready = True

        src_pts = _read_points(SRC_WINDOW)

        # destination is a top-down rectangle
        dst_pts = np.array([[0,0], [BEV_W-1,0], [BEV_W-1,BEV_H-1], [0,BEV_H-1]], dtype=np.float32)

        # compute homography and warp to BEV
        try:
            H = cv2.getPerspectiveTransform(src_pts, dst_pts)
            bev = cv2.warpPerspective(frameM, H, (BEV_W, BEV_H))
        except cv2.error:
            bev = np.zeros((BEV_H, BEV_W, 3), dtype=np.uint8)

        # show both
        cv2.imshow("Middle Camera", frameM)
        cv2.imshow("Middle BEV", bev)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    camM.release()
    cv2.destroyAllWindows()