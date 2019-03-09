# coding=utf-8
from __future__ import absolute_import
import RPi.GPIO as GPIO
import time

# define for bltouch status
class BLTouchState:
	BLTOUCH_DEPLOY = 10
	BLTOUCH_STOW = 90
	BLTOUCH_SELFTEST = 120
	BLTOUCH_RESET = 160


# https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/
class BLTouchGPIO:

	def __init__(self):
		self.GPIO_Zmin = 11
		self.GPIO_Control = 12
		self.trigger = False
		GPIO.setmode(GPIO.BOARD)
		GPIO.setup(self.GPIO_Zmin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.add_event_detect(self.GPIO_Zmin, GPIO.RISING, callback=self.callback, bouncetime=200)

		GPIO.setup(self.GPIO_Control, GPIO.OUT)
		self.bltouch = GPIO.PWM(self.GPIO_Control, 50)
		self.bltouch.start(0)

	def _setmode(self, PW=1475):
		GPIO.output(self.GPIO_Control, True)
		duty = PW / (0.02 * 1000 * 1000)
		self.bltouch.ChangeDutyCycle(duty)
		time.sleep(1)
		GPIO.output(self.GPIO_Control, False)

	'''
	def _setangle(self, Angle):
		duty = Angle / 18 + 2
		GPIO.output(self.GPIO_Control, True)
		self.bltouch.ChangeDutyCycle(duty)
		time.sleep(1)
		GPIO.output(self.GPIO_Control, False)
	'''

	def reset(self, mode=BLTouchState.BLTOUCH_STOW):
		self.trigger = False
		self.probemode(mode)
		# TODO: self check

	def probemode(self, mode=BLTouchState.BLTOUCH_STOW):
		self._setangle(mode)

	def callback(self):
		self.trigger = True

	def cleanup(self):
		self.bltouch.stop()
		self.bltouch.cleanup()
		GPIO.remove_event_detect(self.GPIO_Zmin)
		pass
