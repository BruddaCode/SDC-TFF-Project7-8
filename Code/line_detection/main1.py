from cv2_enumerate_cameras import enumerate_cameras
import cv2
from StereoCamera import StereoCamera
from LineDetector import LineDetector
import threading

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
    # camL = StereoCamera(ids[0], names[0])
    # camM = StereoCamera(ids[1], names[1])
    # camR = StereoCamera(ids[2], names[2])
    detector = LineDetector()
    # cam = StereoCamera(0, "Bert")
    video = cv2.VideoCapture("../Test-Videos-12-03/test3-720/left.mp4") 
    video2 = cv2.VideoCapture("../Test-Videos-12-03/test3-720/right.mp4")
    

    def processFrame(video, name):
        while True:
            ret, frame = video.read()
            if not ret:
                break
            frame = frame[0:449, 0:639]
            print(detector.getIntersection(frame))
            # cv2.imshow(name, coolshit)
            if cv2.waitKey(30) & 0xFF == ord('q'):
                break
    
    processFrame(video, "jeff")
    # thread = threading.Thread(target=processFrame, args=(video, "Bert"))
    # thread2 = threading.Thread(target=processFrame, args=(video2, "Ernie"))
    # thread.start()
    # thread2.start()
    # thread.join()
    # thread2.join()
    # video.release()
    # video2.release()