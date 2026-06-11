from ultralytics.models.yolo.model import YOLO
import numpy as np
import threading
import time
import json
import cv2
import os  

class ObjectDetector(threading.Thread):
    def __init__(self, cam):
        super().__init__()
        with open(os.path.join(os.path.dirname(__file__), '..', 'config.json'), 'r') as file:
            self.config = json.load(file)
        
        try:
            self.model = YOLO(os.path.join(os.path.dirname(__file__), 'TheNewestModel', 'TheSigmaModel_openvino_model'))
        except Exception as e:
            print(f"Error loading model: {e}")
        
        self.cam = cam
        self.running = True
        self.latestFrame = None
        self.latestDetections = None
        
        self.width = self.config["Camera"]["width"]
        self.height = self.config["Camera"]["height"]
        self.intrinsicsKey = self.config["Camera"]["intrinsicMatrix"]
        self.distortionKey = self.config["Camera"]["distCoeffs"]
        self.confThreshold = self.config["ObjectDetection"]["confidenceThreshold"]
        self.classColors = self.config["ObjectDetection"]["ClassColors"]
        self.objectRealSize = self.config["ObjectDetection"]["ObjectRealSize"]

        self.cameraMatrix = np.array([
            [self.intrinsicsKey["fx"], 0, self.intrinsicsKey["cx"]],
            [0, self.intrinsicsKey["fy"], self.intrinsicsKey["cy"]],
            [0, 0, 1]
        ], dtype=np.float64)
        self.distCoeffs = np.array([
            self.distortionKey["k1"],
            self.distortionKey["k2"],
            self.distortionKey["p1"],
            self.distortionKey["p2"],
            self.distortionKey["k3"]
        ], dtype=np.float64)

        self.UNDISTORTMAP = self.buildUndistortMap()
    
    def buildUndistortMap(self):
        matrix, _ = cv2.getOptimalNewCameraMatrix(self.cameraMatrix, self.distCoeffs, (self.width, self.height), 0, (self.width, self.height))
        map1, map2 = cv2.initUndistortRectifyMap(self.cameraMatrix, self.distCoeffs, None, matrix, (self.width, self.height), cv2.CV_16SC2)
        return (map1, map2)

    def undistort(self, frame):
        return cv2.remap(frame, self.UNDISTORTMAP[0], self.UNDISTORTMAP[1], cv2.INTER_LINEAR)
    
    def estimateDistance(self, bboxSize, label):
        if label not in self.objectRealSize:
            print(f"Unknown label for distance estimation: {label}")
            return None
        realSize, useHeight = self.objectRealSize[label]
        if useHeight:
            bboxSize = bboxSize[1]
            focalLength = self.intrinsicsKey["fy"] * (self.height / 1080)
        else:
            bboxSize = bboxSize[0]
            focalLength = self.intrinsicsKey["fx"] * (self.width / 1920)
        if bboxSize <= 0:
            print(f"Invalid bbox size for distance estimation: {bboxSize}")
            return None
        distance = (realSize * focalLength) / bboxSize
        return round(distance, 1)

    def drawDetection(self, frame, bboxPoints, label, color, distance, confidence):
        x1, y1 = bboxPoints[0]
        x2, y2 = bboxPoints[1]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        boundingBoxMiddle = ( x1 + x2 ) / 2
        cv2.circle(frame, (int(boundingBoxMiddle), y1), 5, (255, 0, 255), -1)
        
        labelText = f"{label}, {confidence:.2f}"
        (textWidth, textHeight), _ = cv2.getTextSize(labelText, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(frame, (x1, y1 - textHeight - 10), (x1 + textWidth, y1), color, -1)
        cv2.putText(frame, labelText, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        
        if distance is not None:
            distanceText = f"{distance}m"
            (textWidth, textHeight), _ = cv2.getTextSize(distanceText, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame, (x1, y1 - textHeight - 30), (x1 + textWidth, y1 - textHeight - 10), color, -1)
            cv2.putText(frame, distanceText, (x1, y1 - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        return frame

    def processDetections(self, frame, detections):
        boxes = detections[0].boxes
        drawnFrame = frame.copy()
        detectionsList = []
        for box in boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            bboxPoints = [(x1, y1), (x2, y2)]
            label = self.model.names[cls]
            color = self.classColors.get(label, self.classColors["default"])
            boundingBoxWidth = x2 - x1
            boundingBoxHeight = y2 - y1
            boundingBoxMiddle = ( x1 + x2 ) / 2

            distance = self.estimateDistance((boundingBoxWidth, boundingBoxHeight), label)
            drawnFrame = self.drawDetection(drawnFrame, bboxPoints, label, color, distance, conf)
            detectionsList.append((label, distance, boundingBoxMiddle))
        return drawnFrame, detectionsList

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            frame = self.cam.getFrame()
            if frame is None:
                continue
            
            frame = self.undistort(frame)
            results = self.model(frame, conf=self.confThreshold, verbose=False, task="detect")
            self.latestFrame, self.latestDetections = self.processDetections(frame, results)