import cv2
import numpy as np

video = cv2.VideoCapture("code/right.mp4")
video.open("right.mp4")

if not video.isOpened():
	print("tering ding")

while True:
    ret, frame = video.read()

    if not ret:
		print("wat de fuck man")
		break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian Blur to reduce noise
    blur = cv2.GaussianBlur(gray, (5, 5), 1.4)

    # Apply Canny Edge Detector
    edges = cv2.Canny(blur, threshold1=10, threshold2=150)

	try:
        lines = cv2.HoughLinesP(edges,1,np.pi/180,100,minLineLength=200,maxLineGap=10)
	except:
        print("kut zooi")
        

    if not lines.size == 0:
        for line in lines:
			x1,y1,x2,y2 = line[0]
			cv2.line(frame,(x1,y1),(x2,y2),(0.255,0),2)

    cv2.imshow("Houghlines", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
		break