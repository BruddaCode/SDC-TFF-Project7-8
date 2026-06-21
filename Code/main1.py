from Object_Detection.ObjectDetector import ObjectDetector
from line_detection.PIDController import PIDController
from line_detection.StereoCamera import StereoCamera
from line_detection.LineThread import LineThread
from rijden.carcontroller import CarController

import numpy as np
import time
import cv2

#? what debug mode does:
#? - if debug mode is on, it will use the videos instead of the cameras, 
#? and it will enable synchronous stepping for the line detection threads, 
#? so that the frames are processed together

# turn frame sync on or off
# 0 = off
# 1 = on
DEBUG = 1


# turn controller on or off
#? controller in this case is the code that send messages to the CAN bus
CONTROLLER_ENABLED = 0
KART_SPEED = 50

# broken line tracking
BROKEN_LINE_LEFT = False
BROKEN_LINE_RIGHT = False
lastMode = None
modes = []
singleLeftCounter = 0
singleRightCounter = 0

# stale value tracking for line detection
#? the lower the number, the more aggressive the kart will steer
#? keep the number between 0.1 and 0.3. or dont ¯\_(ツ)_/¯
PID_STRENGTH = 0.16
lineDetectionEnabled = True

# turn tracking
#? turnDelay is the amount of cycles through the while loop that the kart will spend turning, 
#? so the higher the number, the longer the kart will turn for.
#? turnAngle is the angle that the kart will steer while turning, so the higher the number, the sharper the turn will be.
turnFlag = False
turnDelay = 80
turnCounter = 0
turnAngle = -90

# overtaking tracking
LEFT = False
RIGHT = True
switchToLeftLane = False
switchToRightLane = False
switchLaneOnNextBrokenLine = False
laneTime = 2
startLaneSwitch = 0

overtakeCar = False
overtakeCarStep = 0
stepTwoStart = 0
overtakeDuration = 10

# stop sign delay tracking
#? stopDelay is the number of cycles through the while loop that the kart will be stopped
stopCounter = 0
stopDelay = 300
StopSignFlag = False

# TODO: tune distance threshold
# detection distances
STOP_SIGN_DISTANCE = 9.0
TRAFFIC_LIGHT_DISTANCE = 6.0
ZEBRA_CROSSING_DISTANCE = 5.0
PERSON_ON_ZEBRA_DISTANCE = 5.0
PERSON_POSITION_THRESHOLD = 1000
LEFT_TURN_SIGN_DISTANCE = 5.0
CAR_DISTANCE = 4.0

#? cool function that should be able to make te kart switch lanes.
#? sadly this doesnt work as we didnt have enough time to correctly implement it.
def switchLane(direction, controller):
    lineDetectionEnabled = False
    switchToLeftLane = False
    switchToRightLane = False
    
    if time.time() - startLaneSwitch <= laneTime:
        steerAngle = 30
        if not direction:
            switchToLeftLane = True
            steerAngle = -steerAngle
        else:
            switchToRightLane = True
        lineDetectionEnabled = False
    
        controller.steer(steerAngle)
        controller.drive(KART_SPEED)
    else:
        lineDetectionEnabled = True
        switchToLeftLane = False
        switchToRightLane = False
        
    return lineDetectionEnabled, switchToLeftLane, switchToRightLane


if __name__ == "__main__":

    if DEBUG:
        videoPath = "30-04-2026_beelden_Tom"
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
    
    #? this is commented out because if it isnt the code wont run for some reason.
    # enable synchronous stepping so we can request frames together
    # if DEBUG:
    #     threadL.enable_sync_mode(True)
    #     threadR.enable_sync_mode(True)
    #     prevLIndex = threadL.latestIndex
    #     prevRIndex = threadR.latestIndex
    
    threadL.start()
    threadR.start()    
    threadM.start()
    prevCenter = pid.setpoint
    prevTime = time.time()
    
    #? this makes sure that the main code can only run once all threads have a frame.
    #? otherwise the kart would just start driving like a blind man.
    while True: 
        if threadL.latestFrame is not None and threadR.latestFrame is not None and threadM.latestFrame is not None:
            break


    while True:
        
        #? a small manifesto on the whole object detection and decision making part of the code
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

        #? we make it none each time so that only objects that are detected in the current frame will be considered in the decision making
        oneWayLeft = None
        stopSign = None
        signLeftOnly = None
        redLight = None
        greenLight = None
        person = None
        zebraCrossing = None
        car = None
        speedSign20 = None
        speedSign30 = None
        ForbiddenCar = None

        detections = threadM.latestDetections
        # print(f"Detections: {detections}")
        
        #? this is where the None values are assigned to the detected objects
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
                        #? if there are multiple persons, we want to consider the closest one, so we check if the current person is closer than the previously assigned person
                        #? we havent had time to fully test this so please do
                        if person is None or det[1] < person[1]:
                            person = det
                    case "zebra-crossing":
                        zebraCrossing = det
                    case "car":
                        car = det
                    case "speed-sign-20":
                        speedSign20 = det
                    case "speed-sign-30":
                        speedSign30 = det
                    case "forbidden-car":
                        ForbiddenCar = det

        #? now for the decision making, which was a bit rushed to please refactor this and make it better.
        #? but the general idea is this:
        #? check if the object exists
        #? if it does, check the distance
        #? if the distance is below the threshold, take the appropriate action (stop, slow down, prepare to turn, etc.)
        
        #? the zebra crossing and person detection are a bit more complex, because we want to check if the person is on the zebra crossing
        #? and if they are, we want to stop, but if they are not, we just want to slow down. so we check the distance of the zebra crossing
        #? and if it is below the threshold, we check if there is a person, and if there is, we check their distance and position to determine if they are on the zebra crossing or not.
        #? threshold in this case is where the middle of the person is on the screen in pixels.
        #? so if the person starts on the left, that person should be around 1000px, and if the person starts on the right, that person should be around 200px.
        
        if stopSign:
            try:
                if stopSign[1] < STOP_SIGN_DISTANCE:
                    if controller is not None:
                        if StopSignFlag == False:
                            print(f"Stop sign detected at {stopSign[1]}m, stopping kart, {StopSignFlag}")
                            controller.drive(0)
                            controller.brake(100)
                            StopSignFlag = True
                            lineDetectionEnabled = False
                        else:
                            stopCounter+=1
                            print(f"Already stopped for stop sign, ignoring, counter: {stopCounter}")
                            if stopCounter >= stopDelay:
                                print("Already stopped for stop sign, ignoring")
                                stopCounter = 0
                                controller.brake(0)
                                lineDetectionEnabled = True
            except Exception as e:
                print(f"Error getting distance for stop sign: {e}")
        else:
            StopSignFlag = False

        if greenLight:
            try:
                if greenLight[1] < TRAFFIC_LIGHT_DISTANCE: 
                    print(f"Green light detected at {greenLight[1]}m, go go go!")
                    if controller is not None:
                        controller.brake(0)
                        lineDetectionEnabled = True
            except Exception as e:
                print(f"Error getting distance for green light: {e}")

        elif redLight:
            try:
                if redLight[1] < TRAFFIC_LIGHT_DISTANCE:
                    print(f"Red light detected at {redLight[1]}m, stopping kart")
                    if controller is not None:
                        controller.drive(0)
                        controller.brake(100)
                        lineDetectionEnabled = False
            except Exception as e:
                print(f"Error getting distance for red light: {e}")

        if zebraCrossing: 
            try:
                if zebraCrossing[1] < ZEBRA_CROSSING_DISTANCE:
                    lineDetectionEnabled = False
                    if person and person[1] < PERSON_ON_ZEBRA_DISTANCE and person[2] < PERSON_POSITION_THRESHOLD: 
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
            
        if signLeftOnly and turnFlag == False:
            try:
                if signLeftOnly[1] <= LEFT_TURN_SIGN_DISTANCE: 
                    lineDetectionEnabled = False
                    switchLaneOnNextBrokenLine = True
                    turnFlag = True
                    turnAngle = -45
                    turnDelay = 160
                    print(f"Left turn sign detected at {signLeftOnly[1]}m, preparing to turn left")

            except Exception as e:
                print(f"Error getting distance for left turn sign: {e}")

        if oneWayLeft and turnFlag == False:
            try:
                if oneWayLeft[1] <= LEFT_TURN_SIGN_DISTANCE: 
                    lineDetectionEnabled = False
                    switchLaneOnNextBrokenLine = True
                    turnFlag = True
                    print(f"One way left sign detected at {oneWayLeft[1]}m, preparing to turn left")

            except Exception as e:
                print(f"Error getting distance for one way left sign: {e}")

        if ForbiddenCar and turnFlag == False:
            try:
                if ForbiddenCar[1] < LEFT_TURN_SIGN_DISTANCE:
                    print(f"Forbidden Car Sign detected at {ForbiddenCar[1]}m, Turning Left")
                    if controller is not None:
                        lineDetectionEnabled = False
                        switchLaneOnNextBrokenLine = True
                        turnFlag = True
                        turnAngle = -90
                        turnDelay = 80

            except Exception as e:
                print(f"Error getting distance for Forbidden Car Sign: {e}")
        
        #? this is what causes the kart to turn, it sets the turnFlag to true, which then causes the kart to turn for a certain amount of time, and then reset the flag and counter.
        if turnFlag:
            if turnCounter <= turnDelay:
                if controller is not None:
                    controller.steer(turnAngle)
                    controller.drive(KART_SPEED)
                turnCounter += 1
            else:
                lineDetectionEnabled = True
                turnFlag = False
                turnCounter = 0
        
        #? this is the overtaking code, which is also a bit rushed and not fully tested, but the general idea is this:
        #? if a car is detected and is within the distance threshold, we set the overtakeCar flag to true, 
        #? which then causes the kart to switch lanes, wait for a certain amount of time, and then switch back. 
        #? the switching is done by setting the switchToLeftLane or switchToRightLane flag to true, which then causes the kart to switch lanes when it detects a broken line.
        #? the timing is done by using the time module to track how long the kart has been in the overtaking state, and then switching back after a certain amount of time has passed.    
        if car:
            try:
                if car[1] < CAR_DISTANCE:
                    # print(f"Car detected at {car[1]}m, overtaking")
                    overtakeCar = True
                    # controller.drive(0)
                    # controller.brake(100)
            except Exception as e:
                print(f"Error getting distance for car: {e}")

        
        if overtakeCar:
            match overtakeCarStep:
                case 0:
                    if BROKEN_LINE_LEFT:
                        switchToLeftLane = True
                    elif BROKEN_LINE_RIGHT:
                        switchToRightLane = True
                    lineDetectionEnabled = False
                    startLaneSwitch = time.time()
                    if time.time() - startLaneSwitch >= laneTime:
                        overtakeCarStep += 1
                        stepTwoStart = time.time()
                    break
                case 1:
                    if time.time() - stepTwoStart >= overtakeDuration:
                        overtakeCarStep += 1
                    break
                case 2:
                    if BROKEN_LINE_LEFT:
                        switchToLeftLane = True
                    elif BROKEN_LINE_RIGHT:
                        switchToRightLane = True
                    lineDetectionEnabled = False
                    startLaneSwitch = time.time()
                    if time.time() - startLaneSwitch >= laneTime:
                        overtakeCarStep = 0
                        overtakeCar = False
                    break

        # ----------------------------------------------------------------

        # ---------------------- line detection --------------------------
        #? this is commented out because if it isnt the code wont run for some reason.
        # if DEBUG:
        #     threadL.request_step()
        #     threadR.request_step()
        #     threadL.wait_for_index(prevLIndex)
        #     threadR.wait_for_index(prevRIndex)
        #     prevLIndex = threadL.latestIndex
        #     prevRIndex = threadR.latestIndex
        
        leftHit  = threadL.latestIntersection
        rightHit = threadR.latestIntersection
        currTime = time.time()
        
        #? this is where we check for hits and update the last hit values, and also determine the mode (both, single-left, single-right, or none)
        #? the mode is used to determine how to compute the lane center, which is then used for the PID controller to compute the steering angle.
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
        
        if mode == "both":
            modes.append("both")

        if (mode == "single-left" and lastMode == "single-left"):
            modes = []
            singleLeftCounter += 1
            if singleLeftCounter >= 10:  # tune this threshold
                BROKEN_LINE_RIGHT = True
        else:
            singleLeftCounter = 0
        
        if (mode == "single-right" and lastMode == "single-right"):
            modes = []
            singleRightCounter += 1
            if singleRightCounter >= 10:  # tune this threshold
                BROKEN_LINE_LEFT = True
        else:
            singleRightCounter = 0
        
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
            lineDetectionEnabled, switchToLeftLane, switchToRightLane = switchLane(LEFT, controller)
        elif switchToRightLane:
            lineDetectionEnabled, switchToLeftLane, switchToRightLane = switchLane(RIGHT, controller)
        else:
            switchLaneOnNextBrokenLine = False

        #? big print to see all the relevant information for debugging
        # print(f"Mode: {mode:12s} | brokenL: {BROKEN_LINE_LEFT} | brokenR: {BROKEN_LINE_RIGHT}", flush=True)
        # print(f"LineFlag: {lineDetectionEnabled} | Mode: {mode:12s} | L: {str(round(lastLeftHit, 2)) if lastLeftHit is not None else 'None':>5} | R: {str(round(lastRightHit, 2)) if lastRightHit is not None else 'None':>5} | Center: {laneCenter:.2f} | Steer: {steer}", flush=True)
        
        #? this is what the code always does unless turned off when doing a maneuver
        if controller is not None and lineDetectionEnabled:
            controller.steer(steer)
            controller.drive(KART_SPEED)
        
        # ----------------------------------------------------------------

        #? this shows you what the code sees
        if threadL.latestFrame is not None:
            cv2.imshow("left", threadL.latestFrame)

        if threadR.latestFrame is not None:
            cv2.imshow("right", threadR.latestFrame)

        if threadM.latestFrame is not None:
            cv2.imshow("middle", threadM.latestFrame)

        #? this stops the code when you press Q while focused on one of the windows
        #? CTRL+C also works but hey, whatever works best for you. 
        if cv2.waitKey(30) & 0xFF == ord('q'):
            threadL.stop()
            threadR.stop()
            threadM.stop()
            break
    
        
    #? this just makes sure that all windows are closed and the connection to the CAN bus is closed when the code is stopped.
    cv2.destroyAllWindows()
    if controller is not None:
        controller.turnOffBus()
