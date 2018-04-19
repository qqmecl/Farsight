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
        self.check_door_time_out = False
        
        self.num_workers = config['num_workers']
        self.left_cameras = config['left_cameras']
        self.right_cameras = config['right_cameras']

        self.IO = IO_Controller()
        # 一定要在开门之前读数，不然开门动作可能会让读数抖动
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

        object_detection_pools = []
        indexs = self.left_cameras + self.right_cameras

        pool = Pool(self.num_workers, ObjectDetector, (self.input_queues,settings.items,self._detection_queue))

        self.machine = Machine(model=self, states=Closet.states, transitions=Closet.transitions, initial='pre-init')
        self.camera_control = CameraController(input_queue = self.input_queues)

        if settings.has_scale:
            self.scaleDetector = []
            for i in range(2):
                scaleDetector = self.camera_control.getScaleDetector(i)
                scaleDetector.setIo(self.IO)
                scaleDetector.setCart(self.cart)
                self.scaleDetector.append(scaleDetector)


        settings.logger.warning('camera standby')

        self.detectResults = []
        for i in range(2):
            self.detectResults.append(DetectResult())

        handler = SignalHandler(object_detection_pools, tornado.ioloop.IOLoop.current())
        signal.signal(signal.SIGINT, handler.signal_handler)


        make_http_app(self).listen(5000)

        self.init_success()

        print("Start success")

        tornado.ioloop.IOLoop.current().start()


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

        self.detectCache=None

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

                self._start_imageprocessing()

                for i in range(2):
                    self.detectResults[i].reset()
                    self.detectResults[i].resetDetect()
                    if settings.has_scale:
                        self.scaleDetector[i].reset()

                laterDoor = functools.partial(self.delayCheckDoorClose)
                tornado.ioloop.IOLoop.current().call_later(delay=2, callback=laterDoor)
        
        if self.state == "left-door-open" or self.state ==  "right-door-open":#已开门则检测是否开启算法检测
                while(not self._detection_queue.empty()):
                    result = self._detection_queue.get_nowait()

                    index = result[0]
                    motionType = result[1]
                    frame_time = result[3]#frame time maybe wrong

                    if frame_time < self.debugTime:
                        return

                    checkIndex = index%2
                    
                    self.detectResults[checkIndex].checkData(checkIndex,{motionType:result[2]},frame_time)

                    if settings.has_scale:
                        self.scaleDetector[checkIndex].detect_check(self.detectResults[checkIndex])
                    else:
                        self.detect_check(checkIndex)

    def detect_check(self,checkIndex):#pure vision detect
        detect = self.detectResults[checkIndex].getDetect()

        if len(detect) > 0:
            direction = detect[0]["direction"]
            id = detect[0]["id"]

            if settings.items[id]['name'] == "empty_hand":
                print("check empty hand")
                self.detectResults[checkIndex].resetDetect()
                return

            now_time = self.detectResults[checkIndex].getMotionTime("PUSH" if direction is "IN" else "PULL")
            now_num = detect[0]["num"]
            intervalTime = now_time - self.lastDetectTime

            if intervalTime > 0.5:
                self.detectCache = None
                self.detectCache=[detect[0]["id"],detect[0]["num"]]
                if direction == "IN":
                    settings.logger.warning('{0} camera shot Put back,{1} with num {2}'.format(checkIndex,settings.items[id]["name"], now_num))

                    for i in range(detect[0]["fetch_num"]):
                        self.detectCache.append(self.cart.remove_item(id))

                else:
                    settings.logger.warning('{0} camera shot Take out {1} with num {2}'.format(checkIndex,settings.items[id]["name"], now_num))
                    
                    for i in range(detect[0]["fetch_num"]):
                        self.cart.add_item(id)

                    self.detectCache.append(True)
            else:
                if self.detectCache is not None:
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
                            if actionSuccess:
                                self.cart.add_item(cacheId)
                                settings.logger.warning('adjust|take out,{},|'.format(settings.items[cacheId]["name"]))

                            self.cart.remove_item(id)
                            settings.logger.warning('adjust|Put back,{},|'.format(settings.items[id]["name"]))

            self.detectResults[checkIndex].resetDetect()
            self.lastDetectTime = now_time
            self.detectResults[checkIndex].setActionTime()


    def _delay_do_order(self):
        self.close_door_success()
        self.updateScheduler.stop()
        self.IO.change_to_processing_page()

        order = self.cart.as_order()
        order["token"] = self.door_token

        order["data"]={}

        strData = json.dumps(order)
        self.pollData = self.encrypter.aes_cbc_encrypt(strData, key = settings.sea_key)
        self.pollPeriod = tornado.ioloop.PeriodicCallback(self.polling, 50)
        self.pollPeriod.start()

    def polling(self):
        req = requests.post(settings.ORDER_URL, data=self.pollData)
        #settings.logger.info(req.status_code)
        if req.status_code == 200:
            self.order_process_success()
            self.pollPeriod.stop()
            settings.logger.evokeDoorClose()

    #检查门是否关闭，此时只是关上了门，并没有真正锁上门
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
                else:
                    # self.input_queues,settings.items,self._detection_queue
                    if self.input_queues.empty() and self._detection_queue.empty():
                        self.emptyQueueKeepCnt +=1
                    if self.emptyQueueKeepCnt == 4:
                        settings.logger.warning('Door Closed!')
                        for i in range(2):
                            self.detectResults[i].reset()
                        self.check_door_close_callback.stop()
                        self._delay_do_order()

    #发送摄像头工作指令消息
    def _start_imageprocessing(self):
        if self.curSide == self.IO.doorLock.LEFT_DOOR:
            self.camera_control.startCameras(self.left_cameras)
        else:
            self.camera_control.startCameras(self.right_cameras)

    #发送摄像头停止工作指令消息
    def _stop_imageprocessing(self):
        self.camera_control.stopCameras()
