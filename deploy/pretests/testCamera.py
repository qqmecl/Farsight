import numpy as np
import cv2 as cv
import os
from PIL import Image, ImageDraw, ImageFont 



items = {
    '001001': dict(name='农夫山泉矿泉水', price=2.0, weight=575.0),
    '002004': dict(name='美汁源果粒橙', price=5.0, weight=487.0),
    '006001': dict(name='红牛', price=8.0, weight=298.0),
    '007001': dict(name='脉动', price=6.5, weight=546.0),
    '008001': dict(name='三得利乌龙茶', price=6.0, weight=528.0),
    '009001': dict(name='冰糖雪梨', price=6.0, weight=549.0),
    '010001': dict(name='维他柠檬茶', price=7.0, weight=552.0),
    '002001': dict(name='雪碧听装', price=3.5, weight=343.0),
    '002002': dict(name='可口可乐听装', price=3.5, weight=354.0),
    '003001': dict(name='统一阿萨姆奶茶', price=6.5, weight=550.0),
    '003002': dict(name='小茗同学黄色', price=6.5, weight=546.0),
    '003003': dict(name='汤达人豚骨面', price=13.5, weight=184.0),
}

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


MODEL_PATH = os.path.join(os.getcwd(), '../../data/', 'frozen_inference_graph.pb')
DESCRIPTION_PATH = os.path.join(os.getcwd(), '../../data/', 'ssd_mobilenet_v1_coco.pbtxt')
detectionNet = cv.dnn.readNetFromTensorflow(MODEL_PATH,DESCRIPTION_PATH)
classNames = {0: 'background',
                  1: '010001', 2: '002004', 3: '006001', 4: '007001', 5: '008001', 6: '009001',
                  7: '001001', 8: '002001', 9: '002002', 10: '003001', 11: '003002',
                  12: '003003'}


def detect_objects(frame):
    global detectionNet,classNames

    inScaleFactor,meanVal = 0.007843,127.5
    inWidth,inHeight = 300,300

    resize = frame[:,160:,:]
    # last_time=time.time()

    blob = cv.dnn.blobFromImage(resize, inScaleFactor, (inWidth, inHeight), (meanVal, meanVal, meanVal),
                                True)
    detectionNet.setInput(blob)
    detections = detectionNet.forward()
    # print("Detect consume time:",time.time()-last_time)

    rows = resize.shape[0]
    cols = resize.shape[1]

    maxConfidence = 0
    itemId=None

    pos=[]
    for i in range(4):
        pos.append(0)
    real_calssId = None

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        class_id = int(detections[0, 0, i, 1])

        xLeftBottom = int(detections[0, 0, i, 3] * cols)
        yLeftBottom = int(detections[0, 0, i, 4] * rows)
        
        xRightTop = int(detections[0, 0, i, 5] * cols)
        yRightTop = int(detections[0, 0, i, 6] * rows)

        XAxis = (xLeftBottom + xRightTop) / 2
        YAxis = (yLeftBottom + yRightTop) / 2

        try:
            # itemId = self.classNames[class_id]
            # print(settings.items[itemId]["name"])
            if confidence > 0.8:
                #location = self.getDetectPos(XAxis,YAxis,index)
                if XAxis > 100 and confidence > maxConfidence:
                    itemId = classNames[class_id]
                    maxConfidence = confidence

                    pos[0] = xLeftBottom
                    pos[1] = yLeftBottom
                    pos[2] = xRightTop
                    pos[3] = yRightTop

                    real_calssId = class_id
        except KeyError:
            print("class_id is: ",class_id)
            pass

    if maxConfidence !=0:
        cv.rectangle(frame, (pos[0]+160, pos[1]+160), (pos[2], pos[3]),(0, 255, 0))

        if real_calssId in classNames:
            label = items[itemId]["name"] + ": " + str(confidence)
            labelSize, baseLine = cv.getTextSize(label, cv.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            pos[1] = max(pos[1], labelSize[1])
            frame = addChineseText(frame,label,(pos[0], pos[1]+50))

    return frame


def addChineseText(frame,label,pos):
    # 图像从OpenCV格式转换成PIL格式  
    img_PIL = Image.fromarray(cv.cvtColor(frame, cv.COLOR_BGR2RGB))  
  
    font = ImageFont.truetype('STHeiti_Medium.ttc', 20)

    fillColor = (255,0,0)  
  
    draw = ImageDraw.Draw(img_PIL)  
    
    draw.text(pos, label, font=font, fill=fillColor)  
  
    # 转换回OpenCV格式  
    frame = cv.cvtColor(np.asarray(img_PIL),cv.COLOR_RGB2BGR)  

    return frame


index = 2
cap = cv.VideoCapture(usb_cameras[index])
ret=True

while(ret):
    ret, frame = cap.read()
    if ret:
        if index > 1:
            frame = cv.flip(frame,1)
        frame = detect_objects(frame)
        cv.imshow('frame',frame)
        if cv.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv.destroyAllWindows()
 


