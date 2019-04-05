# coding=utf-8
from __future__ import absolute_import

import time
from math import sqrt
from octoprint_BLTouchSoftware.MeshLevelingParameter import MeshLevelingState, Parameter, AXIS
from octoprint_BLTouchSoftware.BLTouchGPIO import BLTouchGPIO, BLTouchState


class BedLevelingv2:

	def __init__(self, logger):
		self.__logger = logger

		self.prev_position = None
		self.current_position = None
		self.relative = False

	def printlog(self, log, level="INFO"):
		if self.__logger is None:
			return
		if level == "INFO":
			self.__logger.info(log)
		elif level == "DEBUG":
			self.__logger.debug(log)

	def set_current_pos(self, px, py, pz):
		if self.prev_position is None:
			self.prev_position = [0, 0, 0]
		else:
			self.prev_position = self.current_position

		if self.relative:
			if px:
				x = self.prev_position[AXIS.X_AXIS] + float(px)
			else:
				x = self.prev_position[AXIS.X_AXIS]
			if py:
				y = self.prev_position[AXIS.Y_AXIS] + float(py)
			else:
				y = self.prev_position[AXIS.Y_AXIS]
			if pz:
				z = self.prev_position[AXIS.Z_AXIS] + float(pz)
			else:
				z = self.prev_position[AXIS.Z_AXIS]
		else:
			if px is None:
				x = self.prev_position[AXIS.X_AXIS]
			else:
				x = px
			if py is None:
				y = self.prev_position[AXIS.Y_AXIS]
			else:
				y = py
			if pz is None:
				z = self.prev_position[AXIS.Z_AXIS]
			else:
				z = pz
		self.current_position = [float(x), float(y), float(z)]
