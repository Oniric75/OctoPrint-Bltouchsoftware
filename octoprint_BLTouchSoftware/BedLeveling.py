# coding=utf-8
from __future__ import absolute_import

import time
from math import sqrt
from MeshLevelingState import MeshLevelingState
from BLTouchGPIO import BLTouchGPIO, BLTouchState


# noinspection PyClassHasNoInit
class BedLeveling:
	index_to_xpos = None  # [grid_max_points_x] : list of x position for each probe x point
	index_to_ypos = None  # [grid_max_points_y] : list of x position for each probe y point
	current_position = None
	prev_position = None
	min_x = 0
	min_y = 0
	min_z = 0
	max_x = 0
	max_y = 0
	max_z = 0
	grid_max_points_x = 0  # number of probe grid x. DEFAULT : 3
	grid_max_points_y = 0  # number of probe grid y. DEFAULT : 3
	grid_points = 0  # number of points into the grid:  grid_max_points_x * grid_max_points_y
	mesh_x_dist = 0
	mesh_y_dist = 0
	realz = -1  # keep track of the z home reference
	z_offset = 0
	z_values = None  # [grid_max_point_x][grid_max_point_y]

	state = MeshLevelingState.MeshStart
	_zigzag_x_index = -1
	_zigzag_y_index = -1
	probe_index = -1
	active = False  # used to know if we are currently doing a bed leveling
	first_run = True  # used to know if it's the first time into the g29 or not
	__logger = None
	printer = None
	bltouch = BLTouchGPIO()
	# ~~ CONSTANT

	X_AXIS = 0  # index for X_AXIS: used for Marlin clearness
	Y_AXIS = 1  # index for Y_AXIS: used for Marlin clearness
	Z_AXIS = 2  # index for Z_AXIS: used for Marlin clearness
	BLTOUCH_DELAY = 375
	MULTIPLE_PROBING = 2  # The number of probes to perform at each point.

	# SPEED
	XY_PROBE_SPEED = 8000  # X and Y axis travel speed(mm / m) between	probes
	HOMING_FEEDRATE_Z = 4 * 60  # Z Homing speeds (mm/m)
	HOMING_FEEDRATE_XY = 50 * 60  # X & Y Homing speeds (mm/m)
	Z_PROBE_SPEED_FAST = HOMING_FEEDRATE_Z  # Feedrate(mm / m)	for the first approach when double-probing
	Z_PROBE_SPEED_SLOW = Z_PROBE_SPEED_FAST / 2  # Feedrate(mm / m)	for the "accurate" probe of each point
	WAIT_FACTOR = 800

	# PROBE (TODO: available in advanced settings)
	Z_CLEARANCE_DEPLOY_PROBE = 10  # Z Clearance for Deploy/Stow
	X_PROBE_OFFSET_FROM_EXTRUDER = 10  # X offset: -left  +right  [of the nozzle]
	Y_PROBE_OFFSET_FROM_EXTRUDER = 10  # Y offset: -front +behind [the nozzle]
	Z_PROBE_OFFSET_FROM_EXTRUDER = 0  # Z offset: -below +above  [the nozzle]
	MIN_PROBE_EDGE = 10  # Certain types of probes need to stay away from edges

	#  ~~  INTERNAL USE
	@staticmethod
	def set_logger(logger):
		if logger is not None:
			BedLeveling.__logger = logger

	@staticmethod
	def printlog(log, level="INFO"):
		if BedLeveling.__logger is None:
			return
		if level == "INFO":
			BedLeveling.__logger.info(log)
		elif level == "DEBUG":
			BedLeveling.__logger.debug(log)

	@staticmethod
	def set_current_pos(px, py, pz):
		if BedLeveling.prev_position is None:
			BedLeveling.prev_position = [0, 0, 0]
		else:
			BedLeveling.prev_position = BedLeveling.current_position
		BedLeveling.current_position = [px, py, pz]

	# ~~  BLTOUCH Software

	# Use for bed leveling
	@staticmethod
	def set_z_offset(pz):
		BedLeveling.z_offset = pz

	@staticmethod
	def set_z(px, py, z):
		if BedLeveling.z_values is None:
			BedLeveling.reset()
		BedLeveling.z_values[px][py] = z

	@staticmethod
	def set_zigzag_z(index, z):
		print(index)
		print(z)

	@staticmethod
	def set_mesh_dist(grid_max_points_x, grid_max_points_y):
		BedLeveling.printlog('Init Probing map')
		BedLeveling.grid_max_points_x = int(grid_max_points_x)
		BedLeveling.grid_max_points_y = int(grid_max_points_y)
		BedLeveling.grid_points = BedLeveling.grid_max_points_x * BedLeveling.grid_max_points_y
		# define MESH_X_DIST ((MESH_MAX_X - (MESH_MIN_X)) / (GRID_MAX_POINTS_X - 1))
		BedLeveling.mesh_x_dist = (
				(BedLeveling.max_x - BedLeveling.min_x) / int(grid_max_points_x) - 1)

		# define MESH_Y_DIST ((MESH_MAX_Y - (MESH_MIN_Y)) / (GRID_MAX_POINTS_Y - 1))
		BedLeveling.mesh_y_dist = (
				(BedLeveling.max_y - BedLeveling.min_y) / int(grid_max_points_y) - 1)

		BedLeveling.index_to_xpos = []
		for x in range(int(grid_max_points_x)):
			BedLeveling.index_to_xpos.append(int(BedLeveling.min_x + x * BedLeveling.mesh_x_dist))

		BedLeveling.index_to_ypos = []
		for y in range(int(grid_max_points_y)):
			BedLeveling.index_to_ypos.append(int(BedLeveling.min_y + y * BedLeveling.mesh_y_dist))
		BedLeveling._z_offset = 0
		BedLeveling.reset()
		BedLeveling.printlog(BedLeveling.index_to_xpos)
		BedLeveling.printlog(BedLeveling.index_to_ypos)

	# noinspection PyUnusedLocal
	@staticmethod
	def reset():
		BedLeveling.state = MeshLevelingState.MeshStart
		BedLeveling._zigzag_x_index = 0
		BedLeveling._zigzag_y_index = 0
		BedLeveling.probe_index = 0
		BedLeveling.realz = 0
		BedLeveling.first_run = True
		BedLeveling.z_values = None
		BedLeveling.z_values = [[0 for y in range(BedLeveling.grid_max_points_y)] for x in
								range(BedLeveling.grid_max_points_x)]

	#	if BedLeveling.bltouch is not None:
	#		BedLeveling.bltouch.cleanup()
	#	bltouch = BLTouchGPIO()


	@staticmethod
	def do_blocking_move_to_z(pz, relative=False, speed=None):
		if speed is None:
			speed = BedLeveling.HOMING_FEEDRATE_XY
		if relative:
			BedLeveling.do_blocking_move_to(0, 0, pz, relative, speed)
		else:
			BedLeveling.do_blocking_move_to(BedLeveling.current_position[BedLeveling.X_AXIS],
											BedLeveling.current_position[BedLeveling.Y_AXIS],
											pz, relative, speed)

	@staticmethod
	def do_blocking_move_to(px, py, pz, relative=False, speed=None):
		axes = {}
		#  return "G0 E0 F%d X%d Y%d Z%d" % (BedLeveling.HOMING_FEEDRATE_XY, px, py, pz)
		if speed is None:
			speed = BedLeveling.HOMING_FEEDRATE_XY
		if relative:
			dist = abs(px) + abs(py) + abs(pz)
			if px != 0:
				axes["x"] = px
			if py != 0:
				axes["y"] = py
			if pz != 0:
				axes["z"] = pz
		else:
			dist = sqrt((px - BedLeveling.prev_position[BedLeveling.X_AXIS]) ** 2 +
						(py - BedLeveling.prev_position[BedLeveling.Y_AXIS]) ** 2 +
						(pz - BedLeveling.prev_position[BedLeveling.Z_AXIS]) ** 2)
			axes["x"] = px
			axes["y"] = py
			axes["z"] = pz

		BedLeveling.printer.jog(axes, relative, speed)
		time.sleep(dist * BedLeveling.WAIT_FACTOR / float(speed))

	@staticmethod
	def do_m114(home=False):
		if home:
			BedLeveling.printer.commands(["G28", "M114"])
			BedLeveling.bltouch.reset()
		else:
			BedLeveling.printer.commands("M114")

	@staticmethod
	def zigzag(pz):
		BedLeveling._zigzag_x_index = BedLeveling.probe_index % BedLeveling.grid_max_points_x
		BedLeveling._zigzag_y_index = BedLeveling.probe_index / BedLeveling.grid_max_points_x
		if BedLeveling._zigzag_y_index % 2:
			BedLeveling.zigzag_x_index = BedLeveling.grid_max_points_x - 1 - BedLeveling.probe_index
		BedLeveling.printlog("zigX=%d, zigY=%d" % (BedLeveling._zigzag_x_index, BedLeveling._zigzag_y_index))
		BedLeveling.do_blocking_move_to(BedLeveling.index_to_xpos[BedLeveling._zigzag_x_index],
										BedLeveling.index_to_ypos[BedLeveling._zigzag_y_index],
										pz)

	@staticmethod
	def gcode_g29():
		px = 0
		py = 0
		if BedLeveling.state == MeshLevelingState.MeshStart:
			BedLeveling.do_m114(True)
		elif BedLeveling.state == MeshLevelingState.MeshNext:
			if BedLeveling.probe_index > BedLeveling.grid_max_points_x * BedLeveling.grid_max_points_y:  # TODO: corriger le bug du dernier point
				BedLeveling.bltouch.probemode(BLTouchState.BLTOUCH_STOW)
				BedLeveling.active = False
				BedLeveling.printlog("The end!")
				return
			if BedLeveling.first_run:  # move the head to the next position TODO: prendre en compte l'offset du bltouch
				BedLeveling.first_run = False
				BedLeveling.zigzag(5)  # Move close to the bed
				#	BedLeveling.realz = 5
				BedLeveling.bltouch.probemode(BLTouchState.BLTOUCH_DEPLOY)
				BedLeveling.do_m114()
				BedLeveling.printlog("Init!")
			else:  # the head is in position X Y, fast probing
				if not BedLeveling.bltouch.trigger:
					#	BedLeveling.realz -= 1
					BedLeveling.printlog("Go Down: z=%d" % BedLeveling.current_position[BedLeveling.Z_AXIS])
					BedLeveling.do_blocking_move_to_z(-1, True)

					BedLeveling.do_m114()
				else:  # bltouch touch bed.
					#	BedLeveling.realz += 1
					BedLeveling.state = MeshLevelingState.MeshProbe
					BedLeveling.do_blocking_move_to_z(BedLeveling.current_position[BedLeveling.Z_AXIS] + 1)
					BedLeveling.bltouch.reset(BLTouchState.BLTOUCH_DEPLOY)
					BedLeveling.do_m114()
		elif BedLeveling.state == MeshLevelingState.MeshProbe:  # slow probing: TODO : à corriger
			if not BedLeveling.bltouch.trigger:
				#  BedLeveling.realz -= 0.1
				BedLeveling.do_blocking_move_to_z(BedLeveling.current_position[BedLeveling.Z_AXIS] - 0.1)
				BedLeveling.do_m114()
			else:  # bltouch touch bed again.
				BedLeveling.state = MeshLevelingState.MeshNext
				BedLeveling.first_run = True
				BedLeveling.probe_index += 1
			# todo: store Z offset for current X Y
			# BedLeveling.printer.commands(["G28", "M114"])
		elif BedLeveling.state == MeshLevelingState.MeshSet:
			pass
		#  BedLeveling.probe_index += 1
		elif BedLeveling.state == MeshLevelingState.MeshSetZOffset:
			pass
		elif BedLeveling.state == MeshLevelingState.MeshReset:
			BedLeveling.reset()

# inline void gcode_g29() > marlin_main.cpp line 4495
