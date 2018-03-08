import tornado.web
from serial_handler.door_lock import DoorLockHandler
import json
import settings
from utils import secretPassword
import os
import signal

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
		self.secretData = secretPassword()

	def parseData(self, psData):
		x = self.secretData.aes_cbc_decrypt(psData)
		params = x.split('&')
		paramsDict = {}
		for i in params:
			j = i.split('=')
			paramsDict[j[0]] = j[1]
		return paramsDict

	def get(self):
		#secretCode = self.get_argument('tt')
		secretCode = (self.request.body).decode()
		paramsDict = self.parseData(secretCode)
		secret = paramsDict.get('secret')
		side = paramsDict.get('side', 'left')
		token = paramsDict.get('token')
		role = paramsDict.get('role', 'user')
		itemId = paramsDict.get('itemId', '0000')
		num = int(paramsDict.get('num', 1))
		print(secret, side, token, role, itemId, num)
		#1代表加
		#0代表减
		# "product"
		# "fljljefjewoi"
		self._handle_door(secret, side, token,itemId,num, role)

	def post(self):
		psp = json.loads((self.request.body).decode())
		print(psp)
		#data = (self.request.body).decode()
		paramsDict = self.parseData(psp['aes_token'])
		print(paramsDict)
		secret = paramsDict.get('secret')
		side = paramsDict.get('side', 'left')
		token = paramsDict.get('token')
		role = paramsDict.get('role', 'user')
		itemId = paramsDict.get('itemId', '000')
		num = int(paramsDict.get('num', 0))

		print(secret, side, token, role, itemId, num)
		# print(data)
		# print(data.get('itemId','000'))
		self._handle_door(secret, side, token,itemId,num, role)

	def _handle_door(self, secret, side, token, itemId, num, role='user'):
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
				elif role == 'worker':
					#self.write(role)
					# 配货员逻辑，同时解锁两边门
					#self.closet.authorize_operator()
					if side == 'left':
						self.closet.authorize_operator(token=token, side=DoorLockHandler.LEFT_DOOR)
					else:
						self.closet.authorize_operator(token=token, side=DoorLockHandler.RIGHT_DOOR)

				self.write(json.dumps(dict(message='open sesame', data=dict(status=1))))
		else:
			self.write(json.dumps(dict(message='bad secret', data=dict(status=-1))))
#chen
class DataHandler(tornado.web.RequestHandler):
	def post(self):
		data = self.get_argument('signal', 'chen')
		print(data)
		if data == 'votance':
			if os.path.exists('/tmp/daemon.pid'):
				print('tttttttt')
				try:
					with open('/tmp/daemon.pid') as f:
						os.kill(int(f.read()), signal.SIGUSR1)
						self.write('zhou')
				except IOError as e:
					self.write('user error')
		elif data == 'pull':
			if os.path.exists('/tmp/daemon.pid'):
				print('sssssss')
				try:
					with open('/tmp/daemon.pid') as f:
						os.kill(int(f.read()), signal.SIGUSR2)
						self.write('jun')
				except IOError as e:
					self.write('user error')


		# print("get result")
		#self.write('friendly user!')

def make_http_app(closet):
	return tornado.web.Application([
		(r"/", MainHandler),
		(r"/door", AuthorizationHandler, dict(closet=closet)),
		(r"/data", DataHandler)
	])
