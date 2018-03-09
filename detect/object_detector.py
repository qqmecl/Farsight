import signal
import os
import cv2 as cv
from multiprocessing import Queue, Pool
import queue
from setproctitle import setproctitle
import time

from detect.area import AreaCheck
import settings




CWD_PATH = os.getcwd()

# print(CWD_PATH)

if CWD_PATH != '/':
    # MODEL_PATH = os.path.join(CWD_PATH + '/data/' + 'frozen_inference_graph_2_7.pb')
    MODEL_PATH = os.path.join(CWD_PATH + '/data/' + 'frozen_inference_graph.pb')
    DESCRIPTION_PATH = os.path.join(CWD_PATH + '/data/' + 'ssd_mobilenet_v1_coco.pbtxt')
else:
    MODEL_PATH = os.path.join('/home/votance/Projects/Farsight' + CWD_PATH + 'data/' + 'frozen_inference_graph_2_7.pb')
    DESCRIPTION_PATH = os.path.join('/home/votance/Projects/Farsight' + CWD_PATH + 'data/' + 'ssd_mobilenet_v1_coco.pbtxt')


transfer_table={
    '001001':'6921168509256',
    '002004':'6956416200067',
    '006001':'6920202888883',
    '007001':'6902538006100',
    '008001':'6921581596048',
    '009001':'6920459989463',
    '010001':'4891028705949',
    '002001':'6901939621271',
    '002002':'6901939621608',
    '003001':'6925303730574',
    '003002':'6925303754952',
    '003003':'6925303714857',
}

class ObjectDetector:
    def __init__(self,input_q,items,detection_queue,hardware_mode="CPU"):
        setproctitle('[farsight-offline] Detect图像处理进程')
        #忽略 SIGINT，由父进程处理
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        if hardware_mode == "GPU":
            import tensorflow as tf
            import numpy as np
            
            with tf.gfile.GFile(MODEL_PATH, 'rb') as f:
              # Load the model
              self.detection_graph = tf.GraphDef()
              self.detection_graph.ParseFromString(f.read())

            with tf.Session() as tf_sess:
              self.tf_sess = tf_sess
              self.tf_sess.graph.as_default()
              tf.import_graph_def(self.detection_graph, name='')
        else:
            self.detectionNet = cv.dnn.readNetFromTensorflow(MODEL_PATH,DESCRIPTION_PATH)


        self.frameCount = 0
        self.confidenceThreshold=0.7
        self.items = items
        self.timeStamp = time.strftime('%Y_%m_%d_%H_%M_%S_',time.localtime(time.time()))
        #Temporary
        self.classNames = {0: 'background',
                  1: '010001', 2: '002004', 3: '006001', 4: '007001', 5: '008001', 6: '009001',
                  7: '001001', 8: '002001', 9: '002002', 10: '003001', 11: '003002',
                  12: '003003'}

        rCenter=320
        rcLen = 10

        while True:
            try:
                frame,index,frame_time = input_q.get(timeout=1)
                if index > 1:
                    frame = cv.flip(frame,1)

                frame_truncated = frame[:, 160: , :]

                last_time = time.time()
                results = self.detect_objects(frame_truncated,index,frame_time,hardware_mode)
                    # print()
                # print("consume ",time.time()-last_time," for every second!")

                if detection_queue.full():#此种情况一般不应该发生，主进程要做到能够处理每一帧图像
                    print("object delte detect")
                    waste = detection_queue.get_nowait()
                try:
                    detection_queue.put_nowait([index,frame[:,rCenter-rcLen:rCenter+rcLen],results,frame_time])#not a good structure
                except queue.Full:
                    print('[FULL]')
                    pass
            except queue.Empty:#不进行识别判断的时候帧会变空
                # print('[EMPTY] input_q is: ')
                pass

    ##当前只考虑单帧的判断
    def detect_objects(self,frame,index,frame_time,hardware_mode):
        self.frameCount += 1
        results=[]
        maxConfidence = 0
        maxItemId=""

        if hardware_mode == "GPU":
            rows = frame.shape[0]
            cols = frame.shape[1]
            frame = cv.resize(frame, (300, 300))
            frame = frame[:, :, [2, 1, 0]]  # BGR2RGB
            out = self.tf_sess.run([self.tf_sess.graph.get_tensor_by_name('num_detections:0'),
                              self.tf_sess.graph.get_tensor_by_name('detection_scores:0'),
                              self.tf_sess.graph.get_tensor_by_name('detection_boxes:0'),
                              self.tf_sess.graph.get_tensor_by_name('detection_classes:0')],
                             feed_dict={'image_tensor:0': frame.reshape(1, frame.shape[0], frame.shape[1], 3)})
            num_detections = int(out[0][0])
            for i in range(num_detections):
                classId = int(out[3][0][i])
                confidence = float(out[1][0][i])
                bbox = [float(v) for v in out[2][0][i]]
                if confidence > maxConfidence and confidence > self.confidenceThreshold:
                    XAxis = (bbox[1]+bbox[3])/2*cols
                    YAxis = (bbox[0]+bbox[2])/2*rows
                    if AreaCheck(XAxis,YAxis,index).passBaseLine():
                        maxItemId = self.classNames[int(classId)]
                        maxConfidence = confidence

        else:
            inWidth,inHeight = 300,300
            resize = cv.resize(frame,(inWidth,inHeight))
            inScaleFactor,meanVal = 0.007843,127.5

            blob = cv.dnn.blobFromImage(resize, inScaleFactor, (inWidth, inHeight), (meanVal, meanVal, meanVal),
                                    True)

            self.detectionNet.setInput(blob)
            detections = self.detectionNet.forward()

            rows = frame.shape[0]
            cols = frame.shape[1]

            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                class_id = int(detections[0, 0, i, 1])

                xLeftBottom = int(detections[0, 0, i, 3] * cols)
                yLeftBottom = int(detections[0, 0, i, 4] * rows)
                
                xRightTop = int(detections[0, 0, i, 5] * cols)
                yRightTop = int(detections[0, 0, i, 6] * rows)

                XAxis = (xLeftBottom + xRightTop) / 2
                YAxis = (yLeftBottom + yRightTop) / 2
                
                itemId = self.classNames[class_id]
                if confidence > self.confidenceThreshold and confidence > maxConfidence:
                    if AreaCheck(XAxis,YAxis,index).passBaseLine():
                            maxConfidence = confidence
                            maxItemId = itemId
                

        if maxConfidence !=0:
            if transfer_table[maxItemId]:
                maxItemId = transfer_table[maxItemId]
            results.append((maxConfidence,maxItemId,frame_time))
      
        return results#默认返回空值