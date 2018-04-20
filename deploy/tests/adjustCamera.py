import numpy as np
import cv2
import os

usb_cameras=[]
if os.path.exists("../../local/config.ini"):
    from configparser import ConfigParser
    config_parser = ConfigParser()
    config_parser.read("../../local/config.ini")
    for i in range(4):
        content = config_parser.get("usb_cameras","index"+str(i))
        usb_cameras.append(content)
    #config_parser.close()
else:
    usb_cameras=[
    "/dev/v4l/by-path/pci-0000:00:14.0-usb-0:10:1.0-video-index0",
    "/dev/v4l/by-path/pci-0000:00:14.0-usb-0:9:1.0-video-index0",
    "/dev/v4l/by-path/pci-0000:00:14.0-usb-0:6:1.0-video-index0",#done
    "/dev/v4l/by-path/pci-0000:00:14.0-usb-0:8:1.0-video-index0"
    ]

index = 0
cap = cv2.VideoCapture(usb_cameras[index])
ret=True


DEFAULT_WIDTH=640
DEFAULT_HEIGHT=480

while(ret):
    ret, frame = cap.read()
    if ret:
        
        
        centerX=315

        cv2.rectangle(frame, (centerX-10, 0), (centerX+10, DEFAULT_HEIGHT),(0, 0, 255),3)
        cv2.imshow('frame',frame)
        cv2.imwrite('frame.png',frame)

        # if index > 1:
        #     frame = cv2.flip(frame,1)

        # if index%2 == 1:
        #     frame = frame[:, 160: , :]#Camera downstairs
        # else:
        #     frame = frame[:, 260: , :]#Camera upstairs

        # cv2.imshow('frame',frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
 


