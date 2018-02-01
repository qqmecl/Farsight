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

                    detectItem = self.getCurrentDetection(True)
                    if detectItem is not None:
                        print("PUT BACK: ",detectItem)
                        self.detect.append("IN")
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
        detectItem = self.getCurrentDetection(False)
        if detectItem is not None:
            print("TAKE OUT: ",detectItem)
            self.detect.append("OUT")
            self.reset()


    def getCurrentDetection(self,isLast):
        upId,upNum,upTime = self.getMax(True)
        downId,downNum,downTime = self.getMax(False)

         if downNum == None:
            if upNum == None:
                return False
            else:
                return chooseDetect(isLast,upNum,upId)
        else:
            if upNum == None:
                 return chooseDetect(isLast,downNum,downId)
            else:
                if downNum > upNum:
                    return chooseDetect(isLast,downNum,downId)
                else:
                    return chooseDetect(isLast,upNum,upId)
                    

    def chooseDetect(self,isLast,num,id):
        if isLast:
            if num > 1: # 原来是3
                return settings.items[id]["name"]
            else:
                self.reset()
        else:
            now_time = time.time()
            if now_time-self.actionTime < 0.2:
                if num >= 2: # 原来是4
                    return settings.items[id]["name"]
            else:
                if num > 1: # 原来是3
                    return settings.items[id]["name"]
                else:
                    self.reset()
        return None


    def loadData(self,detects):
        for val in detects:
            #(index,confidence,itemId,location,cur_time) one
            (index,_id,time,XAxis)=(val[0],val[2],val[4],val[3])
            
            if index % 2 == 0:#up position
                new_num = self.upDetect[_id]["num"] + 1
                self.upDetect[_id]["time"] = ((self.upDetect[_id]["time"]*self.upDetect[_id]["num"])+time)/new_num
                self.upDetect[_id]["num"] = new_num

            else:#down position
                new_num = self.downDetect[_id]["num"] + 1
                self.downDetect[_id]["time"] = ((self.downDetect[_id]["time"]*self.downDetect[_id]["num"])+time)/new_num
                self.downDetect[_id]["num"] = new_num

    def reset(self):
        self.logger = multiprocessing.get_logger()
        self.detectState = "NORMAL"

        self.upDetect = {}
        self.downDetect = {}

        self.detect = []
        for k,item in settings.items.items():
            self.upDetect[k]=dict(num=0,time=0,Out=0,In=0,X=0)
            self.downDetect[k]=dict(num=0,time=0,Out=0,In=0,X=0)

    def getMax(self,isUp):
        val=self.upDetect if isUp else self.downDetect
        maxId,count ="",0
        for k,v in val.items():
            if v["num"] > count:
                count=v["num"]
                maxId=k
        if count >0:
            result = (maxId,count,val[maxId]["time"])
            return result
        else:
            return (None,None,None)

    def getDetect(self):
        return self.detect

    def resetDetect(self):
        self.detect=[]


