from Object_Detection.ObjectDetector import ObjectDetector
from line_detection.PIDController import PIDController
from line_detection.StereoCamera import StereoCamera
from line_detection.LineThread import LineThread
from rijden.carcontroller import CarController

import numpy as np
import time
import cv2

# turn frame sync on or off
# 0 = off
# 1 = on
DEBUG = 1

# turn controller on or off
CONTROLLER_ENABLED = 0
KART_SPEED = 50

# canbus send msg delay
counter = 0
delay = 2

# stale value tracking for line detection
PID_STRENGTH = 0.16
lineDetectionEnabled = True

if __name__ == "__main__":

    if DEBUG:
        videoPath = "bordentest"
        camM = StereoCamera(videoPath=f"{videoPath}/middle.mp4", camPos="middle")
        camL = StereoCamera(videoPath=f"{videoPath}/left.mp4", camPos="left")
        camR = StereoCamera(videoPath=f"{videoPath}/right.mp4", camPos="right")
    else:
        ids = StereoCamera.getCameraId()
        camM = StereoCamera(index=ids[0], camPos="middle")
        camL = StereoCamera(index=ids[1], camPos="left")
        camR = StereoCamera(index=ids[2], camPos="right")
    
    controller = None
    if CONTROLLER_ENABLED:
        controller = CarController()

    threadL = LineThread(camL)
    threadR = LineThread(camR)
    threadM = ObjectDetector(camM)

    pid = PIDController()
    
    # enable synchronous stepping so we can request frames together
    if DEBUG:
        threadL.enable_sync_mode(True)
        threadR.enable_sync_mode(True)
        prevLIndex = threadL.latestIndex
        prevRIndex = threadR.latestIndex
    
    threadL.start()
    threadR.start()    
    threadM.start()
    prevCenter = pid.setpoint
    prevTime = time.time()
    
    while True:

        # --------------------- object detection -------------------------
        detections = threadM.latestDetections
        # print(f"Detections: {detections}")

        if detections is not None:
            for det in detections:
                label = det[0]
                distance = det[1]

                if label == "traffic-light-green":
                    print(f"Green light detected at {distance}m")

                if label == "traffic-light-red" and distance is not None and distance < 5.0:
                    print(f"Red light detected at {distance}m, stopping kart")
                    # if controller is not None:
                        # controller.drive(0)
                
                if label == "zebra-crossing" and distance is not None and distance < 5.0:
                    print(f"Zebra crossing detected at {distance}m, slowing down")
                    # lineDetectionEnabled = False
                    # if controller is not None:
                        # controller.drive(30)
                # else:
                    # lineDetectionEnabled = True

        # ----------------------------------------------------------------

        # ---------------------- line detection --------------------------
        if DEBUG:
            threadL.request_step()
            threadR.request_step()
            threadL.wait_for_index(prevLIndex)
            threadR.wait_for_index(prevRIndex)
            prevLIndex = threadL.latestIndex
            prevRIndex = threadR.latestIndex
        
        leftHit  = threadL.latestIntersection
        rightHit = threadR.latestIntersection
        currTime = time.time()

        mode, laneCenter = threadL.detector.checkForHit(leftHit, rightHit, currTime, prevCenter)
        lastLeftHit = threadL.detector.lastLeftHit
        lastRightHit = threadL.detector.lastRightHit

        # smooth and compute PID
        laneCenter = 0.6 * prevCenter + 0.4 * laneCenter
        prevCenter = laneCenter

        dt = currTime - prevTime
        prevTime = currTime

        steer = pid.compute(laneCenter, dt)
        steer = -(round((np.clip(np.interp(steer, [-PID_STRENGTH, PID_STRENGTH], [-100, 100]), -100, 100)), 2))

        # print(f"Mode: {mode:12s} | L: {str(round(lastLeftHit, 2)) if lastLeftHit is not None else 'None':>5} | R: {str(round(lastRightHit, 2)) if lastRightHit is not None else 'None':>5} | Center: {laneCenter:.2f} | Steer: {steer}", flush=True)
                
        # periodic steering update
        # if controller is not None:
        #     counter+=1
        #     if counter >= delay:
        #         counter = 0
        #         controller.steer(steer)
        #         controller.drive(KART_SPEED)

        if controller is not None and lineDetectionEnabled:
            controller.steer(steer)
            controller.drive(KART_SPEED)
        
        # ----------------------------------------------------------------

        
        if threadL.latestFrame is not None:
            cv2.imshow("left", threadL.latestFrame)

        if threadR.latestFrame is not None:
            cv2.imshow("right", threadR.latestFrame)

        if threadM.latestFrame is not None:
            cv2.imshow("middle", threadM.latestFrame)

        if cv2.waitKey(30) & 0xFF == ord('q'):
            threadL.stop()
            threadR.stop()
            threadM.stop()
            break
    
        

    cv2.destroyAllWindows()
    if controller is not None:
        controller.turnOffBus()