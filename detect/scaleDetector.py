import common.settings as settings

class ScaleDetector:
	def __init__(self,io,cart):
		self.IO = io
		self.cart = cart

		self.curOut0 = 0

		self.handOutVal = 0
		self.handInVal = 0

		self.curIn0 = 0
		self.curIn1 = 0

		self.lastDetectTime = 0
		self.detectState = "NORMAL"
		self.detectCache = None

	def check(self,motions):
		motion,isCover = motions[0],motions[1]
		# print(motion,isCover)
		if motion == "PUSH":
			self.curOut0 = self.IO.get_stable_scale()
			print("this push scale is: ",self.curOut0)
		elif motion == "PULL":
			self.lastPullVal = self.IO.get_stable_scale()
		else:
			if not isCover:
				self.handOutVal = self.IO.get_stable_scale()

				print("this handout val is: ",self.handOutVal)
				
				if self.detectState == "PULL_CHECKING":
					delta = self.handOutVal-self.curOut0
					if delta < -50:
						# settings.logger.warning('{0} camera shot Take out {1} with num {2}'.format(checkIndex,settings.items[id]["name"], now_num))
						for i in range(self.detectCache[0]["fetch_num"]):
							self.cart.add_item(id)

						self.detectState = "NORMAL"
					else:
						print("scale chane val not enough, so return check!!!",delta)
			else:
				self.handInVal = self.IO.get_stable_scale()

				if self.detectState == "PUSH_CHECKING":
					if self.handInVal - self.handOutVal > 50:
						print("push_checking in back success!!")
						_id = self.detectCache[0]["id"]
						for i in range(self.detectCache[0]["fetch_num"]):
							self.cart.remove_item(_id)

						self.detectState = "NORMAL"

						self.curOut0 = self.handInVal
		# print("In Value is: ",self.handInVal)
		# print("Out Value is: ",self.handOutVal)


	#two judge will not interfere with each other
	def detect_check(self,detectResults,checkIndex):
		detect = detectResults.getDetect()

		if len(detect) > 0:
			print("vision detect: ",checkIndex,detect)

			direction = detect[0]["direction"]
			now_time = detectResults.getMotionTime("PUSH" if direction is "IN" else "PULL")

			intervalTime = now_time - self.lastDetectTime
			if intervalTime < 0.25:
				detectResults.resetDetect()
				return

			id = detect[0]["id"]
			if settings.items[id]['name'] == "empty_hand":
				print("check empty hand take out")
				detectResults.resetDetect()
				return

			self.lastDetectTime = now_time

			if direction == "OUT":
				self.detectState = "PULL_CHECKING"
			else:
				self.detectState = "PUSH_CHECKING"
			
			self.detectCache = detect

			detectResults.resetDetect()
			detectResults.setActionTime()


