from cv2_enumerate_cameras import enumerate_cameras
import cv2
from StereoCamera import StereoCamera
from LineDetector import LineDetector
from LineThread import LineThread
import queue
import time

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
    video = cv2.VideoCapture("../Test-Videos-12-03/test3-720/left.mp4") 
    video2 = cv2.VideoCapture("../Test-Videos-12-03/test3-720/right.mp4")
    roi1 = (0,449)
    roi2 = (0,639)
    roi3 = (640, 1279)
    outputQueue1 = queue.Queue(maxsize=5)
    outputQueue2 = queue.Queue(maxsize=5)

    

    def processFrame(video, name):
        while True:
            ret, frame = video.read()
            if not ret:
                break
            frame = frame[0:449, 0:639]
            intersection, frame = detector.getIntersection(frame)
            if intersection is not None and intersection[1] > 0.6 * 449:
                print("STUREN!!!!!")
            cv2.imshow(name, frame)
            if cv2.waitKey(30) & 0xFF == ord('q'):
                break
    
    # processFrame(video, "jeff")
    thread = LineThread(video, detector, roi1, roi2, outputQueue1)
    thread2 = LineThread(video2, detector, roi1, roi3, outputQueue2)
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
            break
    # thread.join()
    # thread2.join()
    cv2.destroyAllWindows()