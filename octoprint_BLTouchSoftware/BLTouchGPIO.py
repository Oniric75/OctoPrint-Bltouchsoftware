# coding=utf-8
from __future__ import absolute_import
import RPi.GPIO as GPIO
from octoprint_BLTouchSoftware.MeshLevelingParameter import Parameter
import inspect
import time

# define for bltouch status
class BLTouchState:
	BLTOUCH_DEPLOY = 10
	BLTOUCH_STOW = 90
	BLTOUCH_SELFTEST = 120
	BLTOUCH_RESET = 160


# https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/
class BLTouchGPIO:

	def __init__(self, bedlevelinginstance):
		self.GPIO_BLTouch_Zmin = 11
		self.GPIO_BLTouch_Control = 12
		self.GPIO_Alfawise_Zmin = 13
		self.GPIO_Switch_Zmin = 16
		self.count = 0
		self.bedlevelingInstance = bedlevelinginstance
		self.trigger = False

		GPIO.cleanup()
		GPIO.setmode(GPIO.BOARD)

		# callback_bltouch_zmin when bltouch touch the bed
		GPIO.setup(self.GPIO_BLTouch_Zmin, GPIO.IN)
		GPIO.add_event_detect(self.GPIO_BLTouch_Zmin, GPIO.RISING, callback=self.callback_bltouch_zmin, bouncetime=50)

		# callback_bltouch_zmin when the zswitch is trigger
		GPIO.setup(self.GPIO_Switch_Zmin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.add_event_detect(self.GPIO_Switch_Zmin, GPIO.BOTH, callback=self.callback_switch_zmin, bouncetime=50)

		# send zmin to printer
		GPIO.setup(self.GPIO_Alfawise_Zmin, GPIO.OUT, initial=GPIO.LOW)


		# control of bltouch
		GPIO.setup(self.GPIO_BLTouch_Control, GPIO.OUT)
		self.bltouch = GPIO.PWM(self.GPIO_BLTouch_Control, 50)
		self.bltouch.start(0)
		self._logger = None

	def setlogger(self, logger):
		self._logger = logger

	def printlog(self, log, level="INFO"):
		if self._logger is None:
			return
		if level == "INFO":
			self._logger.info(log)
		elif level == "DEBUG":
			self._logger.debug(log)

	def _setmode(self, PW=1475):
		GPIO.output(self.GPIO_BLTouch_Control, True)
		duty = (PW / (0.02 * 1000 * 1000)) * 100
		self.bltouch.ChangeDutyCycle(duty)
		time.sleep(1)
		GPIO.output(self.GPIO_BLTouch_Control, False)

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
		self.probemode(BLTouchState.BLTOUCH_RESET)
		time.sleep(0.5)
		self.count = 0
		self.probemode(mode)



	def probemode(self, mode=BLTouchState.BLTOUCH_STOW):
		if mode == BLTouchState.BLTOUCH_DEPLOY:
			self.printlog("BLTOUCH mode change DEPLOY")
			self._setmode(650)
		elif mode == BLTouchState.BLTOUCH_STOW:
			self.printlog("BLTOUCH mode change STOW")
			self._setmode(1475)
		elif mode == BLTouchState.BLTOUCH_SELFTEST:
			self.printlog("BLTOUCH mode change SELFTEST")
			self._setmode(1780)
		elif mode == BLTouchState.BLTOUCH_RESET:
			self.printlog("BLTOUCH mode change RESET")
			self._setmode(2190)

	def callback_bltouch_zmin(self, channel):
		time.sleep(0.001)
		if GPIO.input(channel):
			if Parameter.levelingHome:
				self.printlog("BLTOUCH count %i" % self.count)
				self.count += 1
				if self.count >= 2:
					self.printlog("BLTOUCH HOME TRIGGER x2! channel=%s" % channel)
					self.send_zmin_to_printer(True)
					time.sleep(0.005)
					self.send_zmin_to_printer(False)
					self.count = 0
					Parameter.realz = Parameter.Z_PROBE_OFFSET_FROM_EXTRUDER
					Parameter.levelingHome = False
					self.bedlevelingInstance.g29v2()
					return
			elif Parameter.levelingActive:
				self.trigger = True
				self.printlog("BLTOUCH TRIGGER Leveling! channel=%s" % channel)
				return
			self.printlog("BLTOUCH TRIGGER! channel=%s" % channel)
			self.send_zmin_to_printer(True)
			time.sleep(0.005)
			self.send_zmin_to_printer(False)

		else:
			# self.printlog("BLTOUCH TRIGGER END! channel=%s" % channel)
			self.send_zmin_to_printer(False)

	def callback_switch_zmin(self, channel):
		time.sleep(0.001)
		if not GPIO.input(channel) and Parameter.safe_mode:
			self.printlog("SWITCH TRIGGER SAFE MODE! channel=%s" % channel)
			self.send_zmin_to_printer(True)
		elif Parameter.safe_mode:
			self.printlog("SWITCH END TRIGGER SAFE MODE! channel=%s" % channel)
			self.send_zmin_to_printer(False)

	def send_zmin_to_printer(self, status):
		#  used for the g28 at the begining of the g29
		if status:
			GPIO.output(self.GPIO_Alfawise_Zmin, GPIO.HIGH)
		else:
			GPIO.output(self.GPIO_Alfawise_Zmin, GPIO.LOW)

	def cleanup(self):
		self.bltouch.stop()
		self.bltouch.cleanup()
		GPIO.remove_event_detect(self.GPIO_BLTouch_Zmin)
		pass
