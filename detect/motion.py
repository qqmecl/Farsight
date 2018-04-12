import cv2 as cv
import numpy as np
import time
import common.settings as settings

class MotionDetect:
    def __init__(self):
        self.hand_last = 0
        self.hand_present = 0
        self.motion_dict = {-1:'PUSH',0:'None',1:'PULL'}
        import time
        self.timeStamp = time.strftime('%Y_%m_%d_%H_%M_%S_',time.localtime(time.time()))

        self.refLine = None

    def checkInput(self,frame,frame_time):
        if self.refLine is None:
            # 第一帧的时候切割下原始参考线
            # self.refLine = frame[:, self.rL_cenX-self.rL_half_width : self.rL_cenX+self.rL_half_width]
            self.refLine = frame
            self.hand_last = -6     # -6 = 手在外面， 6 = 手在里面, 其余为中间状态
            self.hand_present = -6
            return "None"

        curLine = frame# 当前帧的参考线

        isCover = self.CoverCheck(curLine, self.refLine) # 判断是否参考线是否被手覆盖
        if isCover == 1:
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

                # print("check motion: ",self.motion_dict[motion])
                return self.motion_dict[motion]
        
        return "None"

    def reset(self):
        self.refLine = None

    def CoverCheck(self, curLine, refLine):

        present_gray = cv.cvtColor(curLine, cv.COLOR_BGR2GRAY)
        # present_gray = cv.GaussianBlur(present_gray, (21, 21), 0) # 还需要检查是否需要高斯模糊
        ref_gray = cv.cvtColor(refLine, cv.COLOR_BGR2GRAY)
  

        SIMI = []
        r = curLine.shape[0]/10.0
        c = curLine.shape[1]
        for k in range(10):
            s = int(k * r)
            e = int((k+1) * r)
            sigX = np.var(ref_gray[s:e,:]) * (r*c) / (r*c-1)
            sigY = np.var(present_gray[s:e,:]) * (r*c) / (r*c-1)
            miuX = np.average(ref_gray[s:e,:])
            miuY = np.average(present_gray[s:e,:])
            sigXY = np.sum(np.multiply(ref_gray[s:e,:]-miuX, present_gray[s:e,:]-miuY))
            sigXY /= (r*c-1)
            C3 = (0.03*255.0)**2 / 2.0
            SIMI.append((sigXY+C3) / ((sigX*sigY)**0.5+C3))
       
        
        if min(SIMI) < 0.5: # 该阈值需要深入测试
            # print ("isCover",SIMI)
            return 1
        else:
            return 0