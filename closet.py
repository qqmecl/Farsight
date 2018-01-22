from camera_handler import CameraHandler
from object_detector import ObjectDetector
from httpd import make_http_app, HTTP_PORT
from signal_handler import SignalHandler
from cart import Cart

from visualize import VisualizeDetection
from selfcheck import selfcheck

import multiprocessing
import logging
from multiprocessing import Queue, Pool, Process
import tornado.ioloop
import signal
import functools
import transitions
from transitions import Machine
import queue

import requests
import json

from setproctitle import setproctitle

# import settings
from serial_handler.io_controller import IO_Controller
 
from detect_result import DetectResult 
import time

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


        dict(trigger='scale_value_changed', source='left-door-open', dest='left-door-detecting'),
        dict(trigger='scale_value_changed', source='right-door-open', dest='right-door-detecting'),

        # TODO:
        # - 关门之后延时锁门。似乎是硬件层面实现，无法在软件中控制。需要确认
        dict(trigger='close_door_success', source=['left-door-open', 'right-door-open'], dest='processing-order'),
        dict(trigger='close_door_success', source=['left-door-detecting', 'right-door-detecting'], dest='processing-order'),
        
        dict(trigger='order_process_success', source='processing-order', dest='standby'),
        dict(trigger='restock_authorize_success', source='standby', dest='authorized-restock'),
        dict(trigger='restock_open_door_success', source='authorized-restock', dest='restocking'),
        dict(trigger='restock_success', source='restocking', dest='standby')
    ]

    def __init__(self, **config):
        self.logger = multiprocessing.get_logger()
        self.logger.setLevel(logging.INFO)

        self.input_queues = [ Queue(maxsize=config['queue_size'])]*4


        self.output_queues = [ Queue(maxsize=config['queue_size'])]*4

        self._detection_queue = Queue(maxsize=30*2)

        self.open_door_time_out = 300#which means 80*20ms = 8s

        self.num_workers = config['num_workers']

        self.visualized_camera = config['visualize_camera']

        self.left_cameras = config['left_cameras']
        self.right_cameras = config['right_cameras']

        self.door_port = config['door_port']
        self.speaker_port = config['speaker_port']
        self.scale_port = config['scale_port']
        self.screen_port = config['screen_port']

        self.http_port = config['http_port']

        self.scale_statis = []

        self.IO = IO_Controller(self.door_port,self.speaker_port,self.scale_port,self.screen_port)

        
        if self.visualized_camera is not None:
            self.visualization = VisualizeDetection(self.output_queues[self.visualized_camera])


    def start(self):
        # 启动后台物体识别进程
        object_detection_pools = []

        # sides = map(lambda x: 'left' if x < 2 else 'right', self.left_cameras + self.right_cameras)

        indexs = self.left_cameras + self.right_cameras

        # 每个摄像头启动一个进程池
        for input_q, output_q, index in zip(self.input_queues, self.output_queues, indexs):
            # print(input_q,output_q,index)
            pool = Pool(self.num_workers, ObjectDetector, (input_q, output_q, self._detection_queue))

        self.machine = Machine(model=self, states=Closet.states, transitions=Closet.transitions, initial='pre-init')

        self.logger.info(self.state)

        # 自检
        # selfcheck()

        # 启动摄像头
        self.camera_ctrl_queue = Queue(1)
        cam_handler = CameraHandler(self.camera_ctrl_queue, self.input_queues)


        # TODO:
        # 使用 Process 需要处理可能存在的进程崩溃问题
        camera_process = Process(target=cam_handler.start)
        camera_process.start()

        # 对所有的摄像头发送standby指令，启动摄像头并且进入待命状态
        self.camera_ctrl_queue.put(dict(cmd='standby', cameras=self.left_cameras + self.right_cameras))
        self.logger.info('摄像头已启动')


        #连接串口管理器
        self.IO.start()

        self.detectResult = DetectResult(-1,0)


        # 捕获 CTRL-C
        handler = SignalHandler(camera_process, object_detection_pools, tornado.ioloop.IOLoop.current())
        signal.signal(signal.SIGINT, handler.signal_handler)

        # 启动 web 服务
        app = make_http_app(self)
        app.listen(self.http_port)

        self.init_success()
        self.logger.info(self.state)

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
            self.logger.warn('状态转换错误!!')
            return

        # 一定要在开门之前读数，不然开门动作可能会让读数抖动
        self.cart = Cart(token, self.IO)

        # self.logger.info(self.state)

        self.beforeScaleVal = self.IO.get_scale_val()

        self.IO.say_welcome()#发声

        self.IO.change_to_inventory_page()#进入购物车界面

        self.IO.unlock(side)#开对应门锁

        self.logger.info('用户已经打开锁')

        self.curSide = side

        print("curside is: ",self.curSide)#default is left side

        self.updateScheduler = tornado.ioloop.PeriodicCallback(self.update, 12)#50 fps
        self.updateScheduler.start()
        #self._start_imageprocessing()


    def adjust_items(self,tup):
        print("tup is: ",tup)

        if self.cart:
            if tup[1] == '1':
                print("adjust add in ",tup[0])
                self.cart.add_item(tup[0])#放入物品
            else:
                print("adjust take out ",tup[0])
                self.cart.remove_item(tup[0])#取出物品


    def update(self):
        if self.state == "authorized-left" or self.state ==  "authorized-right":#已验证则检测是否开门
            self.open_door_time_out -= 1

            if self.open_door_time_out <= 0:
                #已经检查足够多次，重置状态机，并且直接返回
                print('超时未开门')

                self.door_open_timed_out()

                print(self.state)

                self.open_door_time_out = 300#which means 120*12ms = 8s

                self.IO.change_to_welcome_page()
                return

            
            if self.IO.is_door_open(self.curSide):
                if self.curSide == self.IO.doorLock.LEFT_DOOR:
                    self.open_leftdoor_success()
                else:
                    self.open_rightdoor_success()
                self.logger.info('用户已经打开门')
                self.lastScaleVal=None
                self._start_imageprocessing()

                door_check = functools.partial(self._check_door_close)
                self.check_door_close_callback = tornado.ioloop.PeriodicCallback(door_check, 300)
                self.check_door_close_callback.start()
        

        if self.state == "left-door-open" or self.state ==  "right-door-open":#已开门则检测是否开启算法检测
            #此处只能通过本主进程管理控制所有的状态变化，开启摄像头发送帧进程的发送
            self.scale_statis.append(self.IO.get_scale_val())

            if self.lastScaleVal is None:
                self.lastScaleVal = self.IO.get_scale_val()#初始静止状态时的量称值

            curScaleVal = self.IO.get_scale_val()

            # print("-----------------------------")
            # print("last val is: ",self.lastScaleVal)
            # print("cur val is: ", curScaleVal)
            # print("-----------------------------")
            # print("                             ")

            #judge OUT Direction start
            if abs(self.lastScaleVal - curScaleVal) > 0.1:#单位为kg,捕捉到初始量称发生的变化，开启摄像头捕捉
                # print("lastScaleVal is: ",self.lastScaleVal)
                # print("curScaleVal is: ",curScaleVal)
                self.detectResult.setEnvokeTime()
                
                print("                         ")
                self.logger.info("------------------------------------------------")
                self.logger.info("Detection envoked ({},{})!!!! ".format(self.lastScaleVal,curScaleVal))
                self.logger.info("-------------------------------------------------")

                # self.evokeTime = time.time()

                #给摄像头进程发送 start 控制指令
                self.scale_value_changed()

                action = 1 
                if self.lastScaleVal - curScaleVal > 0.1:#
                    while(1):#clear all old data here.
                        try:
                            item = self._detection_queue.get_nowait()
                            # self.detectResult.put(item)#每次都拿
                        except queue.Empty:
                            break
                    # print("locate before frame len is: ",COUNT)
                    action = -1 #被拿走了物品
               
                self.detectResult.reset(action,self.curSide)
                # self.detectResult.reset(action,self.curSide,self.lastScaleVal)
                if action == 1:#默认被放置了物品,则取走队列中的所有识别结果
                    COUNT=0
                    while(1):
                        try:
                            COUNT+=1
                            item = self._detection_queue.get_nowait()
                            self.detectResult.put(item)#每次都拿
                        except queue.Empty:
                            break

                    self.detectResult.debugTest(forcePrint=True)

                    print("理论上在此之前应该识别出识别结果")
                    
                    self.logger.info("locate before frame len is: "+str(COUNT))
            else:
                self.lastScaleVal = curScaleVal

        
        if self.state == "left-door-detecting" or self.state ==  "right-door-detecting":
            #捕捉到重量变化则开始检查是否开启算法结果验证
            self._analyse_result()


    def _analyse_result(self):
        '''
            检测是否有新物品被识别出来，并且进行相应操作（放入购物车，从购物车移除）
        '''
        #考虑一侧门打开后，上下摄像头的不同数据
        #detectionQueue中共有两个摄像头的数据,分别为(0,1)或(2,3)

        #不考虑非常快速拿饮料的情况
        #不考虑同时拿多瓶饮料的情况
        #不考虑同时从上下货架拿饮料的情况
        #判断具体拿了什么物品

        # print("locate test: ----------------")
        # for i in range(3):
        try:
            item = self._detection_queue.get_nowait()#no worry of overflow.
            self.detectResult.put(item)#每次都拿
            # print("Detection envoked---,item",item)
            # self.detectResult.debugTest()
        except queue.Empty:
            # print("得不到满足置信度的帧")
            pass

        # print("before  state is: ",self.state)
        #
        if self.detectResult.isComplete():
            #矫正识别错误的out方向

            # if self.detectResult.getDirection() == "IN":
                # if self.IO.get_scale_val() - self.lastScaleVal < 0.1:
                #     print("Modify direction In --> Out!!!!")
                #     self.detectResult.setDirection("OUT")


            if self.curSide == self.IO.doorLock.LEFT_DOOR:
                self.left_door_detect_complete()
            else:
                self.right_door_detect_complete()

            # print("after complete weird state is: ",self.state)

            #a single action envoked,reset current scale value.
            self.lastScaleVal = None

            labelId = self.detectResult.getLabel()
            if self.detectResult.getDirection() == "OUT":
                # print("out")
                self.cart.add_item(labelId)
            else:
                # pass
                self.cart.remove_item(labelId)
            

    def _delay_print(self):
        # print("scaleValue is: ",self.scale_statis)
        self.scale_statis=[]

    def _check_door_close(self):
        '''
            检查门是否关闭，此时只是关上了门，并没有真正锁上门
        '''
        if not self.IO.is_door_open(self.curSide):
            self.close_door_success()

            reset = functools.partial(self._delay_print)
            tornado.ioloop.IOLoop.current().call_later(delay=8, callback=reset)

            self.updateScheduler.stop()

            self._stop_imageprocessing()

            self.logger.info(self.state)

            self.logger.info('用户已经关上门')
            self.check_door_close_callback.stop()

            #eliminate empty order
            if self.cart.as_order()["data"] != {}:
                self.logger.info(self.cart.as_order())
                
                # 发送订单到中央服务
                requests.post(Closet.ORDER_URL, data=json.dumps(self.cart.as_order()))
                self.order_process_success()
            else:
                self.order_process_success()

            self.IO.say_goodbye()
            self.IO.change_to_processing_page()

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
