import signal
import os
import cv2 as cv
from multiprocessing import Queue, Pool
import queue
from setproctitle import setproctitle
import time

from area import AreaCheck
import settings

CWD_PATH = os.getcwd()
print(CWD_PATH)

if CWD_PATH != '/':
    MODEL_PATH = os.path.join(CWD_PATH + '/data/' + 'frozen_inference_graph.pb')
    DESCRIPTION_PATH = os.path.join(CWD_PATH + '/data/' + 'ssd_mobilenet_v1_coco.pbtxt')
else:
    MODEL_PATH = os.path.join('/home/votance/Projects/Farsight' + CWD_PATH + 'data/' + 'frozen_inference_graph.pb')
    DESCRIPTION_PATH = os.path.join('/home/votance/Projects/Farsight' + CWD_PATH + 'data/' + 'ssd_mobilenet_v1_coco.pbtxt')
# MODEL_PATH = os.path.join(CWD_PATH, 'data', 'frozen_inference_graph_1.pb')
#MODEL_PATH = os.path.join(CWD_PATH, 'data', 'frozen_inference_graph.pb')
#DESCRIPTION_PATH = os.path.join(CWD_PATH, 'data', 'ssd_mobilenet_v1_coco.pbtxt')

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

'''
    #为简化程序结构，只在此ObjectDetector中执行识别单帧的任务
    #此处使用queue实现进程间通信
    实际检测物品的代码，跑在子进程中
'''
#全速无停顿处理每一帧数据
class ObjectDetector:
    def __init__(self,input_q,items,detection_queue):
        setproctitle('[farsight-offline] Detect图像处理进程')
        #忽略 SIGINT，由父进程处理
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        
        self.detectionNet = cv.dnn.readNetFromTensorflow(MODEL_PATH,DESCRIPTION_PATH)

        self.frameCount = 0

        self.items = items

        self.timeStamp = time.strftime('%Y_%m_%d_%H_%M_%S_',time.localtime(time.time()))

        # self.motions = motions

        #Temporary
        self.classNames = {0: 'background',
                  1: '010001', 2: '002004', 3: '006001', 4: '007001', 5: '008001', 6: '009001',
                  7: '001001', 8: '002001', 9: '002002', 10: '003001', 11: '003002',
                  12: '003003'}

        while True:
            try:
                frame,index = input_q.get(timeout=1)
                #self.detect_objects(frame)

                if index > 1:
                    frame = cv.flip(frame,1)
                    # frame = frame[:, -1: 0, :]

                frame_truncated = frame[:, 160: , :]

                

                results = self.detect_objects(frame_truncated,index)
                # print("get frame from index",index)
                # index = index%2
                # motionType = self.motions[index].checkInput(frame)

                #一般情况下，如果主进程没来得及取队列中的数据，则自行清除，确保队列中始终是最新滑动识别窗口
                if detection_queue.full():#此种情况一般不应该发生，主进程要做到能够处理每一帧图像
                    print("object delte detect")
                    waste = detection_queue.get_nowait()

                #if len(results) > 0:
                #print("put into detection")This maybe cause empty or full.
                try:
                    detection_queue.put_nowait([index,frame,results])#not a good structure
                except queue.Full:
                    print('[FULL]')
                    pass
                # output_q.put_nowait()
            except queue.Empty:#不进行识别判断的时候帧会变空
                # print('[EMPTY] input_q is: ')
                pass
        # fps.stop()

    ##当前只考虑单帧的判断
    #TODO:点检测，使用深度学习实现轨迹检测
    def detect_objects(self,frame,index):
        self.frameCount += 1
        inWidth,inHeight = 300,300
        inScaleFactor,meanVal = 0.007843,127.5
        resize = cv.resize(frame,(inWidth,inHeight))

        blob = cv.dnn.blobFromImage(resize, inScaleFactor, (inWidth, inHeight), (meanVal, meanVal, meanVal),
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

            try:
                itemId = self.classNames[class_id]

                if transfer_table[itemId]:
                    itemId = transfer_table[itemId]

                if confidence > 0.8:
                    if AreaCheck(XAxis,YAxis,index).passBaseLine():
                        # print("confidence with id",confidence,itemId)

                        results.append((confidence,itemId,cur_time))
                        
                        if settings.SAVE_DETECT_OUTPUT:
                            import os
                            writePath = os.path.join(os.getcwd(),"../data/output/"+self.timeStamp+"/")

                            if os.path.isdir(writePath) == False:
                                os.mkdir(writePath)

                            cv.rectangle(frame, (xLeftBottom, yLeftBottom), (xRightTop, yRightTop),
                                  (0, 255, 0))
                            # if class_id in classNames:


                            # label = self.items[itemId]["name"] + ": " + str(confidence)
                            # labelSize, baseLine = cv.getTextSize(label, cv.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                            # yLeftBottom = max(yLeftBottom, labelSize[1])
                            # frame = self.addChineseText(frame,label,(xLeftBottom, yLeftBottom+50))


                            # label = itemId + ": " + str(confidence)
                            # labelSize, baseLine = cv.getTextSize(label, cv.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                            # yLeftBottom = max(yLeftBottom, labelSize[1])
                            # frame = self.addChineseText(frame,label,(xLeftBottom, yLeftBottom+50))

                            cv.imwrite(writePath + str(self.frameCount)+self.items[itemId]["name"]+".png",frame)

            except KeyError:
                print("class_id is: ",class_id)
                pass

        return results#默认返回空值

    def addChineseText(self,frame,label,pos):
        # 图像从OpenCV格式转换成PIL格式  
        img_PIL = Image.fromarray(cv.cvtColor(frame, cv.COLOR_BGR2RGB))  
      
        font = ImageFont.truetype('STHeiti_Medium.ttc', 20)

        fillColor = (255,0,0)  
      
        draw = ImageDraw.Draw(img_PIL)  
        
        draw.text(pos, label, font=font, fill=fillColor)  
      
        # 转换回OpenCV格式  
        frame = cv.cvtColor(numpy.asarray(img_PIL),cv.COLOR_RGB2BGR)  

        return frame

