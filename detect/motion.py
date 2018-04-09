import cv2 as cv
import numpy as np
from detect.area import AreaCheck
import time
from common import settings

class MotionDetect:
    def __init__(self,cameraId):
        # print("Init motion detect")
        self.cameraId = cameraId
        self.hand_last = 0
        self.hand_present = 0
        self.last_frame = None
        self.motion_dict = {-1:'PUSH',0:'None',1:'PULL'}

        self.cnt_out =0
        self.cnt_in =0
        self.divide_x = 300

        import time
        self.timeStamp = time.strftime('%Y_%m_%d_%H_%M_%S_',time.localtime(time.time()))

        self.motionTime={"PULL":0,"PUSH":0}
        # Reference Line Settings
        self.refLine = None
        self.sign = 0
        # self.rL_cenX = 310
        # self.rL_half_width = 10


    def checkInput(self,frame,frame_time):
        if self.sign != 40:
            self.sign += 1
            return "sign full"

        if self.refLine is None:
            # 第一帧的时候切割下原始参考线
            # self.refLine = frame[:, self.rL_cenX-self.rL_half_width : self.rL_cenX+self.rL_half_width]
            self.refLine = frame
            self.hand_last = -6     # -6 = 手在外面， 6 = 手在里面, 其余为中间状态
            self.hand_present = -6
            # print ('Initiate Reference Line')
            # import time
            # cv.imwrite(str(time.time())+'.png', frame)
            # cv.imwrite('./Output/FirstFrame/Frame'+self.timeStamp+'.png', frame)
            # cv.imwrite('./Output/FirstFrame/refLine'+self.timeStamp+'.png', frame)
            # cv.imwrite('./Output/FirstFrame/refLine'+self.timeStamp+'.png', frame)
            return "None"
            
        # cv.imshow('frame', frame)
        # cv.waitKey(1)


        curLine = frame # 当前帧的参考线
        # curLine = frame[:, self.rL_cenX-self.rL_half_width : self.rL_cenX+self.rL_half_width] # 当前帧的参考线

        # isCover = self.CoverCheck_old(curLine, self.refLine) # 判断是否参考线是否被手覆盖
        isCover = self.CoverCheck(curLine, self.refLine) # 判断是否参考线是否被手覆盖
        # print (isCover)
        if isCover == 1:

            if settings.SAVE_DEBUG_OUTPUT:
                tiem = time.time()
                cv.imwrite("Output/"+str(tiem)+"ref.png",self.refLine)
                cv.imwrite("Output/"+str(tiem)+"cur.png",curLine)
            # cv.imshow('curLine', curLine)
            # cv.waitKey(1)
            self.hand_present += 2 # 被覆盖的话就将加状态
        else:
            self.hand_present -= 3 # 不被覆盖就减状态

        if abs(self.hand_present) > 6:
            self.hand_present = self.hand_present / abs(self.hand_present) * 6 # 状态只在[-6,6]区间内
        
        # 状态从-6变到6 或 从6变到-6
        if (self.hand_present != self.hand_last) and (abs(self.hand_present) == 6): 
            motion = self.hand_last - self.hand_present
            if motion!= 0:
                motion = motion / abs(motion) # 将motion归一为 1 或 -1
                self.hand_last = self.hand_present # 只在此处存储hand_last，保证它为 -6 或 6
                # settings.logger.warning('Check {} motion : {} by {}'.format(self.cameraId,self.motion_dict[motion],frame_time))# -1--push, 1--pull
                # import os
                # writePath = os.path.join(os.getcwd(),"../data/output/"+self.timeStamp+"/")
                # if os.path.isdir(writePath) == False:
                #     os.mkdir(writePath)
                # cv.putText(frame, self.motion_dict[motion], (320,240), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
                # cv.imwrite(writePath + str(self.frameCount)+".png",frame)
                motionType = self.motion_dict[motion]
                self.motionTime[motionType]=frame_time
                # settings.logger.info('motion detect ttttt {}'.format(motionType))
                return motionType
                #img show with detected motion blob
                # cv.imwrite(outputpath+str(frameCount)+".png",frame)
            #self.hand_last = self.hand_present
        
        return False

    def reset(self):
        self.refLine = None
        # print("reset Done")


    def getMotionTime(self,_type):
        return self.motionTime[_type]

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
    
if __name__ == "__main__":
    motion = MotionDetect()
    #This would check the success rate of Pull Push judge

    # src_file_name = "../../data/input/left_up2018_01_24_12_13_140.avi"
    src_file_name = "./data/input/left_up2018_01_25_14_52_420.avi"
    # outputpath = "../../data/output/"
    cap = cv.VideoCapture(src_file_name)

    ret, frame = cap.read()
    count = 0
    import time
    t1 = time.time()
    while ret:
        count += 1
        # print("frame is: ",frame)

        if count > 40:
            motion.checkInput(frame)
        ret, frame = cap.read()
    t2 = time.time()
    print ('time used: %.5fs' %(t2-t1))
    cap.release()