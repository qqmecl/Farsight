import time
import multiprocessing
import settings

class Queue:
    def __init__(self,limit):
        self.items = []
        self.maxLimit = limit

    def isEmpty(self):
        return self.items == []

    def empty(self):
        self.items=[]

    def enqueue(self, item):
        if self.size() == self.maxLimit:
            self.dequeue()
        self.items.insert(0,item)

    def dequeue(self):
        return self.items.pop()

    def size(self):
        return len(self.items)


class UpDownNotMatchError(Exception):
    pass

#single pipeline check about detecting.
class DetectResult:
    def __init__(self):
        self.window = Queue(20)
        self.reset()

    def checkData(self,data):
        for motion,detects in data.items():
            self.window.enqueue(detects)
            # print("current motion is: ",motion)
            if motion == "PUSH":#Action start or Action done.
                if self.detectState == "PULL_CHECKING":
                    self.takeOutCheck()
                    self.reset()
                else:
                    while(not self.window.isEmpty()):
                        self.loadData(self.window.dequeue())

                    detectId = self.getCurrentDetection(True)
                    if detectId is not None:
                        # print("PUT BACK: ",settings.items[detectId])
                        self.detect.append({"direction":"IN","id":detectId})
                    else:#empty push
                        self.window.empty()#清空window

                    self.reset()
                #TODO
            elif motion == "PULL":
                self.detectState = "PULL_CHECKING"
                self.actionTime = time.time()
            elif motion == "None":
                if self.detectState == "PULL_CHECKING":
                    self.takeOutCheck()
                    #TODO
                    #Check action ending state.

    def takeOutCheck(self):
        while(not self.window.isEmpty()):
            self.loadData(self.window.dequeue())
        detectId = self.getCurrentDetection(False)
        if detectId is not None:
            self.detect.append({"direction":"OUT","id":detectId})
            self.reset()

    def getCurrentDetection(self,isLast):
        id,num,time = self.getMaxNum()
        if id is not None:
            if isLast:
                if num > 1: # 原来是3
                    return id
                else:
                    self.reset()
            else:
                now_time = time.time()
                if now_time-self.actionTime < 0.2:
                    if num >= 2: # 原来是4
                        return id
                else:
                    if num > 1: # 原来是3
                        return id
                    else:
                        self.reset()
        return None

    def loadData(self,detects):
        for val in detects:
            #(confidence,itemId,cur_time) one
            (_id,time)=(val[0],val[2],val[3])
            new_num = self.processing[_id]["num"] + 1
            self.processing[_id]["time"] = ((self.processing[_id]["time"]*self.processing[_id]["num"])+time)/new_num
            self.processing[_id]["num"] = new_num
            
    def reset(self):
        self.logger = multiprocessing.get_logger()
        self.detectState = "NORMAL"
        self.processing = {}

        self.detect = []
        for k,item in settings.items.items():
            self.upDetect[k]=dict(num=0,time=0)
            self.downDetect[k]=dict(num=0,time=0)

    def getMaxNum(self):
        maxId,count ="",0
        for k,v in self.processing.items():
            if v["num"] > count:
                count=v["num"]
                maxId=k

        if count >0:
            return (maxId,count,self.processing[maxId]["time"])
        else:
            return (None,None,None)

    def getDetect(self):
        return self.detect

    def resetDetect(self):
        self.detect=[]


