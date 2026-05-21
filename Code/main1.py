from line_detection.PIDController import PIDController
from line_detection.StereoCamera import StereoCamera
from line_detection.LineThread import LineThread
from rijden.carcontroller import CarController

from cv2_enumerate_cameras import enumerate_cameras
import time
import json
import cv2
import numpy as np

DEBUG = False

def getCameraId(cameraName):
    cameraIDs = []
    
    for camera_info in enumerate_cameras():
        if cameraName.lower() in camera_info.name.lower():
            if int(str(camera_info.index)[-1]) not in cameraIDs:
                cameraIDs.append(int(str(camera_info.index)[-1]))
        else:
            print(f"Camera '{camera_info.name}' does not match the specified name '{cameraName}'.")
        
    return cameraIDs

if __name__ == "__main__":
    with open("config.json", "r") as f:
        config = json.load(f)
    
    PIDKey = config["PID"]
    cameraKey = config["Camera"]
    
    ids = getCameraId(cameraKey["cameraName"])
    names = ["left", "middle", "right"]
    # camM = StereoCamera(id=ids[1], camPos=names[1]) # voor nu niet nodig
    camL = StereoCamera(index=ids[1], camPos=names[0])
    camR = StereoCamera(index=ids[2], camPos=names[2])
    # camL = StereoCamera(videoPath="30-04-2026_verlichte_baan/left.mp4", camPos=names[0])
    # camR = StereoCamera(videoPath="30-04-2026_verlichte_baan/right.mp4", camPos=names[2])
    
    controller = CarController()
    # controller = None
    wL = config["LineWeight"]["left"]
    wR = config["LineWeight"]["right"]

    threadL = LineThread(camL)
    threadR = LineThread(camR)
    
    # enable synchronous stepping so we can request frames together
    if DEBUG:
        threadL.enable_sync_mode(True)
        threadR.enable_sync_mode(True)
    
    threadL.start()
    threadR.start()
    # start indices for synchronization: we'll wait for each thread to advance
    prevLIndex = threadL.latestIndex
    prevRIndex = threadR.latestIndex
    
    targetCenter = PIDKey["targetCenter"]
    pid = PIDController(PIDKey["Kp"], PIDKey["Ki"], PIDKey["Kd"], targetCenter)

    prevCenter = targetCenter
    prevTime = time.time()
    
    # stale value tracking
    MAX_STALE_TIME = 0.5
    lastLeftHit  = None
    lastRightHit = None
    lastLeftTime  = 0.0
    lastRightTime = 0.0
    
    while True:
        if DEBUG:
            threadL.request_step()
            threadR.request_step()
            threadL.wait_for_index(prevLIndex)
            threadR.wait_for_index(prevRIndex)
            prevLIndex = threadL.latestIndex
            prevRIndex = threadR.latestIndex
        
        controller.drive(40)
        leftHit  = threadL.latestIntersection
        rightHit = threadR.latestIntersection
        currTime = time.time()

        # update stored values if we have fresh detections
        if leftHit is not None:
            lastLeftHit  = leftHit
            lastLeftTime = currTime
        if rightHit is not None:
            lastRightHit  = rightHit
            lastRightTime = currTime

        # check if stored values are still within the stale timeout
        leftValid  = lastLeftHit  is not None and (currTime - lastLeftTime)  < MAX_STALE_TIME
        rightValid = lastRightHit is not None and (currTime - lastRightTime) < MAX_STALE_TIME

        if leftValid and rightValid:
            mode = "both"
            laneCenter = lastLeftHit / (lastLeftHit + lastRightHit)

        elif leftValid:
            mode = "single-left"
            laneCenter = lastLeftHit

        elif rightValid:
            mode = "single-right"
            laneCenter = 1 - lastRightHit

        else:
            mode = "lost"
            laneCenter = prevCenter  # hold last known center


        # smooth and compute PID
        laneCenter = 0.6 * prevCenter + 0.4 * laneCenter
        prevCenter = laneCenter

        dt = currTime - prevTime
        prevTime = currTime

        steer = pid.compute(laneCenter, dt)
        steer = -(int(np.clip(np.interp(steer, [-0.18, 0.18], [-100, 100]), -100, 100)))

        print(f"Mode: {mode:12s} | L: {str(round(lastLeftHit, 2)) if lastLeftHit is not None else 'None':>5} | R: {str(round(lastRightHit, 2)) if lastRightHit is not None else 'None':>5} | Center: {laneCenter:.2f} | Steer: {steer}", flush=True)
        controller.steer(-abs(steer))
        # print(f"Steering with value: {steer:.2f} based on lane center: {laneCenter:.2f}")
        
        if threadL.latestFrame is not None:
            cv2.imshow("left", threadL.latestFrame)

        if threadR.latestFrame is not None:
            cv2.imshow("right", threadR.latestFrame)

        if cv2.waitKey(30) & 0xFF == ord('q'):
            threadL.stop()
            threadR.stop()
            break

    cv2.destroyAllWindows()
    controller.turnOffBus()