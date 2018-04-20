import time
import os

class Logger:
  def __init__(self,mode="develop"):
    self.logMode = mode
    self.print_io_list=[]
    self.openDoorTime = self.getTime()
    self.io_prefix = "/home/votance/Projects/Output/"
    self.saveVideoLog = (self.logMode == "produce")

    self.io_path=""

  def checkSaveVideo(self):
    return self.saveVideoLog

  def getSaveVideoPath(self):
      return self.io_path

  def debug(self,message):
    msg = self.getTime()+" [DEBUG] "+message
    self.addInfo(msg)
  
  def info(self,message):
    msg = self.getTime()+" [INFO] "+message
    self.addInfo(msg)

  def warning(self,message):
    msg = self.getTime()+" [WARN] "+message
    self.addInfo(msg)

  # def warn(self,message):
  #   self.logger.warn(message)

  # def error(self,message):
  #   self.logger.error(message)

  def evokeDoorOpen(self):
    self.print_io_list=[]
    if self.logMode == "develop":
      return

    day = time.strftime('%Y-%m-%d/',time.localtime(time.time()))
    minutes = time.strftime('%H_%M_%S/',time.localtime(time.time()))
    self.io_path = self.io_prefix + day + minutes
    # if not os.path.exists(self.io_path):
        # print(self.io_path)
        # os.makedirs(self.io_path)

    # self.io_path += minutes

    if not os.path.exists(self.io_path):
        # print(self.io_path)
        os.makedirs(self.io_path)

  def evokeDoorClose(self):
    if self.logMode == "produce":
      hour = time.strftime('%H_%M_%S', time.localtime(time.time()))
      self.io_path += hour+".log"
      with open(self.io_path,"w+") as file:
        for log in self.print_io_list:
          file.write(log+"\n")
      file.close()
      self.print_io_list=[]


  def getTime(self):
    return time.strftime('[%Y-%m-%d] [%H:%M:%S]', time.localtime(time.time()))

  def addInfo(self,message):
    if self.logMode == "develop":
      print(message)
    else:
      self.print_io_list.append(message)