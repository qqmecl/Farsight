import settings
import time
import multiprocessing
import time

class UpDownNotMatchError(Exception):
    pass

#detect 
#[(index,confidence,itemId,XAxis,YAxis,cur_time)] one

#根据识别结果结合重力传感器方向判断识别结果
class DetectResult:
    def __init__(self,action,doorSide):
    	self.reset(action,doorSide)

    def put(self,detect):#在放置每一帧的时候顺便进行判断
        # print("weird detect is:",detect)
        for val in detect:
            print("pass base line,loc,itemId,time",val[3],val[2],val[4])
            # self.checkDetect(val)
            #(index,confidence,itemId,location,cur_time) one
            (index,_id,time,XAxis)=(val[0],val[2],val[4],val[3])
            
            if index % 2 == 0:#up position
                new_num = self.upDetect[_id]["num"] + 1
                self.upDetect[_id]["time"] = ((self.upDetect[_id]["time"]*self.upDetect[_id]["num"])+time)/new_num

                self.upDetect[_id]["num"] = new_num

                delta = XAxis - self.upDetect[_id]["X"]

                if XAxis - self.upDetect[_id]["X"] < 0:
                    self.upDetect[_id]["Out"] += abs(delta)
                else:
                    self.upDetect[_id]["In"] += abs(delta)


                self.upDetect[_id]["X"] = XAxis
            else:#down position
                new_num = self.downDetect[_id]["num"] + 1
                self.downDetect[_id]["time"] = ((self.downDetect[_id]["time"]*self.downDetect[_id]["num"])+time)/new_num

                self.downDetect[_id]["num"] = new_num

                delta = XAxis - self.upDetect[_id]["X"]

                if XAxis - self.downDetect[_id]["X"] < 0:
                    self.downDetect[_id]["Out"] += abs(delta)
                else:
                    self.downDetect[_id]["In"] += abs(delta)

                self.downDetect[_id]["X"] = XAxis

    def getDirection(self):
        return self.direction

    def setEnvokeTime(self):
        self.enVokeTime = time.time()

    def setDirection(self,direction):
        self.direction = direction

    def debugTest(self,forcePrint=False):
        if forcePrint:
            for k,val in self.upDetect.items():
                print(k,val)
            
            print("--------------------------------------")

            for k,val in self.downDetect.items():
                print(k,val)


        for k,val in self.upDetect.items():
            if val["num"] >0:
                print("                           ")
                print("Debug upDetect is : ",k,val["num"],val["time"],val["Out"],val["In"])
                print("                           ")


        for k,num in self.downDetect.items():
            if val["num"] >0:
                print("                           ")
                print("Debug downDetect is : ",k,val["num"],val["time"])
                print("                              ")

    def getLabel(self):
        self.logger.info("-----------------------------")
        # print("-----------------------------")
        for k,val in self.upDetect.items():
            if val["num"] >0:
                print("Final upDetect is : ",k,val["num"],val["time"],val["Out"],val["In"])


        for k,num in self.downDetect.items():
            if val["num"] >0:
                print("Final downDetect is : ",k,val["num"],val["time"],val["Out"],val["In"])
        
        # print("["+self.direction,settings.items[self.labelId]["name"]+"]")
        # print("-----------------------------")
        
        info = "["+self.direction,settings.items[self.labelId]["name"]+"]"
        self.logger.info(info)
        self.logger.info("-----------------------------")
        
        return self.labelId

    def reset(self,action,doorSide):
        self.logger = multiprocessing.get_logger()

        if action == 1:
            self.direction = "IN"
        else:
            self.direction = "OUT"
            
        self.judgeComplete = False

        self.doorSide = doorSide

        # self.initScaleVal = initScaleVal
        #结果集，即上侧判断出多少个不同的id及对应次数
        self.upDetect = {}
        self.downDetect = {}
        for k,item in settings.items.items():
            self.upDetect[k]=dict(num=0,time=0,Out=0,In=0,X=0)
            self.downDetect[k]=dict(num=0,time=0,Out=0,In=0,X=0)

        # print(self.upDetect)
        self.upLabel = ""
        self.downLabel = ""
        self.labelId = ""

    def getMax(self,isUp):
        val=self.upDetect if isUp else self.downDetect

        maxId,count ="",0
        for k,v in val.items():
            if v["num"] > count:
                count=v["num"]
                maxId=k

        if count >0:
            direction = "OUT" if val[maxId]["time"] >= self.enVokeTime else "IN"
            # direction = "OUT" if val[maxId]["Out"] >= val[maxId]["In"] else "IN"
            result = (maxId,count,val[maxId]["time"],direction)
            return result
        else:
            return (None,None,None,None)

    def isComplete(self):
        upId,upNum,upTime,upDirection = self.getMax(True)
        downId,downNum,downTime,downDirection= self.getMax(False)

        timeThreshold = 0.2
        if downNum == None:
            if upNum == None:
                return False
            else:
                self.labelId = upId
                if time.time() - upTime >timeThreshold:
                    self.setDirection(upDirection)
                    return True
        else:
            if upNum == None:
                self.labelId = downId
                if time.time() - downTime > timeThreshold:
                    self.setDirection(downDirection)
                    return True
            else:
                if downNum > upNum:
                    self.labelId = downId
                    if time.time() - downTime > timeThreshold:
                        self.setDirection(downDirection)
                        return True
                else:
                    self.labelId = upId
                    if time.time() - upTime > timeThreshold:
                        self.setDirection(upDirection)
                        return True
    	# if self.upLabel is not "":
    	# 	if self.downLabel is "":#相信上面的检测结果
    	# 		self.labelId = self.upLabel
    	# 		return True
    	# 	else:
    	# 		if self.upLabel is self.downLabel:
    	# 			self.labelId = self.upLabel
    	# 			return True
    	# 		else:#
    	# 			raise UpDownNotMatchError("上下摄像头判断结果不一致!!")
    	# else:
	    # 	if self.downLabel is not "":
    	# 		self.labelId = self.downLabel
    	# 		return True

    	# return False


