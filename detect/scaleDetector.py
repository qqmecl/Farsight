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

	def check(self,motions):
		motion,isCover = motions[0],motions[1]
		if motion == "PUSH":
			self.lastScale = self.IO.get_stable_scale()

			if self.cart.getStartWeight() is None or self.cart.isEmpty():
				self.cart.setStartWeight(self.lastScale)
				
			if self.detectState == "PULL_CHECKING":
				self.detectState = "NORMAL"

			print("this push scale is: ",self.lastScale)

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
					self.detectState = "NORMAL"
				else:
					# if self.index == 0:
					print("current is: ",current)
					print("self.lastScale is: ",self.lastScale)

			if self.detectState == "PUSH_CHECKING":
				if delta > (self.curActionDelta/2):
					print("push_checking in back success!!")
					_id = self.detectCache[0]["id"]

					#for i in range(self.detectCache[0]["fetch_num"]):
					self.cart.remove_item(_id,self.lastDetectTime)
						
					self.detectState = "NORMAL"
					self.lastScale += self.curActionDelta

	def detect_check(self,detectResults):
		detect = detectResults.getDetect()

		if len(detect) > 0:
			direction = detect[0]["direction"]
			self.lastDetectTime = detectResults.getMotionTime("PUSH" if direction is "IN" else "PULL")
				
			# print(detect)
			_id = detect[0]["id"]
			print("                        ")
			print("                        ")
			print("action time is: ",self.lastDetectTime)

			#[{'direction': 'OUT', 'id': '6921581596048001', 'num': 26, 'time': 1524473704.6296923, 'fetch_num': 2}]
			print("direction {} got {} by time {} with num {}".format(detect[0]["direction"],settings.items[_id]["name"],self.lastDetectTime,detect[0]["num"]))
			print("                        ")
			print("                        ")

			if settings.items[_id]['name'] == "empty_hand":
				print("check empty hand take out")
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
