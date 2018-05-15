# -*- coding: utf-8 -*-
import cv2 as cv

class Shelter(object):
	def __init__(self):
		self.last_frame = None
		self.last_calc = []
		self.last_max_seq = []
		self.warn = 0

	def shadow(self, frame):
		sign = 0
		if self.last_frame is None:
			self.last_frame = frame
			for i in range(10):
				self.last_calc.append(cv.calcHist([frame[48 * i : 48 * (1 + i), :]], [0], None, [32], [0, 256]))
				_, last_max_seq = self.max_num_and_subscript(self.last_calc[i])
				self.last_max_seq.append(last_max_seq)
			return

		now_calc = []
		for i in range(10):
			now_calc.append(cv.calcHist([frame[48 * i : 48 * (1 + i), :]], [0], None, [32], [0, 256]))

		for i in range(10):
			now_max, now_max_seq = self.max_num_and_subscript(now_calc[i])
			if now_max_seq in (self.last_max_seq[i] - 1, self.last_max_seq[i], self.last_max_seq[i] + 1):
				if not now_max_seq:
					if sum(now_calc[i][0: now_max_seq + 1]) > 300:
						sign += 1
				elif now_max_seq // 31:
					if sum(now_calc[i][now_max_seq - 1: 9]) > 300:
						sign += 1
				else:
					if sum(now_calc[i][now_max_seq - 1: now_max_seq + 1]) > 400:
						sign += 1

		if sign > 4:
			self.warn += 1

		if self.warn > 5:
			print('warning warning warning')
		
	def reset(self):
		self.last_frame = None
		self.last_calc = []
		self.last_max_seq = []
		self.warn = 0

	def max_num_and_subscript(self, lst):
		num_max = 0
		seq_max = 0
		for seq, i in enumerate(lst):
			if i > num_max:
				num_max = i
				seq_max = seq
		
		return num_max, seq_max