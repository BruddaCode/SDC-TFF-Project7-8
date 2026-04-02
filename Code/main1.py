from cv2_enumerate_cameras import enumerate_cameras
import cv2
from line_detection.StereoCamera import StereoCamera
from line_detection.LineDetector import LineDetector
from line_detection.LineThread import LineThread
from rijden.carcontroller import CarController

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
    ids = getCameraId("logitech")
    names = ["left", "middle", "right"]
    camL = StereoCamera(ids[0], names[0])
    camM = StereoCamera(ids[1], names[1])
    camR = StereoCamera(ids[2], names[2])
    detector = LineDetector()
    # video = cv2.VideoCapture("../Test-Videos-12-03/test3-720/left.mp4") 
    # video2 = cv2.VideoCapture("../Test-Videos-12-03/test3-720/right.mp4")
    roi = [(0,449), (0,639), (640,1279)]
    controller = CarController()
    

    thread = LineThread(camL, detector, controller, roi[0], roi[1])
    thread2 = LineThread(camR, detector, controller, roi[0], roi[2])
    thread.start()
    thread2.start()
    while True:
        frame = thread.latestFrame
        if frame is not None:
            cv2.imshow("Bert", frame)
        frame = thread2.latestFrame
        if frame is not None:
            cv2.imshow("Ernie", frame)
        if cv2.waitKey(30) & 0xFF == ord('q'):
            thread.stop()
            thread2.stop()
            break
    cv2.destroyAllWindows()