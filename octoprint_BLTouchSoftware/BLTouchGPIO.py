#  import RPi.GPIO as GPIO

class BLTouchGPIO:
	trigger = False

	def __init__(self):
		self.trigger = False

	def reset(self):
		self.trigger = False
		# TODO: self check
		pass

	def probeMode(self, mode="UP"):
		# TODO: probe UP or Down for testing
		pass
