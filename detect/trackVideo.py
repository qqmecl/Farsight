import signal
import os
import cv2 as cv
import numpy as np
from multiprocessing import Queue, Pool
import queue
from setproctitle import setproctitle
import time
import common.settings as settings
import tensorflow as tf

CWD_PATH = os.getcwd()

if CWD_PATH != '/':
    MODEL_PATH = os.path.join(CWD_PATH + '/data/old12_withhand/' + 'frozen_inference_graph.pb')
    LABEL_PATH = os.path.join(CWD_PATH + '/data/old12_withhand/' + 'pascal_label_map.pbtxt')
else:
    MODEL_PATH = os.path.join('/home/votance/Projects/Farsight' + CWD_PATH + 'data/' + 'frozen_inference_graph.pb')
    LABEL_PATH = os.path.join('/home/votance/Projects/Farsight' + CWD_PATH + 'data/' + 'pascal_label_map.pbtxt')


class ObjectDetector:
    def __init__(self,input_q,detection_queue):
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

        ret =True

        stream = cv2.VideoCapture(0)

        while ret:
            ret,frame = stream.read()
            frame = frame[:,160:]
            results = self.detect_objects(frame)
                    


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

    ##当前只考虑单帧的判断
    def detect_objects(self,originalFrame):
        self.frameCount += 1
        results=[]
        rows = originalFrame.shape[0]
        cols = originalFrame.shape[1]
        frame = originalFrame.copy()
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
                cv.rectangle(originalFrame,
                    (int(bbox[1]*cols),int(bbox[0]*rows)),(int(bbox[3]*cols),int(bbox[2]*rows)),
                        (0,0,255))
                itemId = self.classNames[out['detection_classes'][i]]
                results.append((confidence,itemId))
      
      	cv.imshow("frame",originalFrame)

        return results#默认返回空值