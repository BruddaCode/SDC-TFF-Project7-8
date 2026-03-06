from cv2_enumerate_cameras import enumerate_cameras
import yaml
import sys
import cv2
import os

def getCameraId(cameraName):
    cameraIDs = []
    
    for camera_info in enumerate_cameras():
        if cameraName.lower() in camera_info.name.lower():
            if int(str(camera_info.index)[-1]) not in cameraIDs:
                cameraIDs.append(int(str(camera_info.index)[-1]))
        else:
            print(f"Camera '{camera_info.name}' does not match the specified name '{cameraName}'.")
        
    return cameraIDs

class StereoCamera:
    def __init__(self, index, camPos):
        self.cam = cv2.VideoCapture(index, cv2.CAP_V4L2)

        self.config = yaml.safe_load(open("conf.yaml"))
        self.config = self.config[f"test{sys.argv[1]}"].split(", ")

        # make sure the directory exists
        if not os.path.exists(os.path.join(os.getcwd(), f"{self.config[3]}-{self.config[1]}")):
            os.makedirs(os.path.join(os.getcwd(), f"{self.config[3]}-{self.config[1]}"))

        if not self.cam.isOpened():
            raise RuntimeError(f"Camera {index} failed to open")
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.config[0]))
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.config[1]))
        self.cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'mp4v'))
        self.cam.set(cv2.CAP_PROP_FPS, int(self.config[2]))
        self.cam.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.camPos = camPos
        
        print(self.cam.get(cv2.CAP_PROP_FRAME_WIDTH), self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT), self.cam.get(cv2.CAP_PROP_FPS))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(
            os.path.join(os.getcwd(), f"{self.config[3]}-{self.config[1]}", f"{self.camPos}.mp4"),
            fourcc,
            (int(self.config[2])),
            (int(self.config[0]), int(self.config[1]))
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



if __name__ == "__main__":
    ids = getCameraId("logitech")
    names = ["left", "middle", "right"]
    camL = StereoCamera(ids[0], names[0])
    # camM = StereoCamera(ids[1], names[1])
    # camR = StereoCamera(ids[2], names[2])
    
    while True:
        camL.get_frame()
        # camM.get_frame()
        # camR.get_frame()
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            camL.cam.release()
            # camM.cam.release()
            # camR.cam.release()
            cv2.destroyAllWindows()
            break

