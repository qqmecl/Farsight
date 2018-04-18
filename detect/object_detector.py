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
import tensorflow as tf

CWD_PATH = os.getcwd()

if CWD_PATH != '/':
    MODEL_PATH = os.path.join(CWD_PATH + '/data/old12_withhand/' + 'frozen_inference_graph.pb')
    LABEL_PATH = os.path.join(CWD_PATH + '/data/old12_withhand/' + 'pascal_label_map.pbtxt')
else:
    MODEL_PATH = os.path.join('/home/votance/Projects/Farsight' + CWD_PATH + 'data/' + 'frozen_inference_graph.pb')
    LABEL_PATH = os.path.join('/home/votance/Projects/Farsight' + CWD_PATH + 'data/' + 'pascal_label_map.pbtxt')

class ObjectDetector:
    def __init__(self,input_q,items,detection_queue):
        setproctitle('[farsight] model_inferencing_processor')

        signal.signal(signal.SIGINT, signal.SIG_IGN)

        self.classNames = {}

        self.readPbCfg(LABEL_PATH)

        with tf.gfile.GFile(MODEL_PATH, 'rb') as f:
          self.detection_graph = tf.GraphDef()
          self.detection_graph.ParseFromString(f.read())

        with tf.Session() as tf_sess:
          self.tf_sess = tf_sess
          self.tf_sess.graph.as_default()
          tf.import_graph_def(self.detection_graph, name='')
       
        self.image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')
        ops = tf.get_default_graph().get_operations()
  
        all_tensor_names = {output.name for op in ops for output in op.outputs}
        self.tensor_dict = {}
        keyLists = ['num_detections', 'detection_boxes', 'detection_scores',
          'detection_classes', 'detection_masks']

        for key in keyLists:
            tensor_name = key + ':0'
            if tensor_name in all_tensor_names:
                self.tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(tensor_name)


        self.frameCount = 0
        self.confidenceThreshold=0.9
        self.items = items
        self.timeStamp = time.strftime('%Y_%m_%d_%H_%M_%S_',time.localtime(time.time()))
        self.dynamicTracker=[]

        for i in range(2):
            self.dynamicTracker.append(DynamicTrack())

        sign = 0

        while True:
            try:
                frame_truncated,index,frame_time,motionType = input_q.get(timeout=1)
                frame_truncated = self.dynamicTracker[index].check(frame_truncated)#get dynamic tracked location
                results = []
                sign %= 99

                if frame_truncated is not None:
                    sign += 1
                    if sign % 2:
                        self.frame_merge_left = frame_truncated
                    else:
                        x = frame_truncated.shape[0] - self.frame_merge_left.shape[0]
                        if x == 0:
                            frame_merge = np.concatenate((self.frame_merge_left, frame_truncated), axis = 1)
                            left_box_pixel = self.frame_merge_left.shape[1]
                        else:
                            y = abs(x)
                            if y - x:
                                fill = np.zeros((y, frame_truncated.shape[1], 3), np.uint8)
                                frame_truncated = np.concatenate((frame_truncated, fill), axis = 0)
                                left_box_pixel = self.frame_merge_left.shape[1]
                                frame_merge = np.concatenate((self.frame_merge_left, frame_truncated), axis = 1)
                            else:
                                fill = np.zeros((y, self.frame_merge_left.shape[1], 3), np.uint8)
                                self.frame_merge_left = np.concatenate((self.frame_merge_left, fill), axis = 0)
                                left_box_pixel = self.frame_merge_left.shape[1]
                                frame_merge = np.concatenate((self.frame_merge_left, frame_truncated), axis = 1)

                        # cv.imwrite(writePath + str(x) + '.jpg', frame_merge)


                # if frame_truncated is not None:
                #     row = frame_truncated.shape[0]
                #     col = frame_truncated.shape[1]
                #     if row>col:
                #         fill = np.zeros((row,row-col,3),np.uint8)
                #         frame_truncated = np.concatenate((frame_truncated,fill),1)
                #     else:
                #         fill = np.zeros((col-row,col,3),np.uint8)
                #         frame_truncated = np.concatenate((frame_truncated,fill),0)

                #     x += 1
                #     if x % 2:
                #         self.frame_merge_left = frame_truncated
                #     else:
                #         y = frame_truncated.shape[0] - self.frame_merge_left.shape[0]
                #         if y > 0:
                #             z = y % 2
                #             y = y // 2
                #             frame_x = cv.copyMakeBorder(self.frame_merge_left, y, y + z, y, y, cv.BORDER_CONSTANT, value=[0,0,0])
                #             frame_merge = np.concatenate((frame_x, frame_truncated), axis = 1)
                #         elif y == 0:
                #             frame_merge = np.concatenate((self.frame_merge_left, frame_truncated), axis = 1)
                #         elif y < 0:
                #             z = abs(y) % 2
                #             y = abs(y) // 2
                #             frame_x = cv.copyMakeBorder(frame_truncated, y, y + z, y, y, cv.BORDER_CONSTANT, value=[0,0,0])
                #             frame_merge = np.concatenate((self.frame_merge_left, frame_x), axis = 1)
                        # cv.imwrite(writePath + str(x) + '.jpg', frame_merge)
                        # cv.imshow('frame', frame_merge)

                        enlarge_num = frame_merge.shape[1] / 300
                        results = self.detect_objects(frame_merge,frame_time, enlarge_num, left_box_pixel)
                    # if len(results) > 0:
                        # print(results)
                        # cv.imwrite(str(index)+"/frame"+str(self.frameCount)+"_"+str(settings.items[results[0][1]]["name"])+".png",frame_truncated)

                    # if results:
                        # settings.logger.info('{}'.format(results[0][1]))
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
    def detect_objects(self,frame,frame_time, enlarge_num, left_box_pixel):
        self.frameCount += 1
        results=[]
        rows = frame.shape[0]
        cols = frame.shape[1]

        # frame = originalFrame.copy()
        frame = cv.resize(frame, (300, 300))

        frame = frame[:, :, [2, 1, 0]]

        out = self.tf_sess.run(self.tensor_dict,feed_dict={self.image_tensor: frame.reshape(1, frame.shape[0], frame.shape[1], 3)})
        out['num_detections'] = int(out['num_detections'][0])
        out['detection_classes'] = out['detection_classes'][0].astype(np.uint8)
        out['detection_boxes'] = out['detection_boxes'][0]
        out['detection_scores'] = out['detection_scores'][0]

        for i in range(out['num_detections']):
            confidence = out['detection_scores'][i]
            if confidence > self.confidenceThreshold:
                bbox = out['detection_boxes'][i]
                # cv.imwrite(self.writePath + time.strftime('%Y_%m_%d_%H_%M_%S_',time.localtime(time.time())) + '.jpg', bbox)
                # cv.rectangle(originalFrame,
                #     (int(bbox[1]*cols),int(bbox[0]*rows)),(int(bbox[3]*cols),int(bbox[2]*rows)),
                #         (0,0,255))
                box_left_cols = int(bbox[1] + cols)
                box_right_cols = int(bbox[3] + cols)
                frame_left_cols = self.frame_merge_left.shape[1]
                left_box_pixel = int(left_box_pixel / enlarge_num)
                if box_left_cols > left_box_pixel and box_left_cols < frame_left_cols + 1 and box_right_cols > frame_left_cols:
                    continue
                itemId = self.classNames[out['detection_classes'][i]]
                results.append((confidence,itemId,frame_time))
      
        return results#默认返回空值


    def readPbCfg(self,path):
        _id = None
        with open(path,'r') as f:
            for line in f.readlines():   
                line = line.strip()
                splits = line.split(":")
                if len(splits) == 2:
                    for s in splits:
                        s = s.strip()
                    if splits[0] == "id":
                        _id=int(splits[1])
                    elif splits[0] == "name":
                        name = splits[1].strip()
                        name = name.strip("\'")
                        self.classNames[_id] = name+'001'
                        # self.classNames[_id] = name
        f.close()


    