import time
import multiprocessing
import common.settings as settings
from common.queue import Queue

class DetectResult:
    def __init__(self):
        self.window = Queue(12)
        self.logger = multiprocessing.get_logger()
        self.reset()
        self.resetDetect()
        self.curMarkTime = time.time()
        
    def getMotionTime(self,_type):
        return self.motionTime[_type]

    def checkData(self,index,data,frame_time):
        for motion,detects in data.items():
            
            motion = motion[0]

            if motion is not "None":
                self.motionTime[motion]=frame_time
                print('fgdfg')

            # for val in detects:
            #     (_id,_time)=(val[1],val[2])#(confidence,itemId,cur_time) one
            #     settings.logger.info('{0} camera shot {1} by time {2}'.format(index,settings.items[_id]["name"],_time))
            
            self.window.enqueue(detects)


            # if motion is not "None":
            #     print("current motion is: ",motion)
            if motion == "PUSH":#Action start or Action done.
                # print("Got push back action!!!")
                if self.detectState == "PULL_CHECKING":
                    # print("From push state detect pull checking last!!!!!")
                    self.takeOutCheck()
                    self.reset()
                else:
                    # id,num,_time = self.getMaxNum()
                    # print("put back check: ",id,num,_time)
                    while(not self.window.isEmpty()):
                        # pop = self.window.dequeue()
                        # print(pop)
                        self.loadData(self.window.dequeue())

                    # id,num,_time = self.getMaxNum()
                    # print("put back after check: ",id,num,_time)
                    detectId,num,t_ime,fetch_num = self.getCurrentDetection(True)
                    if detectId is not None:
                        self.detect.append({"direction":"IN","id":detectId,"num":num,"time":t_ime,"fetch_num":fetch_num})
                    else:#empty push
                        self.window.empty()#清空window

                    self.reset()

                self.lastMotion = motion
                #TODO
            elif motion == "PULL":
                # print("Last motion is: ",self.lastMotion)
                if self.lastMotion == "PUSH":
                    self.detectState = "PULL_CHECKING"
                    self.actionTime = time.time()

                    limit=3#limit 
                    while(not self.window.isEmpty() and limit >0):
                        pop = self.window.dequeue()
                        # cv.imwrite()
                        self.loadData(pop)
                        limit-=1
                    # print("pull checking start time : ",self.actionTime)

                self.lastMotion = motion
            elif motion == "None":
                # print("self.detectState is ",self.detectState)
                if self.detectState == "PULL_CHECKING":
                    #filter time less situation.

                    self.takeOutCheck(timeCheck=True)



    def takeOutCheck(self,timeCheck=False):
        while(not self.window.isEmpty()):
            pop = self.window.dequeue()
            isAdd = True
            for val in pop:
                _time=val[2]
                if timeCheck and self.curMarkTime > _time:
                    isAdd = False
                break
            if isAdd:
                self.loadData(pop)
            # else:
                # print("not load data")

        detectId,num,t_ime,fetch_num = self.getCurrentDetection(False)
        if detectId is not None:
            # print("TAKE OUT: ",settings.items[detectId])
            result = {"direction":"OUT","id":detectId,"num":num,"time":t_ime,"fetch_num":fetch_num}
            # self.callback(self.closet,result)
            self.detect.append(result)
            self.reset()

    def getCurrentDetection(self,isLast):#these parameters would significantly improve the performance of detect rate!
        id,num,_time,fetch_num = self.getMaxNum()

        back_threshold,out_inTimethreshold,out_timeout_threshold = 1,2,1

        if id is not None:
            if isLast:#in item check
                if num > back_threshold: # 原来是3
                    return id,num,_time,fetch_num
                else:
                    self.reset()
            else:#out item check
                now_time = time.time()

                if now_time-self.actionTime < 1:
                    if num > out_inTimethreshold:
                        return id,num,_time,fetch_num
                else:
                    if num > out_timeout_threshold:
                        return id,num,_time,fetch_num
                    else:
                        self.reset()

                # if now_time-self.actionTime > 0.8:
                #     if num > 1:
                #         return id,num,_time,fetch_num
                #     else:
                #         self.reset()


        return None,None,None,None

    def loadData(self,detects):
        count={}
        for val in detects:
            # _id = val[1] #???? repetition
            count[_id]=0

        for val in detects:
            #(confidence,itemId,cur_time) one
            (_id,time)=(val[1],val[2])
            count[_id]+=1

            # print("check ",settings.items[_id]["name"],"by time ",time)
            new_num = self.processing[_id]["num"] + 1
            self.processing[_id]["time"] = ((self.processing[_id]["time"]*self.processing[_id]["num"])+time)/new_num
            self.processing[_id]["num"] = new_num
            self.processing[_id]["fetch_num"] = max(self.processing[_id]["fetch_num"],count[_id])

            
    def reset(self):
        self.detectState = "NORMAL"
        self.actionTime = time.time()
        self.processing = {}
        self.lastMotion = None
        for k,item in settings.items.items():
            self.processing[k]=dict(num=0,time=0,fetch_num=0)

    def setActionTime(self):
        self.curMarkTime = time.time()

    def getMaxNum(self):
        maxId,count ="",0
        for k,v in self.processing.items():
            if v["num"] > count:
                count=v["num"]
                maxId=k

        if count >0:
            return (maxId,count,self.processing[maxId]["time"],self.processing[maxId]["fetch_num"])
        else:
            return (None,None,None,None)

    def getDetect(self):
        return self.detect

    def resetDetect(self):
        self.detect=[]
        self.motionTime={"PULL":0,"PUSH":0}




