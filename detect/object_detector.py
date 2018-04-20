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

        self.writePath = os.getcwd() + '/photo/'
        # print(writePath)
        sign = 0
        self.vertical = None

        while True:
            try:
                frame_truncated,index,frame_time,motionType = input_q.get(timeout=1)
                frame_truncated = self.dynamicTracker[index].check(frame_truncated)#get dynamic tracked location
                results = []
                sign %= 999

                if frame_truncated is not None:
                    sign += 1
                    if sign % 2:
                        self.frame_merge_left = frame_truncated
                    else:
                        left_x = self.frame_merge_left.shape[1]
                        right_x = frame_truncated.shape[1]
                        left_y = self.frame_merge_left.shape[0]
                        right_y = frame_truncated.shape[0]
                        if left_x >= right_x:
                            if left_x >= (left_y + right_y):
                                sum_planA = (left_x - right_x) * right_y + left_x * (left_x - left_y - right_y) #up concatenate down
                                photo_sign_A = 1
                            else:
                                sum_planA = (left_x - right_x) * right_y + (left_y + right_y) * (left_y + right_y - left_x) #up concatenate down
                                photo_sign_A = 2
                        else:
                            if right_x >= (left_y + right_y):
                                sum_planA = (right_x - left_x) * left_y + right_x * (right_x - left_y - right_y) #up concatenate down
                                photo_sign_A = 3
                            else:
                                sum_planA = (right_x - left_x) * left_y + (left_y + right_y) * (left_y + right_y - right_x) #up concatenate down
                                photo_sign_A = 4
                        
                        if left_y >= right_y:
                            if left_y >= (left_x + right_x):
                                sum_planB = (left_y - right_y) * right_x + left_y * (left_y - left_x - right_x) #left concatenate right
                                photo_sign_B = 5
                            else:
                                sum_planB = (left_y - right_y) * right_x + (left_x + right_x) * (left_x + right_x - left_y) #left concatenate right
                                photo_sign_B = 6
                        else:
                            if right_y >= (left_x + right_x):
                                sum_planB = (right_y - left_y) * left_x + right_y * (right_y - left_x - right_x) #left concatenate right
                                photo_sign_B = 7
                            else:
                                sum_planB = (right_y - left_y) * left_x + (left_x + right_x) * (left_x + right_x - right_y) #left concatenate right
                                photo_sign_B = 8

                        
                        if sum_planA <= sum_planB:
                            self.vertical = True  
                            if photo_sign_A == 1:
                                fill1 = np.zeros((right_y, left_x - right_x, 3), np.uint8)
                                frame_temp_temp = np.concatenate((frame_truncated, fill1), axis = 1)
                                fill2 = np.zeros((left_x - left_y - right_y, left_x, 3), np.uint8)
                                frame_temp = np.concatenate((self.frame_merge_left, frame_temp_temp), axis = 0)
                                frame_merge = np.concatenate((frame_temp, fill2), axis = 0)
                                left_box_pixel = left_y
                            
                            if photo_sign_A == 2:
                                fill1 = np.zeros((right_y, left_x - right_x, 3), np.uint8)
                                frame_temp_temp = np.concatenate((frame_truncated, fill1), axis = 1)
                                fill2 = np.zeros((left_y + right_y, left_y + right_y - left_x, 3), np.uint8)
                                frame_temp = np.concatenate((self.frame_merge_left, frame_temp_temp), axis = 0)
                                frame_merge = np.concatenate((frame_temp, fill2), axis = 1)
                                left_box_pixel = left_y
                            
                            if photo_sign_A == 3:
                                fill1 = np.zeros((left_y, right_x - left_x, 3), np.uint8)
                                frame_temp_temp = np.concatenate((self.frame_merge_left, fill1), axis = 1)
                                fill2 = np.zeros((right_x - left_y - right_y, right_x, 3), np.uint8)
                                frame_temp = np.concatenate((frame_truncated, frame_temp_temp), axis = 0)
                                frame_merge = np.concatenate((frame_temp, fill2), axis = 0)
                                left_box_pixel = right_y

                            if photo_sign_A == 4:
                                fill1 = np.zeros((left_y, right_x - left_x, 3), np.uint8)
                                frame_temp_temp = np.concatenate((self.frame_merge_left, fill1), axis = 1)
                                fill2 = np.zeros((left_y + right_y, left_y + right_y - right_x, 3), np.uint8)
                                frame_temp = np.concatenate((frame_truncated, frame_temp_temp), axis = 0)
                                frame_merge = np.concatenate((frame_temp, fill2), axis = 1)
                                left_box_pixel = right_y
                        else:
                            self.vertical = False
                            if photo_sign_B == 5:
                                fill1 = np.zeros((left_y - right_y, right_x, 3), np.uint8)
                                frame_temp_temp = np.concatenate((frame_truncated, fill1), axis = 0)
                                fill2 = np.zeros((left_y, left_y - left_x - right_x, 3), np.uint8)
                                frame_temp = np.concatenate((self.frame_merge_left, frame_temp_temp), axis = 1)
                                frame_merge = np.concatenate((frame_temp, fill2), axis = 1)
                                left_box_pixel = left_x

                            if photo_sign_B == 6:
                                fill1 = np.zeros((left_y - right_y, right_x, 3), np.uint8)
                                frame_temp_temp = np.concatenate((frame_truncated, fill1), axis = 0)
                                fill2 = np.zeros((left_x + right_x - left_y, left_x + right_x, 3), np.uint8)
                                frame_temp = np.concatenate((self.frame_merge_left, frame_temp_temp), axis = 1)
                                frame_merge = np.concatenate((frame_temp, fill2), axis = 0)
                                left_box_pixel = left_x

                            if photo_sign_B == 7:
                                fill1 = np.zeros((right_y - left_y, left_x, 3), np.uint8)
                                frame_temp_temp = np.concatenate((self.frame_merge_left, fill1), axis = 0)
                                fill2 = np.zeros((right_y, right_y - left_x - right_x, 3), np.uint8)
                                frame_temp = np.concatenate((frame_truncated, frame_temp_temp), axis = 1)
                                frame_merge = np.concatenate((frame_temp, fill2), axis = 1)
                                left_box_pixel = right_x

                            if photo_sign_B == 8:
                                fill1 = np.zeros((right_y - left_y, left_x, 3), np.uint8)
                                frame_temp_temp = np.concatenate((self.frame_merge_left, fill1), axis = 0)
                                fill2 = np.zeros((left_x + right_x - right_y, left_x + right_x, 3), np.uint8)
                                frame_temp = np.concatenate((frame_truncated, frame_temp_temp), axis = 1)
                                frame_merge = np.concatenate((frame_temp, fill2), axis = 0)
                                left_box_pixel = right_x




                        #     sum_planB = abs(left_y - right_y) * left_x if left_y < right_y else abs(left_y - right_y) * right_x #left concatenate right
                        # else:
                        #     sum_planA = abs(left_x - right_x) * left_y + right_x * abs(right_x - left_y - right_y) if left_x < right_x else abs(left_x - right_x) * right_y + left_x * abs(left_x - left_y - right_y) #up concatenate down
                        # if sum_planA > sum_planB: #plan b is winner
                        #     self.vertical = False
                        #     diff = right_y - left_y
                        #     if diff > 0:
                        #         fill = np.zeros((diff, left_x, 3), np.uint8)
                        #         self.frame_merge_left = np.concatenate((self.frame_merge_left, fill), axis = 0)
                        #         left_box_pixel = left_x
                        #         frame_merge = np.concatenate((self.frame_merge_left, frame_truncated), axis = 1)
                        #     elif diff < 0:
                        #         fill = np.zeros((abs(diff), right_x, 3), np.uint8)
                        #         frame_truncated = np.concatenate((frame_truncated, fill), axis = 0)
                        #         left_box_pixel = left_x
                        #         frame_merge = np.concatenate((self.frame_merge_left, frame_truncated), axis = 1)
                        #     else:
                        #         frame_merge = np.concatenate((self.frame_merge_left, frame_truncated), axis = 1)
                        #         left_box_pixel = left_x

                        # elif sum_planA < sum_planB: #plan a is winner
                        #     self.vertical = True
                        #     diff = right_x - left_x
                        #     if diff > 0:
                        #         fill = np.zeros((left_y, diff, 3), np.uint8)
                        #         self.frame_merge_left = np.concatenate((self.frame_merge_left, fill), axis = 1)
                        #         left_box_pixel = left_y
                        #         frame_merge = np.concatenate((self.frame_merge_left, frame_truncated), axis = 0)
                        #     elif diff < 0:
                        #         fill = np.zeros((right_y, abs(diff), 3), np.uint8)
                        #         frame_truncated = np.concatenate((frame_truncated, fill), axis = 1)
                        #         left_box_pixel = left_y
                        #         frame_merge = np.concatenate((self.frame_merge_left, frame_truncated), axis = 0)
                        #     else:
                        #         frame_merge = np.concatenate((self.frame_merge_left, frame_truncated), axis = 0)
                        #         left_box_pixel = left_y

                        # else:
                        #     self.vertical = False
                        #     frame_merge = np.concatenate((self.frame_merge_left, frame_truncated), axis = 1)
                        #     left_box_pixel = left_x


                        # cv.imwrite(writePath + str(sign) + '.jpg', frame_merge)
                        enlarge_num = frame_merge.shape[1] / 300
                        results = self.detect_objects(frame_merge,frame_time, enlarge_num, left_box_pixel, sign)


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

                        # enlarge_num = frame_merge.shape[1] / 300
                        # results = self.detect_objects(frame_merge,frame_time, enlarge_num, left_box_pixel)
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
    def detect_objects(self,originalFrame,frame_time, enlarge_num, left_box_pixel, sign):
        self.frameCount += 1
        results=[]
        rows = originalFrame.shape[0]
        cols = originalFrame.shape[1]

        frame = originalFrame.copy()
        originalFrame = cv.resize(originalFrame, (300, 300))
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
                #         (0,0,255), 2)
                if self.vertical:
                    box_left_or_up = int(bbox[0] * rows)
                    box_right_or_down = int(bbox[2] * rows)
                else:
                    box_left_or_up = int(bbox[1] * cols)
                    box_right_or_down = int(bbox[3] * cols)
                # frame_left_cols = self.frame_merge_left.shape[1]
                # left_box_pixel = int(left_box_pixel / enlarge_num)
                # print(box_left_or_up)
                # print(box_right_or_down)
                # print(left_box_pixel)
                # if box_left_or_up < left_box_pixel and box_left_or_up < frame_left_cols + 1 and box_right_or_down > frame_left_cols:
                    # continue
                if box_left_or_up < left_box_pixel and box_right_or_down > left_box_pixel:
                    # print(box_left_or_up)
                    # print(box_right_or_down)
                    # print(left_box_pixel)
                    # cv.imwrite(self.writePath + str(sign) + '.jpg', originalFrame)
                    continue
                itemId = self.classNames[out['detection_classes'][i]]
                results.append((confidence,itemId,frame_time))
      
        # if len(results) > 2:
            # cv.imwrite(self.writePath + str(sign) + '.jpg', frame)
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