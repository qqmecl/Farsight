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
from detect.frame_stitch import ImageStitch
from detect.detect_frame import DetectFrame

SELECTED_MODEL = '/data/8kinds/'
# SELECTED_MODEL = '/../Models/mobilenet_ssd_v1_coco/'
# SELECTED_MODEL = '/../Models/mobilenet_ssd_v2_coco/'


CWD_PATH = os.getcwd()

if CWD_PATH != '/':
    MODEL_PATH = os.path.join(CWD_PATH  + SELECTED_MODEL + 'frozen_inference_graph.pb')
    LABEL_PATH = os.path.join(CWD_PATH  + SELECTED_MODEL + 'pascal_label_map.pbtxt')
else:
    MODEL_PATH = os.path.join('/home/votance/Projects/Farsight' + SELECTED_MODEL + 'frozen_inference_graph.pb')
    LABEL_PATH = os.path.join('/home/votance/Projects/Farsight' + SELECTED_MODEL + 'pascal_label_map.pbtxt')

class ObjectDetector:
    def __init__(self,input_q,items,camera_number,detection_queue):
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
        self.timeStamp = time.strftime('%H_%M_%S_',time.localtime(time.time()))
        self.dynamicTracker=[]

        for i in range(camera_number):
            self.dynamicTracker.append(DynamicTrack())

        frameSticher = ImageStitch()

        self.writePath = os.getcwd() + '/photo/'+self.timeStamp+"/"
        os.makedirs(self.writePath)

        # print(writePath)
        # sign = 0
        # self.vertical = None

        allCnt = 0
        while True:
            try:
                frame_truncated,index,frame_time,motionType = input_q.get(timeout=1)
                frame_truncated = self.dynamicTracker[index].check(frame_truncated)#get dynamic tracked location
                results = []
                # sign %= 999
                allCnt += 1

                if frame_truncated is not None:
                    newDetectFrame = DetectFrame(frame_truncated,frame_time,motionType,index)

                    stitched_frame = frameSticher.loadIn(newDetectFrame)

                    if stitched_frame is not None:
                        # cv.imwrite(self.writePath + str(allCnt)+".jpg", stitched_frame)
                        rawResults = self.detect_objects(stitched_frame)

                        realResults = frameSticher.filter(rawResults)
                        # print(realResults)

                        for result in realResults:
                            if detection_queue.full():#此种情况一般不应该发生，主进程要做到能够处理每一帧图像
                                print("object delte detect")
                                waste = detection_queue.get_nowait()
                            # print(result)
                            # detection_queue.put_nowait([index,motionType,result[i],frame_time])
                            detection_queue.put_nowait(result)

                #     # allCnt+=1
                #     # cv.imwrite(str(allCnt)+".png",frame_truncated)
                #     # sign += 1
                #     if setting.stitching_number == 2:
                #         if sign % 2:
                #             self.frame_merge_left = frame_truncated
                #             self.lastMotionType,self.lasFrame_time,self.last_index=motionType,frame_time,index
                #         else:
                #             frame_merge, divide_val, self.vertical = self.image_stitching.stitching([self.frame_merge_left, 1], [frame_truncated. 2])
                #             # cv.imwrite(self.writePath + str(sign) + '--' + str(sum_planA) + '--' + str(sum_planB) + '.jpg', frame_merge)
                #             before = time.time()
                #             results = self.detect_objects(frame_merge, frame_time, divide_val)

                #             # print(results)
                #             # print("consume time: ",time.time()-before)

                #             for i in range(2):
                #                 if detection_queue.full():#此种情况一般不应该发生，主进程要做到能够处理每一帧图像
                #                     print("object delte detect")
                #                     waste = detection_queue.get_nowait()

                #                 try:
                #                     if i:
                #                         # if len(results[i]) >1:
                #                             # print("check two item by the same time: ",results[i])
                #                         detection_queue.put_nowait([index,motionType,results[i],frame_time])#not a good structure
                #                     else:
                #                         detection_queue.put_nowait([self.last_index,self.lastMotionType,results[i],self.lasFrame_time])#not a good structure
                #                 except queue.Full:
                #                     print('[FULL]')
                #                     pass

                #     elif setting.stitching_number == 3:
                #         if sign % 3:
                #             if sign % 2:
                #                 self.one_frame = frame_truncated
                #                 self.one_MotionType,self.one_Frame_time,self.one_index=motionType,frame_time,index
                #             else:
                #                 self.another_frame = frame_truncated
                #                 self.another_MotionType, self.another_Frame_time, self.another_index = motionType, frame_time, index
                #         else:
                #             frame_merge, divide_val, self.vertical = self.image_stitching.stitching(self.one_frame, self.another_frame, frame_truncated)
                #             # pass

                # else:
                #     if detection_queue.full():#此种情况一般不应该发生，主进程要做到能够处理每一帧图像
                #         # print("object delte detect")
                #         waste = detection_queue.get_nowait()
                #     try:
                #         detection_queue.put_nowait([index,motionType,[],frame_time])#not a good structure
                #     except queue.Full:
                #         print('[FULL]')
                #         pass

            except queue.Empty:#不进行识别判断的时候帧会变空
                # print('[EMPTY] input_q is: ')
                pass


    def detect_objects(self,frame):
        self.frameCount += 1

        results=[]
        # results0=[]
        # results1=[]

        original = frame.copy()

        rows = frame.shape[0]
        cols = frame.shape[1]
        frame = cv.resize(frame, (300, 300))
        # cv.imwrite(self.writePath + str(sign) + '.jpg', frame)
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
                itemId = self.classNames[out['detection_classes'][i]]

                # cv.rectangle(original,
                    # (int(bbox[1]*cols),int(bbox[0]*rows)),(int(bbox[3]*cols),int(bbox[2]*rows)),
                        # (0,0,255), 2)

                # if self.vertical:
                #     # cv.imwrite(self.writePath + str(sign) + '.jpg', frame)
                #     box_left_or_up = int(bbox[0] * rows)
                #     box_right_or_down = int(bbox[2] * rows)
                # else:
                #     box_left_or_up = int(bbox[1] * cols)
                #     box_right_or_down = int(bbox[3] * cols)


                up_y = int(bbox[0] * rows)
                down_y = int(bbox[2] * rows)
                left_x = int(bbox[1] * cols)
                right_x = int(bbox[3] * cols)

                results.append((itemId,{"up_y":up_y,"down_y":down_y,"left_x":left_x,"right_x":right_x}))

                # if self.vertical:          # append True is first_frame.....append False is second_box
                #     if up_y <= divide_val and down_y <= divide_val:
                #         results0.append((confidence,itemId,frame_time))

                #     if up_y >= divide_val and down_y >= divide_val:
                #         results1.append((confidence,itemId,frame_time))

                #     # if up_y <= divide_val and down_y >= divide_val:

                # else:
                #     if left_x <= divide_val and right_x <= divide_val:
                #         results0.append((confidence,itemId,frame_time))

                #     if left_x >= divide_val and right_x >= divide_val:
                #         results1.append((confidence,itemId,frame_time))

                    # if left_x <= divide_val and right_x >= divide_val:
                    #     cv.imwrite(self.writePath + 'multi' + str(self.frameCount) + '.jpg', original)

        # cv.imwrite(self.writePath + 'multi' + str(self.frameCount) + '.jpg', original)

        # results.append(results0)
        # results.append(results1)

        # if len(results0) > 0:
            # print(self.frameCount," : ",results0)
            # cv.imwrite(self.writePath + 'box_in_up_and_left' + str(self.frameCount) + '.jpg', original)

        # if len(results1) > 0:
            # print(self.frameCount," : ",results1)
            # cv.imwrite(self.writePath + 'box_in_down_and_right' + str(self.frameCount) + '.jpg', original)

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
                        # self.classNames[_id] = name+'001'
                        self.classNames[_id] = name