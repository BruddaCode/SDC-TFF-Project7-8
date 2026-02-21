from cv2_enumerate_cameras import enumerate_cameras as ec
import cv2 as cv

class cameraReader:
    def __init__(self, cap, out, frame):
        self.cap = cap 
        self.frame = frame    
        fourcc = cv.VideoWriter_fourcc(*'XVID')
        self.out = cv.VideoWriter(out, fourcc, 20.0, (640,  480))

    def Stream(self):
        ret, cap_frame = self.cap.read()

        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            exit()

        cv.imshow(self.frame, cap_frame)

        self.out.write(cap_frame)

        if cv.waitKey(1) == ord('q'):
            exit()


class main:
    cap = []

    for camera_info in ec(cv.CAP_MSMF):
        print(camera_info)
        if "logitech" in camera_info.name.lower():
            cap.append(cv.VideoCapture(camera_info.index, camera_info.backend))

    fourcc = cv.VideoWriter_fourcc(*'XVID')
    out = cv.VideoWriter('output.avi', fourcc, 20.0, (640,  480))
    for c in cap:
        if not c.isOpened():
            print("Cannot open camera")
            print(c.index)
            exit()

    cameras = []
    output = ['output1.avi', 'output2.avi', 'output3.avi']
    frames = ['Right', 'Left', 'Middle']

    for c in cap:
        cameras.append(cameraReader(c, output[cap.index(c)], frames[cap.index(c)]))

    while True:
        for c in cameras:
            c.Stream()

        if cv.waitKey(1) == ord('q'):
            break

    for c in cap:
        c.release()
    out.release()
    cv.destroyAllWindows()    