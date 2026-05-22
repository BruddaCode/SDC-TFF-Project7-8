import cv2
from line_detection.StereoCamera import StereoCamera
import os
import numpy as np

if __name__ == "__main__":
    camL = StereoCamera(videoPath="2026-04-02-test3-720/left.mp4", camPos="left")
    camR = StereoCamera(videoPath="2026-04-02-test3-720/right.mp4", camPos="right")
    
    while True:
        frameL = camL.getFrame()
        frameR = camR.getFrame()
        if frameL is not None and frameR is not None:
            cv2.hconcat([frameL, frameR], frameL)
            cv2.imshow("frames", frameL)
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break            