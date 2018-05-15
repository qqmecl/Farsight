import numpy as np
import cv2
import os
from multiprocessing import Process

usb_cameras=[]
detect_baseLine=[]

from configparser import ConfigParser
config_parser = ConfigParser()
config_parser.read("../../local/config.ini")

leftCamerasNum = config_parser.getint("usb_cameras","leftCamerasNum")
rightCamerasNum = config_parser.getint("usb_cameras","rightCamerasNum")
camera_number = leftCamerasNum+rightCamerasNum

camera_height = config_parser.getint("usb_cameras","height")
camera_width = config_parser.getint("usb_cameras","width")

camera_version = config_parser.getint("hardware","camera_version")

for i in range(camera_number):
    content = config_parser.get("usb_cameras","index"+str(i))
    usb_cameras.append(content)
    centerX = config_parser.getint("base_line","centerX"+str(i))
    detect_baseLine.append(centerX)

index = 1

cap = cv2.VideoCapture(usb_cameras[index])


if camera_version == 2:
    cap.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,camera_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,camera_height)

ret=True

while(ret):
    ret, frame = cap.read()
    if ret:
        
        centerX=detect_baseLine[index]

        cv2.rectangle(frame, (centerX-10, 0), (centerX+10, camera_height),(0, 0, 255),3)
        cv2.imshow('frame',frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
     
# Process(target = adjust_cameras, args = (0,)).start()
# Process(target = adjust_cameras, args = (1,)).start()
