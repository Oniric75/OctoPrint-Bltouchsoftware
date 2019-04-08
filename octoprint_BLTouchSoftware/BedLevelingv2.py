# coding=utf-8
from __future__ import absolute_import

import time
from math import sqrt
from octoprint_BLTouchSoftware.MeshLevelingParameter import MeshLevelingState, Parameter, AXIS
from octoprint_BLTouchSoftware.BLTouchGPIO import BLTouchGPIO, BLTouchState


class BedLevelingv2:

	def __init__(self):

		self.__logger = None
		self.printer = None

		self.prev_position = None  # used to store the previous position (in case of relative move)
		self.current_position = None  # used to store the current position
		self.relative = False  # used to know if we are currently doing a relative move or not

		self.index_to_xpos = None  # [grid_max_points_x] : list of x position for each probe x point
		self.index_to_ypos = None  # [grid_max_points_y] : list of x position for each probe y point

		self.grid_points = 0  # number of probing point: calculated from grid_point x & y

		self.z_values = None  # [grid_max_point_x][grid_max_point_y]
		self.available = False  # used to know if a map is available

		self.state = MeshLevelingState.MeshStart
		self.sleepTime = 0
		self.zigzag_increase = True
		self._zigzag_x_index = -1
		self._zigzag_y_index = 0
		self.probe_index = 0
		# self.realz = 0
		self.first_run = True

		self.bltouch = BLTouchGPIO(self)

	def setlogger(self, logger):
		self.__logger = logger
		self.bltouch.setlogger(logger)

	def setprinter(self, printer):
		self.printer = printer

	def printlog(self, log, level="INFO"):
		if self.__logger is None:
			return
		if level == "INFO":
			self.__logger.info(log)
		elif level == "DEBUG":
			self.__logger.debug(log)

	# used to store the head position in the array
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

	# used when the settings are updated to reset the  probing map
	def set_mesh_dist(self, grid_max_points_x, grid_max_points_y):
		self.printlog('Init Probing map')
		Parameter.grid_max_points_x = int(grid_max_points_x)
		Parameter.grid_max_points_y = int(grid_max_points_y)
		self.grid_points = Parameter.grid_max_points_x * Parameter.grid_max_points_y
		# define MESH_X_DIST ((MESH_MAX_X - (MESH_MIN_X)) / (GRID_MAX_POINTS_X - 1))
		Parameter.mesh_x_dist = (
				(Parameter.max_x - Parameter.min_x) / (int(grid_max_points_x) - 1))

		# define MESH_Y_DIST ((MESH_MAX_Y - (MESH_MIN_Y)) /  (GRID_MAX_POINTS_Y - 1))
		Parameter.mesh_y_dist = (
				(Parameter.max_y - Parameter.min_y) / (int(grid_max_points_y) - 1))

		self.index_to_xpos = []
		for x in range(int(grid_max_points_x)):
			px = int(Parameter.min_x + x * Parameter.mesh_x_dist)
			if Parameter.max_x - px < Parameter.X_PROBE_OFFSET_FROM_EXTRUDER:
				px = Parameter.max_x - Parameter.X_PROBE_OFFSET_FROM_EXTRUDER - 1
			self.index_to_xpos.append(px)

		self.index_to_ypos = []
		for y in range(int(grid_max_points_y)):
			py = int(Parameter.min_y + y * Parameter.mesh_y_dist)
			if Parameter.max_y - py < Parameter.Y_PROBE_OFFSET_FROM_EXTRUDER:
				py = Parameter.max_y - Parameter.Y_PROBE_OFFSET_FROM_EXTRUDER - 1
			self.index_to_ypos.append(py)
		self.reset()
		self.printlog(self.index_to_xpos)
		self.printlog(self.index_to_ypos)

	# reset all the leveling
	def reset(self):
		self.state = MeshLevelingState.MeshStart
		self.sleepTime = 0
		self.zigzag_increase = True
		self._zigzag_x_index = -1
		self._zigzag_y_index = 0
		self.probe_index = 0
		Parameter.realz = 0
		self.first_run = True
		self.z_values = None
		self.z_values = [[0 for y in range(Parameter.grid_max_points_y)] for x in
						 range(Parameter.grid_max_points_x)]
		self.available = False

	#  move the head on z using previous position.
	#  could be replaced using relative ?
	#  Named based on marlin
	def do_blocking_move_to_z(self, pz, relative=False, speed=None):
		if speed is None:
			speed = Parameter.HOMING_FEEDRATE_XY
		if relative:
			self.do_blocking_move_to(0, 0, pz, relative, speed)
		else:
			self.do_blocking_move_to(self.current_position[AXIS.X_AXIS],
									 self.current_position[AXIS.Y_AXIS],
									 pz, relative, speed)

	#  move the head on x y z. Named based on marlin
	def do_blocking_move_to(self, px, py, pz, relative=False, speed=None):
		axes = {}
		#  return "G0 E0 F%d X%d Y%d Z%d" % (BedLeveling.HOMING_FEEDRATE_XY, px, py, pz)
		if speed is None:
			speed = Parameter.HOMING_FEEDRATE_XY
		if relative:
			dist = abs(px) + abs(py) + abs(pz)
			if px != 0:
				axes["x"] = px
			if py != 0:
				axes["y"] = py
			if pz != 0:
				axes["z"] = pz
		else:
			dist = sqrt((px - self.prev_position[AXIS.X_AXIS]) ** 2 +
						(py - self.prev_position[AXIS.Y_AXIS]) ** 2 +
						(pz - self.prev_position[AXIS.Z_AXIS]) ** 2)
			axes["x"] = px
			axes["y"] = py
			axes["z"] = pz

		self.printer.jog(axes, relative, speed)
		self.sleepTime = dist * Parameter.WAIT_FACTOR / float(speed)

	#  used to move the head in a zigzag instead of going back to 0 every time
	def zigzag(self, pz):
		if self.zigzag_increase:
			self._zigzag_x_index += 1
			if self._zigzag_x_index >= Parameter.grid_max_points_x:
				self._zigzag_x_index -= 1
				self._zigzag_y_index += 1
				self.zigzag_increase = False
		else:
			self._zigzag_x_index -= 1
			if self._zigzag_x_index < 0:
				self._zigzag_x_index += 1
				self._zigzag_y_index += 1
				self.zigzag_increase = True

		self.do_blocking_move_to(
			self.index_to_xpos[self._zigzag_x_index] + Parameter.X_PROBE_OFFSET_FROM_EXTRUDER,
			self.index_to_ypos[self._zigzag_y_index] + Parameter.Y_PROBE_OFFSET_FROM_EXTRUDER,
			pz)

	def g29v2(self):
		# Error Handling
		if Parameter.realz <= -2:
			self.printlog("realZ <= -2 ... Erreur? stop process")
			self.bltouch.reset(BLTouchState.BLTOUCH_STOW)
			Parameter.levelingActive = False
			Parameter.levelingHome = False
			self.printlog(self.z_values)
			return

		# todo : improve this part. make sure the sleep is right ... maybe the g29 should be threaded ?
		# wait for the move to be done ...
		if self.sleepTime > 10:
			self.printlog("sleep 8...")
			time.sleep(8)
		elif self.sleepTime < 1:
			self.printlog("sleep 1...")
			time.sleep(0.8)
		else:
			self.printlog("sleep %f..." % self.sleepTime)
			time.sleep(self.sleepTime)
		self.printlog("Sleep OVER")


		# Init : first time the g29 function is called
		if self.state == MeshLevelingState.MeshStart:
			self.reset()
			Parameter.levelingHome = True

			self.printer.commands(["G28"])
			self.state = MeshLevelingState.MeshNext
		# self.do_m114(True)
		elif self.state == MeshLevelingState.MeshNext:
			self.printlog("MeshNext")
			Parameter.levelingActive = True
			if self.probe_index >= Parameter.grid_max_points_x * Parameter.grid_max_points_y:  # End
				self.bltouch.reset(BLTouchState.BLTOUCH_STOW)
				Parameter.levelingActive = False
				Parameter.levelingHome = False
				self.available = True
				self.printlog(self.z_values)
				self.printlog("The end!")
				return
			if self.first_run:  # set the head in position
				self.first_run = False
				self.do_blocking_move_to_z(Parameter.Z_CLEARANCE_DEPLOY_PROBE)
				self.zigzag(Parameter.Z_CLEARANCE_DEPLOY_PROBE)  # Move close to the bed
				Parameter.realz = Parameter.Z_CLEARANCE_DEPLOY_PROBE
				self.do_m114()
				self.printlog("Init!")
			else:  # the head is in position, start fast probing
				if self.current_position[AXIS.Z_AXIS] == Parameter.Z_CLEARANCE_DEPLOY_PROBE:
					self.printlog("start fast probing")
					self.bltouch.reset(BLTouchState.BLTOUCH_DEPLOY)
				if not self.bltouch.trigger:  # the probe didnt touch the bed
					self.printlog("Go Down FAST: M114z=%f, realZ:%f" % (
						self.current_position[AXIS.Z_AXIS], Parameter.realz))
					Parameter.realz -= 0.5
					self.do_blocking_move_to_z(-0.5, True)
					self.do_m114()
				else:  # bltouch touch bed.
					Parameter.realz += 1
					self.bltouch.trigger = False
					self.state = MeshLevelingState.MeshProbe
					self.first_run = True
					self.do_blocking_move_to_z(1, True)
					self.do_m114()
		elif self.state == MeshLevelingState.MeshProbe:  # slow probing
			if self.first_run:
				self.printlog("curZ=%f, prevZ=%f, RealZ=%f" % (
					self.current_position[AXIS.Z_AXIS], self.prev_position[AXIS.Z_AXIS],
					Parameter.realz))
				self.bltouch.reset(BLTouchState.BLTOUCH_DEPLOY)
				self.first_run = False
				self.printlog("start slow probing")
			if not self.bltouch.trigger:
				Parameter.realz -= 0.1
				self.printlog("Go Down SlOW: M114z=%f, realZ:%f" % (
					self.current_position[AXIS.Z_AXIS], Parameter.realz))
				self.do_blocking_move_to_z(-0.1, True)
				self.do_m114()
			else:  # bltouch touch bed again.
				self.state = MeshLevelingState.MeshNext
				self.first_run = True
				self.probe_index += 1
				self.bltouch.trigger = False
				self.printlog("index: %d | X:%f, Y:%f; Z:%f, RealZ:%f" % (
					self.probe_index - 1, self.current_position[0], self.current_position[1],
					self.current_position[2], Parameter.realz))

				self.set_z(self._zigzag_x_index, self._zigzag_y_index,
						   Parameter.realz + Parameter.Z_PROBE_OFFSET_FROM_EXTRUDER)
				self.do_m114()
				self.bltouch.reset(BLTouchState.BLTOUCH_STOW)

	def do_m114(self):
		self.printer.commands("M114")

	def set_z(self, px, py, z):
		if self.z_values is None:
			self.printlog("ERROR SHOULD NOT HAPPENNED, CALL reset before")
		self.z_values[px][py] = z

	#  Using mesh map build with g29 to improve Z accuracy
	#  Based on marlin : mesh_bed_leveling.h line 94 to 115
	@staticmethod
	def constrain(val, min_val, max_val):
		return min(max_val, max(min_val, val))

	@staticmethod
	def cell_index_x(x):
		cx = (float(x) - Parameter.min_x) * (1.0 / Parameter.mesh_x_dist)
		return int(BedLevelingv2.constrain(cx, 0, Parameter.grid_max_points_x - 2))

	@staticmethod
	def cell_index_y(y):
		cy = (float(y) - Parameter.min_y) * (1.0 / Parameter.mesh_y_dist)
		return int(BedLevelingv2.constrain(cy, 0, Parameter.grid_max_points_y - 2))

	@staticmethod
	def calc_z0(a0, a1, z1, a2, z2):
		delta_z = (1.0 * (z2 - z1)) / (a2 - a1)
		delta_a = float(a0) - float(a1)
		return z1 + delta_a * delta_z

	def get_z(self, x0, y0):
		cx = self.cell_index_x(x0)
		cy = self.cell_index_y(y0)

		z1 = BedLevelingv2.calc_z0(x0,
								   self.index_to_xpos[cx],
								   self.z_values[cx][cy],
								   self.index_to_xpos[cx + 1],
								   self.z_values[cx + 1][cy])
		z2 = BedLevelingv2.calc_z0(x0,
								   self.index_to_xpos[cx],
								   self.z_values[cx][cy + 1],
								   self.index_to_xpos[cx + 1],
								   self.z_values[cx + 1][cy + 1])

		z0 = BedLevelingv2.calc_z0(y0,
								   self.index_to_ypos[cy],
								   z1,
								   self.index_to_ypos[cy + 1],
								   z2)

		return z0
