from cameraController import CameraController
from network.httpd import make_http_app
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

import requests
import json
import time

from network.utils import Encrypter
from setproctitle import setproctitle
import common.settings as settings

from serial_handler.io_controller import IO_Controller
from detect.detect_result import DetectResult
from detect.motion import MotionDetect
from detect.object_detector import ObjectDetector

class Closet:
    '''
        代表整个柜子
    '''
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
        self.encrypter = Encrypter()
        self.input_queues = Queue(maxsize=20)
        self._detection_queue = Queue(maxsize=20*4)
        self.num_workers = config['num_workers']


        if not settings.is_offline:
            self.IO = IO_Controller()
            self.cart = Cart(self.IO)
            self.initItemData()
       
    def initItemData(self):
        from common.util import get_mac_address
        id = {'uuid': get_mac_address()}
        response = requests.get(settings.INIT_URL,params=id)
        data = response.json()
        result = {}
        for res in data:
            a = float(res['price'])
            b = float(res['weight'])
            c = dict(name = res['goods_name'], price = round(a, 1), weight = round(b, 1))
            result[res['goods_code']] = c
        settings.items = result
        settings.items["0000000000000001"] = dict(name='empty_hand', price=0, weight=184.0)
        # print(settings.items)

    def start(self):
        self.lastDetectTime = time.time()
        self.send_camera_instruction = False

        object_detection_pools = []
        pool = Pool(self.num_workers, ObjectDetector, (self.input_queues,settings.items,settings.camera_number,self._detection_queue))
        self.camera_control = CameraController(input_queue = self.input_queues)

        if settings.has_scale:
            self.scaleDetector = self.camera_control.getScaleDetector()
            self.scaleDetector.setIo(self.IO)
            self.scaleDetector.setCart(self.cart)
        self.detectResult = DetectResult()

        if settings.is_offline:
            stateMachine = Machine(model=self, states=Closet.states, transitions=Closet.transitions, initial='left-door-open')
            self.debugTime = time.time()
            self.updateScheduler = tornado.ioloop.PeriodicCallback(self.update,10)#50 fps
            self.updateScheduler.start()
            laterStart = functools.partial(self.autoDelayStart)
            tornado.ioloop.IOLoop.current().call_later(delay=2, callback=laterStart)
        else:
            make_http_app(self).listen(5000)
            stateMachine = Machine(model=self, states=Closet.states, transitions=Closet.transitions, initial='pre-init')
            self.init_success()
            settings.logger.warning('camera standby')
            print("Start success")


        handler = SignalHandler(object_detection_pools, tornado.ioloop.IOLoop.current())
        signal.signal(signal.SIGINT, handler.signal_handler)

        tornado.ioloop.IOLoop.current().start()

    def autoDelayStart(self):
        self.curSide = 0
        self._start_imageprocessing()


    def authorize(self, token, side):
        try:
            if side == self.IO.doorLock.LEFT_DOOR:
                self.authorization_left_success()
            else:
                self.authorization_right_success()
        except transitions.core.MachineError:
            #settings.logger.info(self.state)
            settings.logger.warning('State conversion error')
            return

        while True:#empty last detection queue
            try:
                result = self._detection_queue.get_nowait()
            except queue.Empty:
                break

        settings.logger.evokeDoorOpen()

        self.door_token = token

        
        self.mode ="normal_mode"
        self.isStopCamera = False
        self.emptyQueueKeepCnt=0


        if settings.speaker_on:
            self.IO.say_welcome()#发声

        self.IO.change_to_inventory_page()#进入购物车界面

        self.IO.unlock(side)#开对应门锁
        
        self.curSide = side

        bug_time = time.time()
    
        while not self.IO.lock_up_door_close(self.curSide):
            if time.time() - bug_time > 2:
                settings.logger.warning('open lock have bug')

        settings.logger.warning('lock is opened by user')

        settings.logger.warning("curside is: {}".format(self.curSide))#default is left side

        self.debugTime = time.time()

        self.timeCnt=[]
        for i in range(settings.camera_number):
            now_time = time.time()
            timer = {"start":now_time,"end":now_time}
            self.timeCnt.append(timer)


        self.outSide0KeepTime = -1.0
        self.outSide1KeepTime = -1.0


        self.updateScheduler = tornado.ioloop.PeriodicCallback(self.update,10)#50 fps
        self.updateScheduler.start()

    def authorize_operator(self, token, side):
        try:
            self.restock_authorize_success()
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
        settings.logger.error("tup is: {}".format(tup))
        if self.cart:
            if tup[1] == 1:
                settings.logger.error("adjust add in {}".format(tup[0]))
                self.cart.add_item(tup[0])#放入物品
            else:
                settings.logger.error("adjust take out {}".format(tup[0]))
                self.cart.remove_item(tup[0])#取出物品

    def delayCheckDoorClose(self):
        door_check = functools.partial(self._check_door_close)
        self.check_door_close_callback = tornado.ioloop.PeriodicCallback(door_check, 300)
        self.check_door_close_callback.start()

    def update(self):
        if self.state == "authorized-left" or self.state ==  "authorized-right":#已验证则检测是否开门

            if not self.send_camera_instruction:
                self._start_imageprocessing()#camera start to open

                self.detectResult.reset()
                self.detectResult.resetDetect()

                if settings.has_scale:
                    self.scaleDetector.reset()
                    self.cart.setBeforDoorOpenWeight()

                self.send_camera_instruction = True


            if self.IO.is_door_lock(self.debugTime):
                settings.logger.info("Time Out time is: {}".format(time.time()-self.debugTime))
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

                self.debugTime = time.time()
                settings.logger.info("OpenDoor time is {}".format(self.debugTime))

                

                laterDoor = functools.partial(self.delayCheckDoorClose)
                tornado.ioloop.IOLoop.current().call_later(delay=2, callback=laterDoor)
        
        if self.state == "left-door-open" or self.state ==  "right-door-open":#已开门则检测是否开启算法检测
                while(not self._detection_queue.empty()):
                    try:
                        result = self._detection_queue.get_nowait()

                        index = result[0]
                        motionType = result[1]
                        frame_time = result[3]#frame time maybe wrong

                        if frame_time < self.debugTime:
                            return

                        # checkIndex = index%2
                        checkIndex = index
                        
                        # self.detectResults[checkIndex].checkData(checkIndex,{motionType:result[2]},frame_time)
                        self.detectResult.checkData(checkIndex,{motionType:result[2]},frame_time)


                        if motionType == "OUT" or motionType =="PULL":
                            self.timeCnt[index]["end"] = frame_time
                        else:
                            self.timeCnt[index]["start"] = frame_time


                        if settings.has_scale:
                            # self.scaleDetector[checkIndex].detect_check(self.detectResults[checkIndex])
                            self.scaleDetector.detect_check(self.detectResult)
                        else:
                            self.detect_check()
                    except queue.Empty:
                        pass

                #To check how long the hand is outside the closet?
                if settings.has_scale:
                    check_cart = True
                    curCameras = settings.left_cameras if self.curSide == self.IO.doorLock.LEFT_DOOR else settings.right_cameras
                    for index in curCameras:
                        if self.timeCnt[index]["end"] - self.timeCnt[index]["start"] <1.0:
                            check_cart = False
                            self.timeCnt[index]["start"] = self.timeCnt[index]["end"]
                            break
                    
                    if check_cart:
                        self.cart.cart_check(self.outSideClosetFromTime)

    def detect_check(self):#pure vision detect
        # detect = self.detectResults[checkIndex].getDetect()
        detect = self.detectResult.getDetect()

        if len(detect) > 0:
            direction = detect[0]["direction"]
            id = detect[0]["id"]

            if settings.items[id]['name'] == "empty_hand":
                print("check empty hand")
                self.detectResult.resetDetect()
                return

            now_time = self.detectResult.getMotionTime("PUSH" if direction is "IN" else "PULL")
            now_num = detect[0]["num"]

            if direction == "IN":
                settings.logger.warning('camera shot Put back {} with num {}'.format(settings.items[id]["name"], now_num))


                if not settings.is_offline:
                    self.cart.remove_item(id,now_time)
            else:
                settings.logger.warning('camera shot Take out {} with num {}'.format(settings.items[id]["name"], now_num))

                if not settings.is_offline:
                    # for i in range(detect[0]["fetch_num"]):
                    self.cart.add_item(id,now_time)

            self.detectResult.resetDetect()

    def _delay_do_order(self):
        self.close_door_success()
        self.updateScheduler.stop()
        self.IO.change_to_processing_page()

        self.send_camera_instruction = False

        order = self.cart.getFinalOrder()
        order["token"] = self.door_token
        self.cart.reset()

        order_data = order["data"]
        for k,v in order_data.items():
            settings.logger.info("final order is {} with num {}".format(settings.items[k]["name"],v))

        if settings.client_mode=="develop":
            order["data"]={}
        # order["data"]={}

        strData = json.dumps(order)
        self.pollData = self.encrypter.aes_cbc_encrypt(strData, key = settings.sea_key)
        self.pollPeriod = tornado.ioloop.PeriodicCallback(self.polling, 50)
        self.pollPeriod.start()

    def polling(self):
        req = requests.post(settings.ORDER_URL, data=self.pollData)
        if req.status_code == 200:
            self.order_process_success()
            self.pollPeriod.stop()
            if settings.box_style == 'single':
                self.IO.change_to_thank_page()
                time.sleep(1)
                self.IO.change_to_welcome_page()
            settings.logger.evokeDoorClose()


    def _check_door_close(self):
        if self.mode == "operator_mode":
            if self.IO.is_door_lock(curSide = self.curSide):
                self.check_door_close_callback.stop()
                settings.logger.warning('Door Closed!')
                self.restock_close_door_success()
        else:
            if self.IO.is_door_lock(curSide = self.curSide):
                if not self.isStopCamera:
                    if settings.speaker_on:
                        self.IO.say_goodbye()

                    self._stop_imageprocessing()
                    self.isStopCamera = True

                    if settings.has_scale:
                        self.scaleDetector.notifyCloseDoor()
                        self.cart.setAfterDoorCloseWeight()
                else:
                    # self.input_queues,settings.items,self._detection_queue
                    if self.input_queues.empty() and self._detection_queue.empty():
                        self.emptyQueueKeepCnt +=1
                    if self.emptyQueueKeepCnt == 4:
                        settings.logger.warning('Door Closed!')
                        self.check_door_close_callback.stop()
                        laterAction = functools.partial(self._delay_do_order)
                        tornado.ioloop.IOLoop.current().call_later(delay=2, callback=laterAction)

    #发送摄像头工作指令消息
    def _start_imageprocessing(self):
        if self.curSide == 0:
            self.camera_control.startCameras(settings.left_cameras)
        else:
            self.camera_control.startCameras(settings.right_cameras)

    #发送摄像头停止工作指令消息
    def _stop_imageprocessing(self):
        self.camera_control.stopCameras()
