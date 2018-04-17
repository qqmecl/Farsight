import cv2 as cv
import numpy as np
import time
import common.settings as settings

class MotionDetect:
    def __init__(self):
        self.hand_last = 0
        self.hand_present = 0
        self.motion_dict = {-1:'PUSH',0:'None',1:'PULL'}
        self.refLine = None

    def checkInput(self,frame,frame_time):
        if self.refLine is None:
            self.refLine = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            self.hand_last = -6     # -6 = 手在外面， 6 = 手在里面, 其余为中间状态
            self.hand_present = -6
            return "None"

        curLine = frame# 当前帧的参考线

        isCover = self.CoverCheck(curLine) # 判断是否参考线是否被手覆盖

        if isCover:
            self.hand_present += 2 #被覆盖的话就将加状态
        else:
            self.hand_present -= 3 #不被覆盖就减状态

        if abs(self.hand_present) > 6:
            self.hand_present = self.hand_present / abs(self.hand_present) * 6 # 状态只在[-6,6]区间内
        
        # 状态从-6变到6 或 从6变到-6
        if (self.hand_present != self.hand_last) and (abs(self.hand_present) == 6): 
            motion = self.hand_last - self.hand_present
            if motion!= 0:
                motion = motion / abs(motion)
                self.hand_last = self.hand_present
                return (self.motion_dict[motion],isCover)
        
        return ("None",isCover)

    def reset(self):
        self.refLine = None

    def CoverCheck(self, curLine):
        present_gray = cv.cvtColor(curLine, cv.COLOR_BGR2GRAY)

        SIMI = []
        r = curLine.shape[0]/10.0
        c = curLine.shape[1]
        for k in range(10):
            s = int(k * r)
            e = int((k+1) * r)
            sigX = np.var(self.refLine[s:e,:]) * (r*c) / (r*c-1)
            sigY = np.var(present_gray[s:e,:]) * (r*c) / (r*c-1)
            miuX = np.average(self.refLine[s:e,:])
            miuY = np.average(present_gray[s:e,:])
            sigXY = np.sum(np.multiply(self.refLine[s:e,:]-miuX, present_gray[s:e,:]-miuY))
            sigXY /= (r*c-1)
            C3 = (0.03*255.0)**2 / 2.0
            SIMI.append((sigXY+C3) / ((sigX*sigY)**0.5+C3))
       
        
        if min(SIMI) < 0.5: # 该阈值需要深入测试
            # print ("isCover",SIMI)
            return True
        else:
            return False