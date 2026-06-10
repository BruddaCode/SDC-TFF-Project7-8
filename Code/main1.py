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
DEBUG = 0

# turn controller on or off
CONTROLLER_ENABLED = 1
KART_SPEED = 50
currentAngle = 0

# canbus send msg delay
counter = 0
delay = 2

# broken line tracking
BROKEN_LINE_LEFT = False
BROKEN_LINE_RIGHT = False
lastMode = None
modes = []

# stale value tracking for line detection
PID_STRENGTH = 0.16
lineDetectionEnabled = True

# turn tracking
turn_start_time = None
TURN_DURATION = 2.0  # TODO: tune this
DELAY_DURATION = 3.0 # time to wait at stop sign, can be tuned

LEFT = False
RIGHT = True
switchToLeftLane = False
switchToRightLane = False
switchLaneOnNextBrokenLine = False
laneTime = 2000
startLaneSwitch = 0

def switchLane(direction, controller):
    if time.time() - startLaneSwitch <= laneTime:
        steer = 30
        if not direction:
            steer = -steer
        lineDetectionEnabled = False
    
        controller.steer(steer)
        controller.drive(KART_SPEED)
    else:
        lineDetectionEnabled = True
        switchToLeftLane = False
        switchToRightLane = False


if __name__ == "__main__":

    if DEBUG:
        videoPath = "2026-05-28_beelden_onderbrokenlijn"
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
        # for object detection, the things that still need changing are:
        # - the distance thresholds for each object (currently 5m for everything, but should be different for each object) -> 3m?
        # - the actions taken for each object (currently just print statements, but should be actually controlling the kart)
            # - Zebrapad + Persoon = stop (<= 3m), Zebrapad + !Persoon = slow down (not stop) -> px Person >= 961 px == Right side, px Person <= 959 px == Left side, compare with Zebrapad pixels
            # - Verkeerslicht groen = doorrijden, verkeerslicht rood = stoppen
            # - One way left/sign left only = voorbereiden op linksaf slaan (misschien al eerder, afhankelijk van afstand)
            # - Stop sign = <= 3m stoppen 
            # - Speed sign 20/30, in principe snelheid aanpassen, maar denk niet dat we zo snel uberhaupt gaan, dus negeren? (low priority)
            # - Person (on its own) = negeren, tenzij zo dichtbij dat practisch aangereden (low priority) 
            # - Stop light off = negeren, tenzij zo dichtbij dat practisch aangereden (low priority)
        # - when persons are detected (and "zebrapad") from right to left walk, or wait, for a specified amount of time (10seconds? or so) -> vorige groep deed op basis van frames... wisselvallig, denk t is beter om te hardcoden
        # - prioritieten stellen (zelfmoord of niet zelfmoord) -> else ifs, met afstand geimplementeerd, zodat dingen niet genegeerd worden.

        oneWayLeft = None
        stopSign = None
        StopSignFlag = False
        signLeftOnly = None
        redLight = None
        greenLight = None
        person = None
        zebraCrossing = None
        car = None
        speedSign20 = None
        speedSign30 = None
        SpeedSignFlag = False

        detections = threadM.latestDetections
        # print(f"Detections: {detections}")

        if detections is not None:
            for det in detections:
                match det[0]:
                    case "one-way-left":
                        oneWayLeft = det
                    case "stop-sign":
                        stopSign = det
                    case "sign-left-only":
                        signLeftOnly = det  
                    case "traffic-light-red":
                        redLight = det
                    case "traffic-light-green":
                        greenLight = det
                    case "person":
                        person = det
                    case "zebra-crossing":
                        zebraCrossing = det
                    case "car":
                        car = det
                    case "speed-sign-20":
                        speedSign20 = det
                    case "speed-sign-30":
                        speedSign30 = det

        if stopSign:
            try:
                if stopSign[1] < 3.0:
                    print(f"Stop sign detected at {stopSign[1]}m, stopping kart")
                    if controller is not None:
                        if StopSignFlag == False:
                            controller.drive(0)
                            controller.brake(100)
                            StopSignFlag = True
                            delay(DELAY_DURATION * 1000) # wait for 3 seconds, can be tuned
                        else:
                            print("Already stopped for stop sign, ignoring")
                            controller.brake(0)
                            controller.drive(KART_SPEED)
            except Exception as e:
                print(f"Error getting distance for stop sign: {e}")
        else:
            StopSignFlag = False    

        if greenLight:
            try:
                if greenLight[1] < 3.0: 
                    print(f"Green light detected at {greenLight[1]}m, go go go!")
                    if controller is not None:
                        controller.brake(0)
                        controller.drive(KART_SPEED)
            except Exception as e:
                print(f"Error getting distance for green light: {e}")

        elif redLight:
            try:
                if redLight[1] < 3.0:
                    print(f"Red light detected at {redLight[1]}m, stopping kart")
                    if controller is not None:
                        controller.drive(0)
                        controller.brake(100)
            except Exception as e:
                print(f"Error getting distance for red light: {e}")

        if zebraCrossing: 
            try:
                if zebraCrossing[1] < 5.0:
                    lineDetectionEnabled = False
                    if person and person[1] < 5.0: 
                        print(f"Person detected on zebra crossing at {person[1]}m, stopping kart, at {person[2]}px")
                        if controller is not None:
                            controller.drive(0)
                            controller.brake(100)
                    else:
                        print(f"Zebra crossing detected at {zebraCrossing[1]}m, slowing down")
                        if controller is not None:
                            controller.brake(0)
                            controller.steer(0)
                            controller.drive(40)
            except Exception as e:
                print(f"Error getting distance for zebra crossing: {e}")
        else:
            lineDetectionEnabled = True
            # controller.drive(KART_SPEED)

        # elif det[0] == "person" and det[1] is not None and det[1] < 5.0:
        #     if det[2] >= 961: # person on right side, so walking from right to left
        #         print(f"Person detected on the right at {det[1]}m, waiting for them to cross")
        #         if controller is not None:
        #             controller.drive(0)
        #             time.sleep(5)  # wait for 5 seconds, can be tuned
        #             controller.drive(KART_SPEED)

        if signLeftOnly or oneWayLeft:
            try:
                if signLeftOnly[1] < 5.0 or oneWayLeft[1] < 5.0: # TODO: tune distance threshold
                    if turn_start_time is None:  # Only trigger once
                        print(f"{det[0]} at {det[1]}m, preparing to turn left")
                        turn_start_time = time.time()
                        switchLaneOnNextBrokenLine = True
                        if controller is not None:
                            currentAngle = -50
                            lineDetectionEnabled = False
                            controller.steer(currentAngle)
                            controller.drive(KART_SPEED)
            except Exception as e:
                print(f"Error getting distance for left turn sign: {e}")
                
        if car:
            try:
                if car[1] < 4.0:
                    print(f"Car detected at {car[1]}m, slowing down")
                    if controller is not None:
                        controller.drive(0)
                        controller.brake(100)  # apply moderate brake, can be tuned
            except Exception as e:
                print(f"Error getting distance for car: {e}")

        if turn_start_time is not None and time.time() - turn_start_time >= TURN_DURATION:
            print("Turn complete, re-enabling line detection")
            turn_start_time = None
            if controller is not None:
                currentAngle = 0
                lineDetectionEnabled = True
        elif currentAngle != 0:
            controller.steer(currentAngle)  # Maintain turn angle until turn is complete
            controller.drive(KART_SPEED)


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

        
        if mode == "both":
            modes.append("both")

        if (mode == "single-left" and lastMode == "single-left"):
            modes = []
            BROKEN_LINE_RIGHT = True
        
        if (mode == "single-right" and lastMode == "single-right"):
            modes = []
            BROKEN_LINE_LEFT = True
        
        if len(modes) >= 20:
            BROKEN_LINE_LEFT = False
            BROKEN_LINE_RIGHT = False
            modes = []

        lastMode = mode

        if switchLaneOnNextBrokenLine and lineDetectionEnabled:
            if BROKEN_LINE_LEFT:
                switchToLeftLane = True
                startLaneSwitch = time.time()
            elif BROKEN_LINE_RIGHT:
                switchToRightLane = True
                startLaneSwitch = time.time()

        if switchToLeftLane:
            switchLane(LEFT, controller)
        elif switchToRightLane:
            switchLane(RIGHT, controller)

        # print(f"Mode: {mode:12s} | brokenL: {BROKEN_LINE_LEFT} | brokenR: {BROKEN_LINE_RIGHT}", flush=True)
        
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
        controller.turnOffBus()#
