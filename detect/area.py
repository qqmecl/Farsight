# FILTER_BASE_LINE = [[(260.0,-1.0),(366.0,481.0)],[(250.0,-1.0),(320.0,481.0)],
# [(344.0,-1.0),(298.0,481.0)],[(384.0,-1.0),(352.0,481.0)]]

FILTER_BASE_LINE = [[(207.0,-1.0),(275.0,481.0)],[(250.0,-1.0),(320.0,481.0)],
[(344.0,-1.0),(298.0,481.0)],[(384.0,-1.0),(352.0,481.0)]]

LINE_EQUATION = []
for points in FILTER_BASE_LINE:
    k = (points[1][1]-points[0][1])/(points[1][0]-points[0][0])#下斜率
    b = points[1][1]-k*points[1][0]
    LINE_EQUATION.append([k,b])

class AreaCheck:
	def __init__(self,x,y,pos):
	    y = 480-y
	    self.pos = pos
	    self.x=x
	    self.location = y- LINE_EQUATION[pos][0]*x

	#By pass,we mean the outside part
	def passBaseLine(self):
		# return self.x > 290 
		# return True
		if self.pos >1:
			return self.x > 150
		else:
			return self.location < LINE_EQUATION[self.pos][1] - 160