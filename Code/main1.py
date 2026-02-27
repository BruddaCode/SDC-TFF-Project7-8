from cv2_enumerate_cameras import enumerate_cameras
import cv2
from StereoCamera import GrayStereoCamera, StereoCamera

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
    # camM = StereoCamera(ids[1], names[1])
    # camR = GrayStereoCamera(ids[2], names[2])
    
    while True:
        camL.get_frame()
        # camM.get_frame()
        # camR.get_frame()
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break