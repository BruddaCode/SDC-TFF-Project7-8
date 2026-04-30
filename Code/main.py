from line_detection.StereoCamera import StereoCamera
from line_detection.LineThread import LineThread
from rijden.carcontroller import CarController

from cv2_enumerate_cameras import enumerate_cameras
import cv2
import json

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
    index = getCameraId("logitech")
    names = ["left", "middle", "right"]
    camL = StereoCamera(index=index[1], camPos=names[0])
    camR = StereoCamera(index=index[2], camPos=names[2])
    

    while True:
        frame = camL.getFrame()
        # line for left cam
        # cv2.line(frame, (1130,720), (135,0) , (255,255,255),2)
        # line for right cam
        # cv2.line(frame, (165, 720), (1280,35), (255,255,255), 2)
        cv2.imshow("frame", frame)
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()