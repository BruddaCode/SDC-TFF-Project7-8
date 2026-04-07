import cv2
import numpy as np
import glob
import os

# Chessboard dimensions (internal corners)
grid_size = (9, 6) # uit mijn hoofd moet je alleen de interne hoeken tellen, dus 10x7 squares = 9x6 corners ff als voorbeeld, pas aan naar jouw bord
square_size = 2.0  # cm
cameraID = 0  # cameraID, moet je ff mee spelen, begin met 0 en als dat niet werkt, probeer 1, 2, etc. totdat je de middelste camera hebt gevonden
amount_of_frames = 20 # hoeveelheid fotos die je wilt maken.
resolution = (1920, 1080) 
fps = 30
auto_focus = 0  # 0 = uit, 1 = aan, kan calibratie beïnvloeden, dus kloot er maar wat mee
path = os.path.join(os.getcwd(), 'calibration_images') # gooit de foto's in een map genaamd 'calibration_images' in de huidige werkmap

if not os.path.exists(path):
    os.makedirs(path)

cam = cv2.VideoCapture(cameraID, cv2.CAP_V4L2)
# v4l2-ctl -d /dev/video0 --list-formats-ext <---- dat in de terminal gooien om te kijken welke formaten beschikbaar zijn
cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cam.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
cam.set(cv2.CAP_PROP_FPS, fps)
cam.set(cv2.CAP_PROP_AUTOFOCUS, auto_focus)

# Create a resizable window with a larger display size
cv2.namedWindow("Calibration", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Calibration", resolution[0], resolution[1])

if not cam.isOpened():
    print(f"Camera {cameraID} failed to open")
    exit(1)

print("Camera initialized. Press SPACE to capture an image, or ESC to exit.")
print(cam.get(cv2.CAP_PROP_FRAME_WIDTH), cam.get(cv2.CAP_PROP_FRAME_HEIGHT), cam.get(cv2.CAP_PROP_FPS), cam.get(cv2.CAP_PROP_AUTOFOCUS))

while True:    
    ret, frame = cam.read()
    cv2.imshow("Calibration", frame)
    key = cv2.waitKey(30)
    if key % 256 == 27:  # ESC to exit
        print("Calibration process interrupted by user.")
        cam.release()
        cv2.destroyAllWindows()
        exit(1)
        break
    elif key % 256 == 32:  # SPACE to capture image
        img_name = os.path.join(path, f"calibration_{amount_of_frames}.jpg")
        cv2.imwrite(img_name, frame)
        print(f"Captured {img_name}")
        amount_of_frames -= 1
        if amount_of_frames == 0:
            print("Captured all required images.")
            break

cam.release()
cv2.destroyAllWindows()


# Create 3D object points
obj_points = np.zeros((grid_size[0] * grid_size[1], 3), np.float32)
obj_points[:, :2] = np.mgrid[0:grid_size[0], 0:grid_size[1]].T.reshape(-1, 2) * square_size

obj_points_list = []
img_points_list = []

# Load calibration images
images = glob.glob(os.path.join(path, 'calibration_*.jpg'))
for fname in images:
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, grid_size, None)
    if ret:
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1),
                                   (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
        obj_points_list.append(obj_points)
        img_points_list.append(corners)

# Perform calibration
ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
    obj_points_list, img_points_list, gray.shape[::-1], None, None)

print("Camera Matrix:\n", camera_matrix)
print("Distortion Coefficients:\n", dist_coeffs)
print("Reprojection Error:", ret)

# Save calibration data
# save as txt file also for easy access
np.savetxt(os.path.join(path, 'camera_data.txt'), (camera_matrix, dist_coeffs, ret), fmt='%s', header='Camera Matrix, Distortion Coefficients, Reprojection Error')
np.savez(os.path.join(path, 'calibration_data.npz'), camera_matrix=camera_matrix, dist_coeffs=dist_coeffs)   