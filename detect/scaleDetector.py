class ScaleDetector:
	def __init__(self,io,cart):
		self.IO = io
		self.cart = cart

	    self.firstPushVal = 0
	    self.lastPullVal = 0

	    self.curVal=0

	    self.curOut0 = 0
	    self.curOut1 = 0

	    self.curIn0 = 0
	    self.curIn1 = 0


	def getOrderDict(self):
		return dict(start=self.firstPushVal, final=self.lastPullVal)


	def check(self,motion,val):
		if self.firstPushVal == 0:
			self.firstPushVal = val


		self.curVal = val

