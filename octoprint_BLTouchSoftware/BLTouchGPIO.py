# coding=utf-8
from __future__ import absolute_import
#  import RPi.GPIO as GPIO


# define for bltouch status
class BLTouchState():
	BLTOUCH_DEPLOY = 10
	BLTOUCH_STOW = 90
	BLTOUCH_SELFTEST = 120
	BLTOUCH_RESET = 160


# https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/
class BLTouchGPIO:
	trigger = False

	def __init__(self):
		self.trigger = False

	def reset(self, mode=BLTouchState.BLTOUCH_STOW):
		self.trigger = False
		self.probeMode(mode)
		# TODO: self check
		pass

	def probeMode(self, mode=BLTouchState.BLTOUCH_STOW):
		# TODO: probe UP or Down for testing
		pass

	def callback(self):
		self.trigger = True
