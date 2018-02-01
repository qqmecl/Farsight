import cv2 as cv
import numpy as np
from area import AreaCheck

class MotionDetect:
    def __init__(self):
        self.hand_last = 0
        self.hand_present = 0
        self.curMotion = 0
        self.default_width = 640
        self.last_frame = None
        self.motion_dict = {-1:'PUSH',0:'None',1:'PULL'}

        self.fgbg = cv.createBackgroundSubtractorMOG2()
        self.fgbg_kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE,(3,3))

        self.cnt_out =0
        self.cnt_in =0
        self.divide_x = 300
        self.frameCount = 0

        import time
        self.timeStamp = time.strftime('%Y_%m_%d_%H_%M_%S_',time.localtime(time.time()))

        # Reference Line Settings
        self.refLine = None
        self.rL_cenX = 300
        self.rL_half_width = 10


    def checkInput(self,frame):
        if self.refLine is None:
            # 第一帧的时候切割下原始参考线
            self.refLine = frame[:, self.rL_cenX-self.rL_half_width : self.rL_cenX+self.rL_half_width]
            self.hand_last = -6     # -6 = 手在外面， 6 = 手在里面, 其余为中间状态
            self.hand_present = -6
            return "None"
        # cv.imshow('frame', frame)
        cv.waitKey(1)

        self.frameCount +=1

        curLine = frame[:, self.rL_cenX-self.rL_half_width : self.rL_cenX+self.rL_half_width] # 当前帧的参考线

        isCover = self.CoverCheck(curLine, self.refLine) # 判断是否参考线是否被手覆盖
        # print (isCover)
        if isCover == 1:
            self.hand_present += 2 # 被覆盖的话就将加状态
        else:
            self.hand_present -= 2 # 不被覆盖就减状态

        if abs(self.hand_present) > 6:
            self.hand_present = self.hand_present / abs(self.hand_present) * 6 # 状态只在[-6,6]区间内
        
        # 状态从-6变到6 或 从6变到-6
        if (self.hand_present != self.hand_last) and (abs(self.hand_present) == 6): 
            motion = self.hand_last - self.hand_present
            if motion!= 0:
                motion = motion / abs(motion) # 将motion归一为 1 或 -1
                self.hand_last = self.hand_present # 只在此处存储hand_last，保证它为 -6 或 6
                print('hand state changed. the motion is:',self.motion_dict[motion])  # -1--push, 1--pull
                # import os
                # writePath = os.path.join(os.getcwd(),"../data/output/"+self.timeStamp+"/")
                # if os.path.isdir(writePath) == False:
                #     os.mkdir(writePath)
                # cv.putText(frame, self.motion_dict[motion], (320,240), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
                # cv.imwrite(writePath + str(self.frameCount)+".png",frame)

                return self.motion_dict[motion]
                #img show with detected motion blob
                # cv.imwrite(outputpath+str(frameCount)+".png",frame)
            #self.hand_last = self.hand_present
        
        return "None"

    def checkInput_old(self,frame):
        if self.last_frame is None:
            self.last_frame = frame.copy()
            return "None"

        self.frameCount +=1

        xmin_d,ymin_d,xmax_d,ymax_d = self.adjacentDiff(frame)#to judge hand in state.

        xmin_s,ymin_s,xmax_s,ymax_s = self.fgbgDiff(frame)#to judge hand out state.

        self.last_frame = frame.copy()
        #self.last_frame = frame

        if self.cnt_out < 0:
            self.cnt_out = 0
        if self.cnt_in < 0:
            self.cnt_in = 0

        #every frame has a loss:-1
        self.cnt_out -= 1
        self.cnt_in  -= 1

        #considering the diff method to decide whether the state is 1--hands_in
        #To do: add info from diff to cross-verify
        if AreaCheck(xmin_d,ymin_d,0).passBaseLine() == False:#2 frame above,then believe it's hand in. 
            self.cnt_in += 2  #when detected in the left region, reward 2
        else:
            self.cnt_in -= 1  #else loss -1

        if self.cnt_in >= 3:
            self.hand_present = 1
            self.cnt_in = 3   #need to be modified

        #considering the segm method to decide whether the state is 0--hands_out
        if AreaCheck(xmin_s,ymin_s,0).passBaseLine() == True:
            self.cnt_out += 2  # when detected in the right region, reward 2
        else:
            self.cnt_out -= 1  # else loss -1
        if self.cnt_out >= 3:
            self.hand_present = 0
            self.cnt_out = 3   # need to be modified


        if self.hand_present != self.hand_last:
            motion = self.hand_last - self.hand_present
            if motion!= 0:
                self.hand_last = self.hand_present
                print('hand state changed. the motion is:',self.motion_dict[motion])  # -1--push, 1--pull
                import os
                writePath = os.path.join(os.getcwd(),"../../data/output/"+self.timeStamp+"/")
                if os.path.isdir(writePath) == False:
                    os.mkdir(writePath)

                if self.motion_dict[motion] == "PUSH":
                    cv.circle(frame,(int((xmin_d+xmax_d)/2), int((ymin_d+ymax_d)/2)),5, (255,0,0), 5)
                    cv.rectangle(frame, (xmin_d, ymin_d), (xmax_d, ymax_d), (255, 0, 0), 3)
                else:
                    cv.circle(frame,(int((xmin_s+xmax_s)/2), int((ymin_s+ymax_s)/2)),5, (0,0,255), 5)
                    cv.rectangle(frame, (xmin_s, ymin_s), (xmax_s,ymax_s), (0, 0, 255), 3)

                cv.putText(frame, self.motion_dict[motion], (320,240), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
                cv.imwrite(writePath + str(self.frameCount)+".png",frame)

                return self.motion_dict[motion]
                #img show with detected motion blob
                # cv.imwrite(outputpath+str(frameCount)+".png",frame)
        self.hand_last = self.hand_present
        
        return "None"


    def CoverCheck(self, curLine, refLine):

        present_gray = cv.cvtColor(curLine, cv.COLOR_BGR2GRAY)
        # present_gray = cv.GaussianBlur(present_gray, (21, 21), 0) # 还需要检查是否需要高斯模糊

        ref_gray = cv.cvtColor(refLine, cv.COLOR_BGR2GRAY)
        # last_gray = cv.GaussianBlur(last_gray, (21, 21), 0)

        frame_delta = cv.absdiff(ref_gray, present_gray)
        # frame_delta = cv.absdiff(curLine, refLine)
        frame_delta = cv.threshold(frame_delta, 30, 255, cv.THRESH_BINARY)[1] # the threshold could be modified
        

        frame_delta = cv.erode(frame_delta,None, iterations=2)
        frame_delta = cv.dilate(frame_delta, None, iterations=5) # 先腐蚀后膨胀，消除因为抖动造成的噪点

        # cv.imshow('frame_delta', frame_delta)
        # cv.waitKey(1)

        gray_value_sum = np.sum(frame_delta) # 计算灰度值的总和

        cover_area_ratio = float(gray_value_sum) / (curLine.shape[0] * curLine.shape[1]) / 255 # 计算覆盖区域的ratio

        if cover_area_ratio > 0.05: # 该阈值需要深入测试
            return 1
        else:
            return 0


    def adjacentDiff(self,present):
        xmin = self.default_width
        ymin = 0
        xmax = 0
        ymax = 0

        present_gray = cv.cvtColor(present, cv.COLOR_BGR2GRAY)
        present_gray = cv.GaussianBlur(present_gray, (21, 21), 0)

        last_gray = cv.cvtColor(self.last_frame, cv.COLOR_BGR2GRAY)
        last_gray = cv.GaussianBlur(last_gray, (21, 21), 0)

        frame_delta = cv.absdiff(last_gray, present_gray)
        frame_delta = cv.threshold(frame_delta, 25, 255, cv.THRESH_BINARY)[1] # the threshold should be modified

        #TODO:for future optimization
        frame_delta = cv.erode(frame_delta,None, iterations=2)
        frame_delta = cv.erode(frame_delta, None, iterations=2)
        frame_delta = cv.erode(frame_delta, None, iterations=2)
        frame_delta = cv.erode(frame_delta, None, iterations=1)
        frame_delta = cv.dilate(frame_delta, None, iterations=10)

        #find be connected components and draw the rect bbox
        (_, cnts, _) = cv.findContours(frame_delta.copy(), cv.RETR_CCOMP, cv.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if cv.contourArea(c) < 20: # need to be tested
                continue
            (x, y, w, h) = cv.boundingRect(c)
            #print(cv.contourArea(c))
            if x < xmin:
                xmin = x
                ymin = y
                xmax = x+w
                ymax = y+h
            cv.rectangle(frame_delta, (x, y), (x + w, y + h), (0, 255, 0), 5)
        # img show the diff img with operation and rect bbox
        # cv.imshow("diff_3", frame_delta)
        return (xmin, ymin, xmax, ymax)

    def fgbgDiff(self,frame):
        xmin = self.default_width
        ymin = 0
        xmax = 0
        ymax = 0

        fgmask = self.fgbg.apply(frame)
        fgmask = cv.morphologyEx(fgmask, cv.MORPH_OPEN, self.fgbg_kernel)
        fgmask = cv.threshold(fgmask, 244, 255, cv.THRESH_BINARY)[1] # wipe the shadow

        fgmask = cv.erode(fgmask,None, iterations=2)
        fgmask = cv.erode(fgmask, None, iterations=2)
        fgmask = cv.erode(fgmask, None, iterations=2)
        fgmask = cv.erode(fgmask, None, iterations=1)
        fgmask = cv.dilate(fgmask, None, iterations=10)
        
        (_, cnts, _) = cv.findContours(fgmask.copy(), cv.RETR_CCOMP, cv.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if cv.contourArea(c) < 20: # need to be tested
                continue
            (x, y, w, h) = cv.boundingRect(c)
            #print(cv.contourArea(c))
            if x < xmin:
                xmin = x
                ymin = y
                xmax = x+w
                ymax = y+h
            cv.rectangle(fgmask, (x, y), (x + w, y + h), (0, 255, 0), 5)
        return xmin, ymin, xmax, ymax

# if __name__ == "__main__":
#     motion = MotionDetect()
#     #This would check the success rate of Pull Push judge
#     src_file_name = "../../data/input/left_up2018_01_24_12_13_140.avi"
#     # src_file_name = "../../data/input/left_up2018_01_25_14_52_420.avi"
#     # outputpath = "../../data/output/"
#     cap = cv.VideoCapture(src_file_name)

#     ret, frame = cap.read()
#     while ret:
#         #print("frame is: ",frame)
#         motion.checkInput(frame)
#         ret, frame = cap.read()
#     cap.release()
    
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