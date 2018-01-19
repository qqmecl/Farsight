import tornado.web
from serial_handler.door_lock import DoorLockHandler
import json

HTTP_PORT = 8888
SECRET_KEY = "grtrgewfgvs"  # 和原来代码一样，写死了先


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")


class AuthorizationHandler(tornado.web.RequestHandler):
    '''
        授权开门 Handler
        TODO:
        - 在生产环境中不相应 GET 请求
        - 修改鉴权算法，不使用写死的 SECRET_KEY（可以先使用 SECRET_KEY + Nonce + Timestamp 签名验证）
    '''
    def initialize(self, closet):
        self.closet = closet

    def get(self):
        secret = self.get_query_argument('secret')
        side = self.get_query_argument('side', 'left')
        role = self.get_query_argument('role', 'user')
        token = self.get_query_argument('token')
        
        itemId = self.get_query_argument('itemId', '0000')
        num = self.get_query_argument('num',1)

        #1代表加
        #0代表减
        # "product"
        # "fljljefjewoi"
        self._handle_door(secret, side, token,itemId,num, role)

    def post(self):
        # print(self.request.body)
        data = tornado.escape.json_decode(self.request.body)
        print(data)
        # print(data.get('itemId','000'))

        self._handle_door(data['secret'], data.get('side', 'left'), 
            data['token'], data.get('itemId','000'),
            data.get('num',0),data.get('role', 'user'))

    def _handle_door(self, secret, side, token,itemId,num,role='user'):
        if secret == SECRET_KEY:
            if token == "product":
                # print("adjust: ",itemId,num)
                self.closet.adjust_items((itemId,num))
            else:
                if role == 'user':
                    if side == 'left':
                        self.closet.authorize(token=token, side=DoorLockHandler.LEFT_DOOR)
                    else:
                        self.closet.authorize(token=token, side=DoorLockHandler.RIGHT_DOOR)
                elif role == 'operator':
                    # 配货员逻辑，同时解锁两边门
                    self.closet.authorize_operator()

                self.write(json.dumps(dict(message='open sesame', data=dict(status=1))))
        else:
            self.write(json.dumps(dict(message='bad secret', data=dict(status=-1))))


def make_http_app(closet):
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/door", AuthorizationHandler, dict(closet=closet)),
    ])
