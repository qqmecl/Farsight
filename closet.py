from camera_handler import CameraHandler
from httpd import make_http_app, HTTP_PORT
from signal_handler import SignalHandler
from cart import Cart

import multiprocessing
from multiprocessing import Queue, Pool, Process
import tornado.ioloop
import signal
import functools
import transitions
from transitions import Machine
import queue
import os  # 为视频输出文件创造新的Output文件夹

import requests
import json
from setproctitle import setproctitle
import time
from utils import secretPassword
import settings
from serial_handler.io_controller import IO_Controller

from detect.detect_result import DetectResult
from detect.motion import MotionDetect
from detect.object_detector import ObjectDetector

import cv2
import logging
#chen
import asyncio

class Closet:
    '''
        代表整个柜子
    '''
    ORDER_URL = 'https://www.hihigo.shop/api/v1/order'

    states = [
        'pre-init',            # 尚未初始化和自检
        'standby',             # 等待授权
        'authorized-left',     # 一旦授权，立刻开锁，并且开始检测门是否打开
        'authorized-right',
        'left-door-open',      # 检测到门打开状态后，进入此状态
        'right-door-open',

        'left-door-detecting', #左门识别检测中
        'right-door-detecting',#右门识别检测中

        'processing-order',    # 正在处理订单
        'authorized-restock',  # 授权开始补货
        'restocking'           # 已经开门，正在补货
    ]

    # - 从已授权回到 standby 状态的转移（用户超时未开门）
    transitions = [
        dict(trigger='init_success', source='pre-init', dest='standby'),
        dict(trigger='authorization_left_success', source='standby', dest='authorized-left'),
        dict(trigger='authorization_right_success', source='standby', dest='authorized-right'),

        dict(trigger='door_open_timed_out', source=['authorized-left', 'authorized-right', 'authorized-restock'], dest='standby'),

        dict(trigger='open_leftdoor_success', source='authorized-left', dest='left-door-open'),
        dict(trigger='open_rightdoor_success', source='authorized-right', dest='right-door-open'),


        dict(trigger='left_door_detect_complete', source='left-door-detecting', dest='left-door-open'),
        dict(trigger='right_door_detect_complete', source='right-door-detecting', dest='right-door-open'),


        # dict(trigger='scale_value_changed', source='left-door-open', dest='left-door-detecting'),
        # dict(trigger='scale_value_changed', source='right-door-open', dest='right-door-detecting'),

        # TODO:
        # - 关门之后延时锁门。似乎是硬件层面实现，无法在软件中控制。需要确认
        dict(trigger='close_door_success', source=['left-door-open', 'right-door-open'], dest='processing-order'),
        dict(trigger='close_door_success', source=['left-door-detecting', 'right-door-detecting'], dest='processing-order'),

        dict(trigger='order_process_success', source='processing-order', dest='standby'),

        dict(trigger='restock_authorize_success', source='standby', dest='authorized-restock'),
        dict(trigger='restock_close_door_success', source='authorized-restock', dest='standby')
        #dict(trigger='restock_success', source='restocking', dest='standby')
    ]

    def __init__(self, **config):
        #self.logger = settings.logger
        #chen
        self.loop = asyncio.get_event_loop()

        self.secretPassword = secretPassword()


        self.input_queues = Queue(maxsize=20)


        self._detection_queue = Queue(maxsize=20*4)

        self.check_door_time_out = False

        self.num_workers = config['num_workers']

        self.visualized_camera = config['visualize_camera']

        self.left_cameras = config['left_cameras']
        self.right_cameras = config['right_cameras']

        self.run_mode = config['run_mode']

        self.door_port = config['door_port']
        self.speaker_port = config['speaker_port']
        self.scale_port = config['scale_port']
        self.screen_port = config['screen_port']
        self.http_port = config['http_port']
        self.IO = IO_Controller(self.door_port,self.speaker_port,self.scale_port,self.screen_port)

        self.initItemData()
        if self.visualized_camera is not None:
            self.visualization = VisualizeDetection(self.output_queues[self.visualized_camera])

        logging.getLogger('transitions').setLevel(logging.WARN)

    def initItemData(self):
        import utils
        id = {'uuid': settings.get_mac_address()}
        response = requests.get(settings.init_url,params=id)
        #settings.logger.info('{}'.format(response))
        data = response.json()
        #settings.logger.info('{}'.format(data))
        result = {}
        for res in data:
            a = float(res['price'])
            b = float(res['weight'])
            c = dict(name = res['goods_name'], price = round(a, 1), weight = round(b, 1))
            result[res['goods_code']] = c
        settings.items = result
        #settings.logger.info('{}'.format(settings.items))


    def start(self):
        # settings.logger.info("initiate start by settings.items",settings.items)

        self.lastDetectTime = time.time()
        #print(self.screen_port)
        # 启动后台物体识别进程
        object_detection_pools = []

        # sides = map(lambda x: 'left' if x < 2 else 'right', self.left_cameras + self.right_cameras)

        indexs = self.left_cameras + self.right_cameras

        # 每个摄像头启动一个进程池
        # motions = [MotionDetect()]*2

        self.motions = []

        for i in range(2):
            self.motions.append(MotionDetect())

        # for input_q, index in zip(self.input_queues, indexs):
            # pool = Pool(self.num_workers, ObjectDetector, (input_q,settings.items,self._detection_queue))
        pool = Pool(self.num_workers, ObjectDetector, (self.input_queues,settings.items,self._detection_queue,self.run_mode))

        self.machine = Machine(model=self, states=Closet.states, transitions=Closet.transitions, initial='pre-init')


        # 自检
        # selfcheck()

        # 启动摄像头，创造Output文件夹
        self.camera_ctrl_queue = Queue(1)
        cam_handler = CameraHandler(self.camera_ctrl_queue, self.input_queues)

        if not os.path.exists('/home/votance/Projects/Farsight/Output'):
            os.makedirs('/home/votance/Projects/Farsight/Output')

        # TODO:
        # 使用 Process 需要处理可能存在的进程崩溃问题
        camera_process = Process(target=cam_handler.start)
        camera_process.start()

        # 对所有的摄像头发送standby指令，启动摄像头并且进入待命状态
        self.camera_ctrl_queue.put(dict(cmd='standby', cameras=self.left_cameras + self.right_cameras))
        settings.logger.warning('camera standby')


        #连接串口管理器
        # self.IO.start()

        self.detectResults = []
        for i in range(2):
            self.detectResults.append(DetectResult())


        # 捕获 CTRL-C
        handler = SignalHandler(camera_process, object_detection_pools, tornado.ioloop.IOLoop.current(), self.loop)
        signal.signal(signal.SIGINT, handler.signal_handler)

        # 启动 web 服务
        app = make_http_app(self)
        app.listen(self.http_port)

        self.init_success()


        # 最后：启动 tornado ioloop
        tornado.ioloop.IOLoop.current().start()


    def authorize(self, token, side):
        '''
            用户授权开启一边的门，会解锁对应的门，并且让各个子进程进入工作状态
        '''
        try:
            if side == self.IO.doorLock.LEFT_DOOR:
                self.authorization_left_success()
            else:
                self.authorization_right_success()
        except transitions.core.MachineError:
            #settings.logger.info(self.state)
            settings.logger.warn('State conversion error')
            return



        while True:#empty last detection queue
            try:
                result = self._detection_queue.get_nowait()
            except queue.Empty:
                break


        self.door_token = token      #chen
        # 一定要在开门之前读数，不然开门动作可能会让读数抖动
        self.cart = Cart(token, self.IO)

        # self.logger.info(self.state)

        self.mode ="normal_mode"

        self.beforeScaleVal = self.IO.get_scale_val()

        if settings.speaker_on:
            self.IO.say_welcome()#发声

        self.IO.change_to_inventory_page()#进入购物车界面

        self.IO.unlock(side)#开对应门锁

        settings.logger.warning('lock is opened by user')

        self.curSide = side

        settings.logger.warning("curside is: {}".format(self.curSide))#default is left side

        self.debugTime = time.time()

        self.detectCache=None

        self.firstFrameInit0 = False
        self.firstFrameInit1 = False



        self.updateScheduler = tornado.ioloop.PeriodicCallback(self.update,10)#50 fps
        self.updateScheduler.start()



        #self._start_imageprocessing()

    def authorize_operator(self, token, side):
        '''
            用户授权开启一边的门，会解锁对应的门，并且让各个子进程进入工作状态
        '''
        try:
            self.restock_authorize_success()
            # if side == self.IO.doorLock.LEFT_DOOR:
            #     self.authorization_left_success()
            # else:
            #     self.authorization_right_success()
        except transitions.core.MachineError:
            self.logger.warn('状态转换错误!!')
            return

        self.mode = "operator_mode"

        self.IO.unlock(side)#开对应门锁

        settings.logger.warning('lock is opened by user')

        self.curSide = side

        settings.logger.warning("curside is: {}".format(self.curSide))#default is left side

        door_check = functools.partial(self._check_door_close)
        self.check_door_close_callback = tornado.ioloop.PeriodicCallback(door_check, 300)
        self.check_door_close_callback.start()


    def adjust_items(self,tup):
        settings.logger.info("tup is: {}".format(tup))

        if self.cart:
            if tup[1] == '1':
                settings.logger.info("adjust add in {}".format(tup[0]))
                self.cart.add_item(tup[0])#放入物品
            else:
                settings.logger.info("adjust take out {}".format(tup[0]))
                self.cart.remove_item(tup[0])#取出物品

    def delayCheckDoorClose(self):
        door_check = functools.partial(self._check_door_close)
        self.check_door_close_callback = tornado.ioloop.PeriodicCallback(door_check, 300)
        self.check_door_close_callback.start()

    def update(self):
        if self.state == "authorized-left" or self.state ==  "authorized-right":#已验证则检测是否开门
            #self.open_door_time_out -= 1

            # settings.logger.info("Checking time is: ",time.time()-self.debugTime)

            if self.check_door_time_out == False and time.time()-self.debugTime > 7:
                # now_time = time.time()
                settings.logger.info("Time Out time is: {}".format(time.time()-self.debugTime))

                #已经检查足够多次，重置状态机，并且直接返回
                settings.logger.warning('open door timeout')
                # settings.logger.info(self.state)
                # self.open_door_time_out = True#which means 120*12ms = 8s
                self.IO.change_to_welcome_page()
                self.updateScheduler.stop()
                self.door_open_timed_out()
                return

            if self.IO.is_door_open(self.curSide):
                self.open_door_time_out = True

                if self.curSide == self.IO.doorLock.LEFT_DOOR:
                    self.open_leftdoor_success()
                else:
                    self.open_rightdoor_success()
                settings.logger.warning('door is opened by user')

                self.debugTime = time.time()

                settings.logger.info("OpenDoor time is {}".format(self.debugTime))

                #self.calcTime0 = time.time()

                #self.calc_cnt0 = 0

                #self.calcTime1 = time.time()

                #self.calc_cnt1 = 0
                #self.calc_cnt = 0
                #self.calcTime = time.time()

                # later = functools.partial(self._start_imageprocessing)
                # tornado.ioloop.IOLoop.current().call_later(delay=1.0, callback=later)

                self._start_imageprocessing()

                laterDoor = functools.partial(self.delayCheckDoorClose)
                tornado.ioloop.IOLoop.current().call_later(delay=2, callback=laterDoor)
        if self.state == "left-door-open" or self.state ==  "right-door-open":#已开门则检测是否开启算法检测
                try:



                    result = self._detection_queue.get_nowait()

                    #self.calc_cnt +=1

                    #if time.time() - self.calcTime > 1:
                    #    settings.logger.error("{} calc every second".format(self.calc_cnt))
                    #    self.calcTime = time.time()
                    #    self.calc_cnt = 0

                    index = result[0]
                    frame = result[1]
                    frame_time = result[3]


                    if frame_time < self.debugTime:
                        # settings.logger.info("Check cached frame: ",frame_time,self.debugTime)
                        return

                    # settings.logger.info(self.motions[i])
                    checkIndex = index%2

                    #if checkIndex == 0:
                    #    self.calc_cnt0 +=1

                    #    if time.time() - self.calcTime0 > 1:
                    #        settings.logger.error("{} calc0000 every second".format(self.calc_cnt0))
                    #        self.calcTime0 = time.time()
                    #        self.calc_cnt0 = 0

                    #if checkIndex == 1:
                    #    self.calc_cnt1 +=1

                    #    if time.time() - self.calcTime1 > 1:
                    #        settings.logger.error("{} calc1111 every second".format(self.calc_cnt1))
                    #        self.calcTime1 = time.time()
                    #        self.calc_cnt1 = 0

                    # settings.logger.info("weird index is: ",checkIndex)
                    # settings.logger.info(len(self.motions))
                    if checkIndex == 0 and self.firstFrameInit0 == False:
                        settings.logger.info("Frist 0 camera Frame Init interval time is: {}".format(time.time()-self.debugTime))
                        self.firstFrameInit0 = True
                        # cv2.imwrite("Output/"+str(self.debugTime)+str(index)+"first.png",frame)

                    if checkIndex == 1 and self.firstFrameInit1 == False:
                        settings.logger.info("Frist 1 camera Frame Init interval time is: {}".format(time.time()-self.debugTime))
                        self.firstFrameInit1 = True
                        # cv2.imwrite("Output/"+str(self.debugTime)+str(index)+"first.png",frame)

                    # last_time = time.time()
                    motionType = self.motions[checkIndex].checkInput(frame)
                    # settings.logger.info("Check input use time: ",time.time()-last_time)

                    self.detectResults[checkIndex].checkData(checkIndex,{motionType:result[2]})
                    detect = self.detectResults[checkIndex].getDetect()
                    # if downNum == None:
                    #     if upNum == None:
                    #         return False
                    #     else:
                    #         return chooseDetect(isLast,upNum,upId)
                    # else:
                    #     if upNum == None:
                    #          return chooseDetect(isLast,downNum,downId)
                    #     else:
                    #         if downNum > upNum:
                    #             return chooseDetect(isLast,downNum,downId)
                    #         else:
                    #             return chooseDetect(isLast,upNum,upId)
                    if len(detect) > 0:
                        #settings.logger.error('detect 000000')
                        #chen_time = time.time()

                        direction = detect[0]["direction"]
                        id = detect[0]["id"]

                        now_time = detect[0]["time"]
                        now_num = detect[0]["num"]


                        intervalTime = now_time - self.lastDetectTime

                        settings.logger.info("action interval is: {}".format(intervalTime))

                        if intervalTime > 0.5:
                            self.detectCache = None

                            self.detectCache=[detect[0]["id"],detect[0]["num"]]

                            if direction == "IN":
                                settings.logger.warning('camera{0},|Put back,{1},inventory is {2}.|'.format(checkIndex,settings.items[id]["name"], now_num))

                                self.detectCache.append(self.cart.remove_item(id))
                            else:
                                settings.logger.warning('camera{0},|Take out,{1},inventory is {2}.|'.format(checkIndex,settings.items[id]["name"], now_num))
                                self.cart.add_item(id)
                                self.detectCache.append(True)
                        else:
                            if self.detectCache is not None:
                                #fix camera result
                                settings.logger.info("Enter cache result fixing phase!")
                                cacheId = self.detectCache[0]
                                cacheNum = self.detectCache[1]
                                actionSuccess = self.detectCache[2]

                                if now_num > cacheNum and id != cacheId:
                                    if direction == "OUT":
                                        self.cart.remove_item(cacheId)
                                        self.cart.add_item(id)

                                        settings.logger.warning('adjust|Put back,{},|'.format(settings.items[cacheId]["name"]))
                                        settings.logger.warning('adjust|take out,{},|'.format(settings.items[id]["name"]))
                                    elif direction == "IN":
                                        # if self.cart.isHaveItem(cacheId):
                                        if actionSuccess:
                                            self.cart.add_item(cacheId)
                                            settings.logger.warning('adjust|take out,{},|'.format(settings.items[cacheId]["name"]))

                                        self.cart.remove_item(id)
                                        settings.logger.warning('adjust|Put back,{},|'.format(settings.items[id]["name"]))
                        #settings.logger.error('chen_time is {}'.format(time.time() - chen_time))
                        self.detectResults[checkIndex].resetDetect()

                        self.lastDetectTime = now_time

                        settings.logger.info("Action time is: {}".format(time.time()))
                        self.detectResults[checkIndex].setActionTime()
                        self.loop.run_until_complete(new_chen())
                except queue.Empty:
                    # settings.logger.info()
                    pass
    @asyncio.coroutine
    def new_chen():
        if intervalTime > 0.5:
            self.detectCache = None

            self.detectCache=[detect[0]["id"],detect[0]["num"]]

            if direction == "IN":
                settings.logger.warning('camera{0},|Put back,{1},inventory is {2}.|'.format(checkIndex,settings.items[id]["name"], now_num))
                chen_loop_arg1 = yield from self.cart.remove_item(id)
                self.detectCache.append(chen_loop_arg1)
            else:
                settings.logger.warning('camera{0},|Take out,{1},inventory is {2}.|'.format(checkIndex,settings.items[id]["name"], now_num))
                yield from self.cart.add_item(id)
                self.detectCache.append(True)
        else:
            if self.detectCache is not None:
                #fix camera result
                settings.logger.info("Enter cache result fixing phase!")
                cacheId = self.detectCache[0]
                cacheNum = self.detectCache[1]
                actionSuccess = self.detectCache[2]

                if now_num > cacheNum and id != cacheId:
                    if direction == "OUT":
                        yield from self.cart.remove_item(cacheId)
                        yield from self.cart.add_item(id)

                        settings.logger.warning('adjust|Put back,{},|'.format(settings.items[cacheId]["name"]))
                        settings.logger.warning('adjust|take out,{},|'.format(settings.items[id]["name"]))
                    elif direction == "IN":
                        # if self.cart.isHaveItem(cacheId):
                        if actionSuccess:
                            yield from self.cart.add_item(cacheId)
                            settings.logger.warning('adjust|take out,{},|'.format(settings.items[cacheId]["name"]))

                        yield from self.cart.remove_item(id)
                        settings.logger.warning('adjust|Put back,{},|'.format(settings.items[id]["name"]))

        self.detectResults[checkIndex].resetDetect()

        self.lastDetectTime = now_time

        settings.logger.info("Action time is: {}".format(time.time()))
        self.detectResults[checkIndex].setActionTime()

    def _delay_do_order(self):
        self.close_door_success()

        self.updateScheduler.stop()

        for i in range(2):
            self.motions[i].reset()

        self.IO.change_to_processing_page()


        now_scale = self.IO.get_scale_val()

        delta = now_scale - self.beforeScaleVal
        if  delta < -0.1:
            settings.logger.warning("Envoke weight change")
            if self.cart.as_order()["data"]!={}:
                order = self.cart.as_order()
                # self.logger.info(order)
                strData = json.dumps(order)
                self.pollData = self.secretPassword.aes_cbc_encrypt(strData)
                # settings.logger.info(self.pollData)

                #req = requests.post(Closet.ORDER_URL, data=self.pollData)
                self.pollPeriod = tornado.ioloop.PeriodicCallback(self.polling, 50)
                self.pollPeriod.start()

                # self.order_process_success()
            else:
                self.order_process_success()
                #发送订单到中央服务
                # self.pollPeriod = tornado.ioloop.PeriodicCallback(self.polling, 50)
                # self.pollPeriod.start()
        else:
            settings.logger.warning("Can't Envoke weight change")
            self.order_process_success()


    #chen chen chen
    def polling(self):
        req = requests.post(Closet.ORDER_URL, data=self.pollData)
        #settings.logger.info(req.status_code)
        if req.status_code == 200:
            self.order_process_success()
            self.pollPeriod.stop()

    def door_polling(self):
        req = requests.post(Closet.ORDER_URL, data=self.door_Close_Data)
        #settings.logger.info(req.status_code)
        if req.status_code == 200:
            self.pollPeriod_door_close.stop()


    def _check_door_close(self):
        '''
            检查门是否关闭，此时只是关上了门，并没有真正锁上门
        '''
        if not self.IO.is_door_open(self.curSide):

            self.check_door_close_callback.stop()


            #self.logger.info(self.state)

            settings.logger.warning('door is closed')
            #chen
            order = {'data': {}, 'token': self.door_token, 'code': settings.get_mac_address()}
            strData = json.dumps(order)
            self.door_Close_Data = self.secretPassword.aes_cbc_encrypt(strData)
            self.pollPeriod_door_close = tornado.ioloop.PeriodicCallback(self.door_polling, 50)

            self.pollPeriod_door_close.start()
            #chen
            if self.mode == "operator_mode":

                self.restock_close_door_success()
                return

            self._stop_imageprocessing()

            if settings.speaker_on:
                self.IO.say_goodbye()




            reset = functools.partial(self._delay_do_order)
            tornado.ioloop.IOLoop.current().call_later(delay=3, callback=reset)



    def _start_imageprocessing(self):
        '''
            发送摄像头工作指令消息
        '''
        if self.curSide == self.IO.doorLock.LEFT_DOOR:
            self.camera_ctrl_queue.put(dict(cmd='start', cameras=self.left_cameras))
        else:
            self.camera_ctrl_queue.put(dict(cmd='start', cameras=self.right_cameras))

        if self.visualized_camera is not None:
            self.visualization.start()

    def _stop_imageprocessing(self):
        '''
            发送摄像头停止工作指令消息
        '''
        if self.curSide == self.IO.doorLock.LEFT_DOOR:
            self.camera_ctrl_queue.put(dict(cmd='stop', cameras=self.left_cameras))
        else:
            self.camera_ctrl_queue.put(dict(cmd='stop', cameras=self.right_cameras))

        if self.visualized_camera is not None:
            # TODO: 是否要 cv2.destroyAllWindows() ?
            self.visualization.stop()
