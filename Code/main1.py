from line_detection.StereoCamera import StereoCamera
from line_detection.LineThread import LineThread
from rijden.carcontroller import CarController

from cv2_enumerate_cameras import enumerate_cameras
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
    ids = getCameraId("logitech")
    names = ["left", "middle", "right"]
    # camM = StereoCamera(id=ids[1], camPos=names[1]) # voor nu niet nodig
    # camL = StereoCamera(id=ids[0], camPos=names[0])
    # camR = StereoCamera(id=ids[2], camPos=names[2])
    camL = StereoCamera(videoPath="2026-04-02-test3-720/left.mp4", camPos=names[0])
    camR = StereoCamera(videoPath="2026-04-02-test3-720/right.mp4", camPos=names[2])
    roi = [(0,449), (0,639), (640,1279)]
    controller = CarController()
    
    thread = LineThread(camL, controller, (roi[0], roi[1]))
    thread2 = LineThread(camR, controller, (roi[0], roi[2]))
    thread.start()
    thread2.start()
    while True:
        frame = thread.latestFrame
        if frame is not None:
            cv2.imshow(camL.camPos, frame)
        frame = thread2.latestFrame
        if frame is not None:
            cv2.imshow(camR.camPos, frame)
        if cv2.waitKey(30) & 0xFF == ord('q'):
            thread.stop()
            thread2.stop()
            break
    cv2.destroyAllWindows()