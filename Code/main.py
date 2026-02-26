from cv2_enumerate_cameras import enumerate_cameras
import cv2

# class cameraReader:
#     def __init__(self, cap, out, frame):
#         self.cap = cap 
#         self.frame = frame    
#         fourcc = cv.VideoWriter_fourcc(*'XVID')
#         self.out = cv.VideoWriter(out, fourcc, 20.0, (640,  480))

#     def Stream(self):
#         ret, cap_frame = self.cap.read()

#         if not ret:
#             print("Can't receive frame (stream end?). Exiting ...")
#             exit()

#         cv.imshow(self.frame, cap_frame)

#         self.out.write(cap_frame)

#         if cv.waitKey(1) == ord('q'):
#             exit()


# class main:
#     cap = []

#     for camera_info in ec():
#         print(camera_info)
#         if "logitech" in camera_info.name.lower():
#             cap.append(cv.VideoCapture(int(str(camera_info.index)[-1]), camera_info.backend))

#     fourcc = cv.VideoWriter_fourcc(*'XVID')
#     out = cv.VideoWriter('output.avi', fourcc, 20.0, (640,  480))
#     for c in cap:
#         if not c.isOpened():
#             print("Cannot open camera")

#     cameras = []
#     output = ['output1.avi', 'output2.avi', 'output3.avi']
#     frames = ['Right', 'Left', 'Middle']

#     for c in cap:
#         cameras.append(cameraReader(c, output[cap.index(c)], frames[cap.index(c)]))

#     while True:
#         for c in cameras:
#             c.Stream()

#         if cv.waitKey(1) == ord('q'):
#             break

#     for c in cap:
#         c.release()
#     out.release()
#     cv.destroyAllWindows()

class StereoCamera:
    def __init__(self, index, camPos):
        self.cam = cv2.VideoCapture(index, cv2.CAP_V4L2)
        if not self.cam.isOpened():
            print(f"Camera {index} failed to open")
            return None
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'mp4v'))
        self.cam.set(cv2.CAP_PROP_FPS, 30)
        self.cam.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.camPos = camPos
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(
            f"{self.camPos}.mp4",
            fourcc,
            30,
            (640, 480)
        )
        print(f"Stereo Camera {index} initialized.")
        
    def get_frame(self):
        ret, frame = self.cam.read()
        if not ret:
            print("Failed to grab frame")
            return None
        cv2.imshow(f"{self.camPos}", frame)
        self.writer.write(frame)
        # return frame

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
    cams = []
    
    for id, name in zip(ids, names):
        cams.append(StereoCamera(id, name))

    while True:
        for cam in cams:
            cam.get_frame()