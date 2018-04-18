import common.settings as settings

class ScaleDetector:
	def __init__(self,index):
		self.IO = None
		self.cart = None
		self.index = index
		self.reset()

	def setIo(self,io):
		self.IO = io

	def setCart(self,cart):
		self.cart = cart
	
	def reset(self):
		self.lastScale = 0

		self.handOutVal = 0
		# self.handInVal = 0

		self.curActionDelta = 0
		self.lastDetectTime = 0
		self.detectState = "NORMAL"
		self.detectCache = None


	def check(self,motions):
		motion,isCover = motions[0],motions[1]
		# print(motion,isCover)
		if motion == "PUSH":
			self.lastScale = self.IO.get_stable_scale()

			if self.cart.getStartWeight() is None:
				self.cart.setStartWeight(self.lastScale)

			if self.detectState == "PULL_CHECKING":
				self.detectState = "NORMAL"

			if self.index == 0:
				print("this push scale is: ",self.lastScale)

		elif motion == "PULL":
			self.lastPullVal = self.IO.get_stable_scale()
		else:
			# if not isCover:
			# 	self.handOutVal = self.IO.get_stable_scale()
			# 	if self.detectState == "PULL_CHECKING":
			# 		delta = self.handOutVal - self.lastScale
			# 		if delta < -(self.curActionDelta/2):
			# 			_id = self.detectCache[0]["id"]
			# 			# for i in range(self.detectCache[0]["fetch_num"]):
			# 				# self.cart.add_item(_id,self.lastDetectTime)
			# 			self.cart.add_item(_id,self.lastDetectTime)
			# 			self.detectState = "NORMAL"
			# 		else:
			# 			if self.index == 0:
			# 				print("current handOutVal: ",self.handOutVal)
			# 				print("last scale is: ",self.lastScale)
			# 				print("                                              ")
			# else:
			# 	current = self.IO.get_stable_scale()
			# 	if self.detectState == "PUSH_CHECKING":
			# 		if self.handInVal - self.handOutVal > (self.curActionDelta/2):
			# 			print("push_checking in back success!!")
			# 			_id = self.detectCache[0]["id"]

			# 			# for i in range(self.detectCache[0]["fetch_num"]):
			# 				# self.cart.remove_item(_id,self.lastDetectTime)
			# 			self.cart.remove_item(_id,self.lastDetectTime)
			# 			self.detectState = "NORMAL"
			# 			self.lastScale = self.handOutVal+ self.curActionDelta

			current = self.IO.get_stable_scale()

			delta = current - self.lastScale
			
			if self.detectState == "PULL_CHECKING":
				
				if delta < -(self.curActionDelta/2):
					_id = self.detectCache[0]["id"]
					# for i in range(self.detectCache[0]["fetch_num"]):
						# self.cart.add_item(_id,self.lastDetectTime)
					self.cart.add_item(_id,self.lastDetectTime)
					self.detectState = "NORMAL"
				# else:
				# 	if self.index == 0:
				# 		print("current handOutVal: ",self.handOutVal)
				# 		print("last scale is: ",self.lastScale)
				# 		print("                                              ")
			
			if self.detectState == "PUSH_CHECKING":
				if delta > (self.curActionDelta/2):
					print("push_checking in back success!!")
					_id = self.detectCache[0]["id"]

					# for i in range(self.detectCache[0]["fetch_num"]):
						# self.cart.remove_item(_id,self.lastDetectTime)
					self.cart.remove_item(_id,self.lastDetectTime)
					self.detectState = "NORMAL"
					self.lastScale = current+ self.curActionDelta


	#two judge will not interfere with each other
	def detect_check(self,detectResults):
		detect = detectResults.getDetect()

		if len(detect) > 0:
			direction = detect[0]["direction"]

			self.lastDetectTime = detectResults.getMotionTime("PUSH" if direction is "IN" else "PULL")

			# print(detect)
			# print("action time is: ",self.lastDetectTime)

			_id = detect[0]["id"]

			if settings.items[_id]['name'] == "empty_hand":
				print("check empty hand take out")
				detectResults.resetDetect()
				return

			if direction == "OUT":
				self.detectState = "PULL_CHECKING"
			else:
				self.detectState = "PUSH_CHECKING"

			self.curActionDelta = settings.items[_id]['weight']

			self.detectCache = detect
			detectResults.resetDetect()
			detectResults.setActionTime()


