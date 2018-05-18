# -*- coding: utf-8 -*-
import numpy as np
from detect.detect_frame import DetectFrame
import common.settings as settings

class ImageStitch(object):
    def __init__(self):
        self.cacheList=[]
        self.vertical = None
        self.divide_val = None

    def loadIn(self,detect_frame):
        if len(self.cacheList) < settings.stitching_number:
            self.cacheList.append(detect_frame)
        else:
            final_frame = self.stitching()
            self.cacheList = []
            return final_frame

        return None

    def filter(self,rawResults):
        realResults = []
        for raw in rawResults:
            if self.vertical:
                if raw[1]['up_y'] <= self.divide_val and raw[1]['down_y'] >= self.divide_val:
                    pass
                else:
                    realResults.append(raw[0])
            else:
                if raw[1]['left_x'] <= self.divide_val and raw[1]['right_x'] >= self.divide_val:
                    pass
                else:
                    realResults.append(raw[0])

        return realResults

    def stitching(self):
        frame = self.cacheList

        if settings.stitching_number < 3:
            # pure_frame = (frame[0].frameData, frame[1].frameData)
            image_a = sorted(frame, key = lambda x: x.frameData.shape[1])
            pure_frame_a = (image_a[1].frameData, image_a[0].frameData)
            sum_planA, photo_sign_A = self.black_area_add(pure_frame_a, reverse = False)

            image_b = sorted(frame, key = lambda x: x.frameData.shape[0])
            pure_frame_b = (image_b[1].frameData, image_b[0].frameData)
            sum_planB, photo_sign_B = self.black_area_add(pure_frame_b, reverse = True)
            # print(pure_frame_b[0].shape[0], 'hhhhhhhhhh', pure_frame_b[1].shape[0])

            if sum_planB - sum_planA >= 0:
                self.vertical = True
                frame_merge = self.compose_photo_two_image(pure_frame_a, photo_sign_A, x = 1, y = 0, plan_a = True)

                self.divide_val = pure_frame_a[0].shape[0]

            else:
                self.vertical = False
                frame_merge = self.compose_photo_two_image(pure_frame_b, photo_sign_B, x = 0, y = 1, plan_a = False)

                self.divide_val = pure_frame_b[0].shape[1]

            return frame_merge

        elif number < 4:
            # left_x = frame[0].shape[1]
            # middle_x = frame[1].shape[1]
            # right_x = frame[2].shape[1]
            # left_y = frame[0].shape[0]
            # middle_y = frame[1].shape[0]
            # right_y = frame[2].shape[0]
            # left_area = left_x + left_y
            # middle_area = middle_x + middle_y
            # right_area = right_x + right_y
            # area = []
            # for i in frame:
            #     area.append([i.shape[1], i.shape[0]])
            frame.sort(key = lambda x: x.shape[1]) #max min是以x轴方向的大小来判断的

            max_x = frame[0].shape[1]
            middle_x = frame[1].shape[1]
            min_x = frame[2].shape[1]
            max_y = frame[0].shape[0]
            middle_y = frame[1].shape[0]
            min_y = frame[2].shape[0]

            if max_x >= (max_y + middle_y + min_y):
                sum1 = (max_x - (max_y + middle_y + min_y)) * max_x + (max_x - middle_x) * middle_y + (max_x - min_x) * min_y

            else:
                sum2 = ((max_y + middle_y + min_y) - max_x) * (max_y + middle_y + min_y) + (max_x - middle_x) * middle_y + (max_x - min_x) * min_y

            if (middle_x + min_x) <= max_x:

                if min_y <= middle_y:

                    if max_x >= (max_y + middle_y):
                        sum3 = (max_x - (max_y + middle_y)) * max_x + (max_x - (middle_x + min_x)) * middle_y + (middle_y - min_y) * min_x
                    else:
                        sum4 = ((max_y + middle_y) - max_x) * (max_y + middle_y) + (middle_y - min_y) * (max_x - middle_x) + (max_x - (middle_x + min_x)) * min_y

                else:
                    if max_x >= (max_y + min_y):
                        sum5 = (max_x - (max_y + min_y)) * max_x + (min_y - middle_y) * middle_x + (max_x - (middle_x + min_x)) * (max_x - max_y)

                    else:
                        sum6 = ((max_y + min_y) - max_x) * (max_y + min_y) + (max_x - (middle_x + min_x)) * min_y + (min_y - middle_y) * middle_x

            else:

                if min_y <= middle_y:

                    if (middle_x + min_x) >= (max_y + middle_y):
                        sum7 = ((middle_x + min_x) - (max_y + middle_y)) * (middle_x + min_x) + ((middle_x + min_x) - max_x) * max_y + (middle_y - min_y) * min_x

                    else:
                        sum8 = ((max_y + middle_y) - (middle_x + min_x)) * (max_y + middle_y) + ((middle_x + min_x) - max_x) * max_y + (middle_y - min_y) * min_x

                else:
                    if (middle_x + min_x) >= (max_y + middle_y):
                        sum9 = ((middle_x + min_x) - (max_y + middle_y)) * (middle_x + min_x) + (min_y - middle_y) * middle_x + ((middle_x + min_x) - max_x) * max_y

                    else:
                        sum10 = ((max_y + middle_y) - (middle_x + min_x)) * (max_y + min_y) + ((middle_x + min_x) - max_x) * max_y + (min_y - middle_y) * middle_x

            if min_y <= (max_y + middle_y):

                if (max_x + min_x) <= (max_y + middle_y):
                    sum11 = ((max_y + middle_y) - (max_x + min_x)) * (max_y + middle_y) + (max_x - middle_x) * middle_y + ((max_y + middle_y) - min_y) * min_x

                else:
                    sum12 = ((max_x + min_x) - (max_y + mille_y)) * (max_x + min_x) + (max_x - middle_x) * middle_y + ((max_y + middle_y) - min_y) * min_x

            else:

                if (max_x + min_x) >= min_y:
                    sum13 = ((max_x + min_x) - min_y) * (max_x + min_x) + (min_y - max_y) * (max_x - middle_x) + (min_y - (max_y + middle_y)) * middle_x

                else:
                    sum14 = (min_y - (max_x + min_x)) + min_y + (min_y - max_y) * (max_x - middle_x) + (min_y - (max_y + middle_y)) * middle_x


    def black_area_add(self, frame, reverse = False):
        if reverse:
            left_x = frame[0].shape[0]
            right_x = frame[1].shape[0]
            left_y = frame[0].shape[1]
            right_y = frame[1].shape[1]
        else:
            left_x = frame[0].shape[1]
            right_x = frame[1].shape[1]
            left_y = frame[0].shape[0]
            right_y = frame[1].shape[0]


        if left_x >= (left_y + right_y):
            sum_plan = (left_x - right_x) * right_y + left_x * (left_x - left_y - right_y) #up concatenate down
            photo_sign = 1
        else:
            sum_plan = (left_x - right_x) * right_y + (left_y + right_y) * (left_y + right_y - left_x) #up concatenate down
            photo_sign = 2

        return sum_plan, photo_sign


    def compose_photo(self, small_fill_y, small_fill_x, big_fill_y, big_fill_x, frame_merge_filled, frame_merge_temp, axises, exchange = False):
        fill1 = np.zeros((small_fill_y,small_fill_x, 3), np.uint8)
        frame_temp_temp = np.concatenate((frame_merge_filled, fill1), axis = axises[0])
        fill2 = np.zeros((big_fill_y, big_fill_x, 3), np.uint8)
        if exchange:
            frame_temp = np.concatenate((frame_temp_temp, frame_merge_temp), axis = axises[1])
        else:
            frame_temp = np.concatenate((frame_merge_temp, frame_temp_temp), axis = axises[1])
        frame_merge = np.concatenate((frame_temp, fill2), axis = axises[2])
        return frame_merge

    def compose_photo_two_image(self, frame, sign, x, y, plan_a = True):
        if plan_a:
            if sign == 1: 
                frame_merge = self.compose_photo(small_fill_y = frame[1].shape[y], small_fill_x = frame[0].shape[x] - frame[1].shape[x], big_fill_y = frame[0].shape[x] - frame[0].shape[y] - frame[1].shape[y],
                            big_fill_x = frame[0].shape[x], frame_merge_filled = frame[1], frame_merge_temp = frame[0], axises = [1, 0, 0])

            if sign == 2:
                frame_merge = self.compose_photo(small_fill_y = frame[1].shape[y], small_fill_x = frame[0].shape[x] - frame[1].shape[x], big_fill_y = frame[0].shape[y] + frame[1].shape[y],
                            big_fill_x = frame[0].shape[y] + frame[1].shape[y] - frame[0].shape[x], frame_merge_filled = frame[1], frame_merge_temp = frame[0], axises = [1, 0, 1])

        else:
            if sign == 1: 
                frame_merge = self.compose_photo(small_fill_x = frame[1].shape[y], small_fill_y = frame[0].shape[x] - frame[1].shape[x], big_fill_x = frame[0].shape[x] - frame[0].shape[y] - frame[1].shape[y],
                            big_fill_y = frame[0].shape[x], frame_merge_filled = frame[1], frame_merge_temp = frame[0], axises = [0, 1, 1])

            if sign == 2:
                frame_merge = self.compose_photo(small_fill_x = frame[1].shape[y], small_fill_y = frame[0].shape[x] - frame[1].shape[x], big_fill_x = frame[0].shape[y] + frame[1].shape[y],
                            big_fill_y = frame[0].shape[y] + frame[1].shape[y] - frame[0].shape[x], frame_merge_filled = frame[1], frame_merge_temp = frame[0], axises = [0, 1, 0])
        return frame_merge
