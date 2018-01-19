import numpy as np
import cv2


usb_cameras=["/dev/v4l/by-path/pci-0000:00:14.0-usb-0:9:1.0-video-index0",
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:10:1.0-video-index0",
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:6:1.0-video-index0",
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:8:1.0-video-index0"
]

index = 0

cap = cv2.VideoCapture(usb_cameras[index])

while(True):
    # Capture frame-by-frame
    ret, frame = cap.read()

    # Our operations on the frame come here
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Display the resulting frame
    cv2.imshow('frame',gray)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()