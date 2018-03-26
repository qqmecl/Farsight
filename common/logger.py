import time
import logging

class Logger(object):
	def __init__(self, dev = False, time = time.localtime()):
		self.log =  logging.getLogger('farsight')
		self.log.setLevel(logging.INFO)
		self.logger = logging.getLogger(path)
		fmt1 = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
		fmt2 = logging.Formatter('%(levelname)s - %(message)s')
   		#设置CMD日志
   		sh = logging.StreamHandler()
   		sh.setFormatter(fmt1)
   		sh.setLevel(logging.INFO)
   		#设置文件日志
   		xx = time.strftime('%Y/%m/%d', time)
   		yy = time.strftime('%H:%M:%S', time)
   		self.fh = logging.FileHandler('Output/' + xx + '/' + yy + '/' + yy + '.log')
   		self.fh.setFormatter(fmt2)
   		self.fh.setLevel(logging.INFO)
   		
   		if dev:
   			self.logger.addHandler(sh)
   		else:
   			self.logger.addHandler(fh)
  
  	def debug(self,message):
   		self.logger.debug(message)
  
  	def info(self,message):
   		self.logger.info(message)
  
  	def war(self,message):
   		self.logger.warn(message)
  
  	def error(self,message):
   		self.logger.error(message)
  
  	def cri(self,message):
   		self.logger.critical(message)