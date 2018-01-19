import signal
import os
import cv2 as cv
from multiprocessing import Queue, Pool
import queue
from setproctitle import setproctitle
import time
import settings
# from object_detection.utils import label_map_util
# from object_detection.utils import visualization_utils as vis_util
# from detection_helper import draw_boxes_and_labels
# from detection_helper import FPS


CWD_PATH = os.getcwd()
#Path to frozen detection graph. This is the actual model that is used for the object detection.
MODEL_PATH = os.path.join(CWD_PATH, 'data', 'frozen_inference_graph.pb')
# List of the strings that is used to add correct label for each box.
DESCRIPTION_PATH = os.path.join(CWD_PATH, 'data', 'ssd_mobilenet_v1_coco.pbtxt')

FILTER_BASE_LINE = [[(260.0,-1.0),(366.0,481.0)],[(250.0,-1.0),(320.0,481.0)],
[(344.0,-1.0),(298.0,481.0)],[(384.0,-1.0),(352.0,481.0)]]

LINE_EQUATION = []
for points in FILTER_BASE_LINE:
    k = (points[1][1]-points[0][1])/(points[1][0]-points[0][0])#下斜率
    b = points[1][1]-k*points[1][0]
    LINE_EQUATION.append([k,b])

'''
    #为简化程序结构，只在此ObjectDetector中执行识别单帧的任务
    #此处使用queue实现进程间通信
    实际检测物品的代码，跑在子进程中
'''
class ObjectDetector:
    def __init__(self, input_q, output_q,detection_queue):
        setproctitle('[farsight] TensorFlow 图像处理进程')
        #忽略 SIGINT，由父进程处理
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        
        self.detectionNet = cv.dnn.readNetFromTensorflow(MODEL_PATH,DESCRIPTION_PATH)

        #Temporary
        self.classNames = {0: 'background',
                  1: '010001', 2: '002004', 3: '006001', 4: '007001', 5: '008001', 6: '009001',
                  7: '001001', 8: '002001', 9: '002002', 10: '003001', 11: '003002',
                  12: '003003'}

        # fps = FPS().start()
        while True:
            # fps.update()
            try:
                frame,index = input_q.get(timeout=1)

                results = self.detect_objects(frame,index)
               
                #一般情况下，如果主进程没来得及取队列中的数据，则自行清除，确保队列中始终是最新滑动识别窗口
                if detection_queue.full():
                    print("object delte detect")
                    waste = detection_queue.get_nowait()

                if len(results) > 0:
                    detection_queue.put_nowait(results)

                # output_q.put_nowait()
            except queue.Empty:#不进行识别判断的时候帧会变空
                # print('[EMPTY] input_q is: ')
                pass

        # fps.stop()

    ##当前只考虑单帧的判断
    #TODO:点检测，使用深度学习实现轨迹检测
    def detect_objects(self,frame,index):
        inWidth,inHeight = 300,300
        inScaleFactor,meanVal = 0.007843,127.5
        blob = cv.dnn.blobFromImage(frame, inScaleFactor, (inWidth, inHeight), (meanVal, meanVal, meanVal),
                                    True)
        self.detectionNet.setInput(blob)
        detections = self.detectionNet.forward()

        rows = frame.shape[0]
        cols = frame.shape[1]
        
        results=[]
        cur_time = time.time()

        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]

            class_id = int(detections[0, 0, i, 1])

            xLeftBottom = int(detections[0, 0, i, 3] * cols)
            yLeftBottom = int(detections[0, 0, i, 4] * rows)
            
            xRightTop = int(detections[0, 0, i, 5] * cols)
            yRightTop = int(detections[0, 0, i, 6] * rows)

            XAxis = (xLeftBottom + xRightTop) / 2
            YAxis = (yLeftBottom + yRightTop) / 2

            # XAxis =  xRightTop
            # YAxis = yRightTop
            try:
                itemId = self.classNames[class_id]
                if confidence > 0.8:
                    location = self.getDetectPos(XAxis,YAxis,index)
                    if self.passBaseLine(index,location):
                        print("confidence is: ",confidence)
                        if index %2 == 0:
                            print("上摄像头: ",settings.items[itemId]["name"],XAxis,cur_time)
                        else:
                            print("下摄像头: ",settings.items[itemId]["name"],XAxis,cur_time)
                        print("----------------")
                        print("                ")
                        results.append((index,confidence,itemId,location,cur_time))

            except KeyError:
                print("class_id is: ",class_id)
                pass
            # print(confidence,itemId,XAxis,YAxis)

        return results#默认返回空值


    def getDetectPos(self,x,y,pos):
        return y- LINE_EQUATION[pos][0]*x

    def passBaseLine(self,pos,location):
        return location < LINE_EQUATION[pos][1]

if __name__ == '__main__':
    input_q = Queue(maxsize=5)
    # output_q = Queue(maxsize=5)
    detection_q = Queue(maxsize=1)

    import multiprocessing
    import logging
    from multiprocessing import Queue, Pool, Process

    # 每个摄像头启动一个进程池
    indexs = [0]
    pool = Pool(1, ObjectDetector, (input_q, detection_q, 1))

    detect = object_detector(input_q, detection_q)

    
