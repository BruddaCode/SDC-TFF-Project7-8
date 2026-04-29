from line_detection.PIDController import PIDController
from line_detection.StereoCamera import StereoCamera
from line_detection.LineThread import LineThread
from rijden.carcontroller import CarController

from cv2_enumerate_cameras import enumerate_cameras
import time
import json
import cv2

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
    # camL = StereoCamera(index=ids[0], camPos=names[0])
    # camR = StereoCamera(index=ids[2], camPos=names[2])
    camL = StereoCamera(videoPath="2026-04-02-test3-720/left.mp4", camPos=names[0])
    camR = StereoCamera(videoPath="2026-04-02-test3-720/right.mp4", camPos=names[2])
    
    # controller = CarController()
    controller = None
    wL = config["LineWeight"]["left"]
    wR = config["LineWeight"]["right"]

    threadL = LineThread(camL)
    threadR = LineThread(camR)
    threadL.start()
    threadR.start()
    
    targetCenter = PIDKey["targetCenter"]
    pid = PIDController(PIDKey["Kp"], PIDKey["Ki"], PIDKey["Kd"], targetCenter)

    prevCenter = targetCenter
    prevTime = time.time()
    
    while True:
        # controller.drive(40)
        leftHit = threadL.latestIntersection
        rightHit = threadR.latestIntersection

        if leftHit is not None and rightHit is not None:
            laneCenter = (wL * leftHit + wR * rightHit) / (wL + wR)

            laneCenter = 0.7 * prevCenter + 0.3 * laneCenter
            prevCenter = laneCenter
      
            error = targetCenter - laneCenter

            currTime = time.time()
            dt = currTime - prevTime
            prevTime = currTime

            steer = pid.compute(error, dt)

            steer = max(-100, min(100, steer))

            # controller.steer(steer)
            print(f"Steering with value: {steer:.2f} based on lane center: {laneCenter:.2f}")
        
        if threadL.latestFrame is not None:
            cv2.imshow("left", threadL.latestFrame)
        
        if threadR.latestFrame is not None:
            cv2.imshow("right", threadR.latestFrame)

        if cv2.waitKey(30) & 0xFF == ord('q'):
            threadL.stop()
            threadR.stop()
            break

    cv2.destroyAllWindows()
    # controller.turnOffBus()