import cv2
import numpy as np

video = cv2.VideoCapture("right_1.mp4")

while True:
	ret, frame = video.read()
	if not ret:
		break

	kernel = np.array([[100, 5, 100],[5, 100, 5],[100, 5, 100]])

	# apply gaussian blur for less noise on the frame
	filteredFrame = cv2.GaussianBlur(frame, (5, 5), 1.4)

	# Turn the frame gray
	filteredFrame = cv2.cvtColor(filteredFrame, cv2.COLOR_BGR2GRAY)
	
	filteredFrame = cv2.inRange(filteredFrame, 195, 255)

	# filter between dark and light and make dark black and light white
	_, filteredFrame = cv2.threshold(filteredFrame, 200, 255, cv2.THRESH_BINARY)

	dst = cv2.filter2D(filteredFrame, -1, kernel)

	# apply canny edge detection to see adges of objects
	filteredFrame = cv2.Canny(dst, threshold1=70, threshold2=150)

	lines = cv2.HoughLinesP(filteredFrame,1,np.pi/180,100,minLineLength=30,maxLineGap=50)
	if lines is not None:
		for line in lines:
			x1,y1,x2,y2 = line[0]
			cv2.line(frame,(x1,y1),(x2,y2),(0,0,255),2)  
             
	cv2.imshow("idono", dst)
	cv2.imshow("white", frame)
	# cv2.imshow("original", frame[0:319, 210:640])

	if cv2.waitKey(33) & 0xFF == ord('q'):
		break