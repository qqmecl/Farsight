import common.settings as settings

class ScaleDetector:
	def __init__(self,io,cart):
		self.IO = io
		self.cart = cart

	    self.firstPushVal = None
	    self.lastPullVal = None

	    self.curOut0 = 0

	    self.handOutVal = 0
	    self.handInVal = 0


	    self.curIn0 = 0
	    self.curIn1 = 0

	    self.lastDetectTime = 0
	    self.detectState = "NORMAL"
	    self.detectCache = None

	def getOrderDict(self):
		return dict(start=self.firstPushVal, final=self.lastPullVal)

	def check(self,motions):
		motion,isCover = motions[0],motions[1]

		if motion == "PUSH":
			if self.firstPushVal is None:
				self.firstPushVal = self.IO.get_stable_scale()

			self.curOut0 = self.IO.get_stable_scale()
		elif motion == "PULL":
			self.lastPullVal = self.IO.get_stable_scale()

			self.detectState = "NORMAL"
		else:
			if not isCover:
				self.handOutVal = self.IO.get_stable_scale()
			else:
	    		self.handInVal = self.IO.get_stable_scale()

	    		if self.detectState == "PUSH_CHECKING":
	    			if self.handInVal - self.handOutVal > 50:
            			_id = self.detectCache[0]["id"]
            			for i in range(self.detectCache[0]["fetch_num"]):
	                    	self.cart.remove_item(_id)

	                    self.curOut0 = self.handInVal


	#two judge will not interfere with each other
	def detect_check(self,detectResults):
		detect = detectResults.getDetect()

        if len(detect) > 0:
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

            now_num = detect[0]["num"]
            
            if direction == "OUT":
            	if self.handOutVal-self.curOut0 >-50:
               		print("scale chane val not enough, so return check!!!",changeVal)
                else:
                	settings.logger.warning('{0} camera shot Take out {1} with num {2}'.format(checkIndex,settings.items[id]["name"], now_num))
                
	                for i in range(detect[0]["fetch_num"]):
	                    self.cart.add_item(id)

	                self.lastDetectTime = now_time
            else:
            	self.detectState = "PUSH_CHECKING"
            	self.detectCache = detect
            	# if self.curOut1-self.curOut0 >-50:
             #   		print("scale chane val not enough, so return check!!!",changeVal)
            
            detectResults.resetDetect()
            detectResults.setActionTime()


