import common.settings as settings
import time

class ScaleDetector:
	def __init__(self):
		self.IO = None
		self.cart = None
		self.reset()

	def setIo(self,io):
		self.IO = io

	def setCart(self,cart):
		self.cart = cart
	
	def reset(self):
		self.lastScale = 0
		self.curActionDelta = 0
		self.lastDetectTime = 0
		self.detectState = "NORMAL"

		self.detectCache = None
		self.visionDetectTime = None

		#Extra weight variation inferring logic here.
		self.extra_lastScale=0
		self.isRealPullOut = False
		self.isRealPushBack = False

	#In case of missdetection situation.
	def extraCheck(self,motion):
		if motion =="PUSH":
			current = self.IO.get_stable_scale()

			if self.extra_lastScale is None:
				print("first time push")
			else:
				if current - self.extra_lastScale > 100:
					print("something put back")

			self.extra_lastScale = current
		elif motion == "PULL":
			current = self.IO.get_stable_scale()
			if current - self.extra_lastScale < -100:
				print("something take out")

			self.extra_lastScale = current
		else:
			pass

	#Firstly make sure every put back would be countable.
	def check(self,motion):
		# motion,isCover = motions[0],motions[1]
		if motion == "PUSH":
			self.lastScale = self.IO.get_stable_scale()

			if self.cart.getStartWeight() is None or self.cart.isEmpty():
				self.cart.setStartWeight(self.lastScale)
				
			if self.detectState == "PULL_CHECKING":
				self.detectState = "NORMAL"

			#print("this push scale is: ",self.lastScale)

		elif motion == "PULL":
			pass
		else:
			current = self.IO.get_stable_scale()
			delta = current - self.lastScale

			c_time = time.time()
			
			if self.detectState == "PULL_CHECKING":
				if abs(c_time - self.visionDetectTime)< 0.5:
					if delta < -(self.curActionDelta/2):
						_id = self.detectCache[0]["id"]
						
						#for i in range(self.detectCache[0]["fetch_num"]):
							# print("add_item")
						self.cart.add_item(_id,self.lastDetectTime)

						settings.logger.info("Final detect Out {}".format(settings.items[_id]["name"]))

						self.detectState = "NORMAL"
					else:
						pass
						# print("current is: ",current)
						# print("self.lastScale is: ",self.lastScale)
						# print("                      ")

			if self.detectState == "PUSH_CHECKING":
				if delta > (self.curActionDelta/2):
					# print("push_checking in back success!!")
					_id = self.detectCache[0]["id"]

					#for i in range(self.detectCache[0]["fetch_num"]):
					self.cart.remove_item(_id,self.lastDetectTime)
					
					settings.logger.info("Final detect In {}".format(settings.items[_id]["name"]))

					self.detectState = "NORMAL"
					self.lastScale += self.curActionDelta

		# self.extraCheck(motion)

	def detect_check(self,detectResults):
		detect = detectResults.getDetect()

		if len(detect) > 0:
			direction = detect[0]["direction"]
			self.lastDetectTime = detectResults.getMotionTime("PUSH" if direction is "IN" else "PULL")
				
			# print(detect)
			_id = detect[0]["id"]
			#[{'direction': 'OUT', 'id': '6921581596048001', 'num': 26, 'time': 1524473704.6296923, 'fetch_num': 2}]
			settings.logger.info("vision detect direction {} got {} by time {} with num {}".format(detect[0]["direction"],settings.items[_id]["name"],self.lastDetectTime,detect[0]["num"]))

			if settings.items[_id]['name'] == "empty_hand":
				# print("check empty hand take out")
				detectResults.resetDetect()
				return

			if direction == "OUT":
				self.detectState = "PULL_CHECKING"
			else:
				self.detectState = "PUSH_CHECKING"

			self.visionDetectTime = time.time()

			self.curActionDelta = settings.items[_id]['weight']
			self.detectCache = detect
			detectResults.resetDetect()

	def notifyCloseDoor(self):
		if self.detectState == "PULL_CHECKING":
			_id = self.detectCache[0]["id"]
			self.cart.add_item(_id,self.lastDetectTime)
			self.detectState = "NORMAL"
