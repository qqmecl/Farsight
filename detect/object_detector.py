import signal
import os
import cv2 as cv
import numpy as np
from multiprocessing import Queue, Pool
import queue
from setproctitle import setproctitle
import time
import common.settings as settings
from detect.dynamic_track import DynamicTrack

CWD_PATH = os.getcwd()
if CWD_PATH != '/':
    MODEL_PATH = os.path.join(CWD_PATH + '/data/' + 'frozen_inference_graph.pb')
    DESCRIPTION_PATH = os.path.join(CWD_PATH + '/data/' + 'ssd_mobilenet_v1_coco.pbtxt')
else:
    MODEL_PATH = os.path.join('/home/votance/Projects/Farsight' + CWD_PATH + 'data/' + 'frozen_inference_graph.pb')
    DESCRIPTION_PATH = os.path.join('/home/votance/Projects/Farsight' + CWD_PATH + 'data/' + 'ssd_mobilenet_v1_coco.pbtxt')

class ObjectDetector:
    def __init__(self,input_q,items,detection_queue,hardware_mode="CPU"):
        setproctitle('[farsight] model_inferencing_processor')

        signal.signal(signal.SIGINT, signal.SIG_IGN)

        if hardware_mode == "GPU":
            import tensorflow as tf
            
            with tf.gfile.GFile(MODEL_PATH, 'rb') as f:
              self.detection_graph = tf.GraphDef()
              self.detection_graph.ParseFromString(f.read())

            with tf.Session() as tf_sess:
              self.tf_sess = tf_sess
              self.tf_sess.graph.as_default()
              tf.import_graph_def(self.detection_graph, name='')
        else:
            self.detectionNet = cv.dnn.readNetFromTensorflow(MODEL_PATH,DESCRIPTION_PATH)

        self.frameCount = 0
        self.confidenceThreshold=0.9
        self.items = items
        self.timeStamp = time.strftime('%Y_%m_%d_%H_%M_%S_',time.localtime(time.time()))
        self.dynamicTracker=[]

        for i in range(2):
            self.dynamicTracker.append(DynamicTrack())

        #Temporary
        self.classNames = {0: 'background',
                  1: '6921168509256001', 2: '6956416200067001', 3: '6920202888883001', 4: '6902538006100001', 5: '6921581596048001', 6: '6920459989463001',
                  7: '4891028705949001', 8: '6901939621271001', 9: '6901939621608001', 10: '6925303730574001', 11: '6925303754952001',
                  12: '6925303714857001',13: '0000000000000001'}

        while True:
            try:
                frame_truncated,index,frame_time,motionType = input_q.get(timeout=1)
                frame_truncated = self.dynamicTracker[index].check(frame_truncated)#get dynamic tracked location
                results = []

                if frame_truncated is not None:
                    row = frame_truncated.shape[0]
                    col = frame_truncated.shape[1]
                    if row>col:
                        fill = np.zeros((row,row-col,3),np.uint8)
                        frame_truncated = np.concatenate((frame_truncated,fill),1)
                    else:
                        fill = np.zeros((col-row,col,3),np.uint8)
                        frame_truncated = np.concatenate((frame_truncated,fill),0)

                    results = self.detect_objects(frame_truncated,index,frame_time,hardware_mode)

                # if len(results) >0:
                    # cv.imwrite(str(index)+"/frame"+str(self.frameCount)+"_"+str(settings.items[results[0][1]]["name"])+".png",frame_truncated)

                if detection_queue.full():#此种情况一般不应该发生，主进程要做到能够处理每一帧图像
                    print("object delte detect")
                    waste = detection_queue.get_nowait()
                try:
                    detection_queue.put_nowait([index,motionType,results,frame_time])#not a good structure
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
                    maxConfidence = confidence
                    maxItemId = itemId
                
        if maxConfidence !=0:
            results.append((maxConfidence,maxItemId,frame_time))
      
        return results#默认返回空值