# coding=utf-8
from __future__ import absolute_import

import time
from math import sqrt
from octoprint_BLTouchSoftware.MeshLevelingParameter import MeshLevelingState, Parameter
from octoprint_BLTouchSoftware.BLTouchGPIO import BLTouchGPIO, BLTouchState


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
	z_values = None  # [grid_max_point_x][grid_max_point_y]
	available = False  # used to know if the mesh map is built and available
	sleepTime = 0
	relative = False
	zigzag_increase = True
	#  safe_mode = False  # set through settings : enable or not the zmin switch from alfawise

	state = MeshLevelingState.MeshStart
	_zigzag_x_index = -1
	_zigzag_y_index = -1
	probe_index = -1
	#  active = False  # used to know if we are currently doing a bed leveling
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

	# PROBE (Set &  TODO: Available in advanced settings)
	Z_CLEARANCE_DEPLOY_PROBE = 8  # Z Clearance for Deploy/Stow
	X_PROBE_OFFSET_FROM_EXTRUDER = 10  # X offset: -left  +right  [of the nozzle]
	Y_PROBE_OFFSET_FROM_EXTRUDER = 10  # Y offset: -front +behind [the nozzle]
	Z_PROBE_OFFSET_FROM_EXTRUDER = 0  # Z offset: -below +above  [the nozzle]
	MIN_PROBE_EDGE = 10  # Certain types of probes need to stay away from edges

	#  ~~  INTERNAL USE
	@staticmethod
	def set_logger(logger):
		if logger is not None:
			BedLeveling.__logger = logger
			BedLeveling.bltouch.setlogger(logger)

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

		if BedLeveling.relative:
			if px:
				x = BedLeveling.prev_position[BedLeveling.X_AXIS] + float(px)
			else:
				x = BedLeveling.prev_position[BedLeveling.X_AXIS]
			if py:
				y = BedLeveling.prev_position[BedLeveling.Y_AXIS] + float(py)
			else:
				y = BedLeveling.prev_position[BedLeveling.Y_AXIS]
			if pz:
				z = BedLeveling.prev_position[BedLeveling.Z_AXIS] + float(pz)
			else:
				z = BedLeveling.prev_position[BedLeveling.Z_AXIS]
		else:
			if px is None:
				x = BedLeveling.prev_position[BedLeveling.X_AXIS]
			else:
				x = px
			if py is None:
				y = BedLeveling.prev_position[BedLeveling.Y_AXIS]
			else:
				y = py
			if pz is None:
				z = BedLeveling.prev_position[BedLeveling.Z_AXIS]
			else:
				z = pz
		BedLeveling.current_position = [float(x), float(y), float(z)]

	# ~~  BLTOUCH Software

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
				(BedLeveling.max_x - BedLeveling.min_x) / (int(grid_max_points_x) - 1))

		# define MESH_Y_DIST ((MESH_MAX_Y - (MESH_MIN_Y)) /  (GRID_MAX_POINTS_Y - 1))
		BedLeveling.mesh_y_dist = (
				(BedLeveling.max_y - BedLeveling.min_y) / (int(grid_max_points_y) - 1))

		BedLeveling.index_to_xpos = []
		for x in range(int(grid_max_points_x)):
			px = int(BedLeveling.min_x + x * BedLeveling.mesh_x_dist)
			if BedLeveling.max_x - px < BedLeveling.X_PROBE_OFFSET_FROM_EXTRUDER:
				px = BedLeveling.max_x - BedLeveling.X_PROBE_OFFSET_FROM_EXTRUDER - 1
			BedLeveling.index_to_xpos.append(px)

		BedLeveling.index_to_ypos = []
		for y in range(int(grid_max_points_y)):
			py = int(BedLeveling.min_y + y * BedLeveling.mesh_y_dist)
			if BedLeveling.max_y - py < BedLeveling.Y_PROBE_OFFSET_FROM_EXTRUDER:
				py = BedLeveling.max_y - BedLeveling.Y_PROBE_OFFSET_FROM_EXTRUDER - 1
			BedLeveling.index_to_ypos.append(py)
		BedLeveling.reset()
		BedLeveling.printlog(BedLeveling.index_to_xpos)
		BedLeveling.printlog(BedLeveling.index_to_ypos)

	# noinspection PyUnusedLocal
	@staticmethod
	def reset():
		BedLeveling.state = MeshLevelingState.MeshStart
		BedLeveling.sleepTime = 0
		BedLeveling.zigzag_increase = True
		BedLeveling._zigzag_x_index = -1
		BedLeveling._zigzag_y_index = 0
		BedLeveling.probe_index = 0
		BedLeveling.realz = 0
		BedLeveling.first_run = True
		BedLeveling.z_values = None
		BedLeveling.z_values = [[0 for y in range(BedLeveling.grid_max_points_y)] for x in
								range(BedLeveling.grid_max_points_x)]
		BedLeveling.available = False
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
		BedLeveling.sleepTime = dist * BedLeveling.WAIT_FACTOR / float(speed)

	# BedLeveling.printlog("sleepTime:%f" % BedLeveling.sleepTime)

	@staticmethod
	def do_m114(home=False):
		if home:
			BedLeveling.bltouch.reset()
			BedLeveling.printer.commands(["G28", "M114"])
		else:
			BedLeveling.printer.commands("M114")

	@staticmethod
	def zigzag(pz):
		if BedLeveling.zigzag_increase:
			BedLeveling._zigzag_x_index += 1
			if BedLeveling._zigzag_x_index >= BedLeveling.grid_max_points_x:
				BedLeveling._zigzag_x_index -= 1
				BedLeveling._zigzag_y_index += 1
				BedLeveling.zigzag_increase = False
		else:
			BedLeveling._zigzag_x_index -= 1
			if BedLeveling._zigzag_x_index < 0:
				BedLeveling._zigzag_x_index += 1
				BedLeveling._zigzag_y_index += 1
				BedLeveling.zigzag_increase = True

		BedLeveling.do_blocking_move_to(
			BedLeveling.index_to_xpos[BedLeveling._zigzag_x_index] + BedLeveling.X_PROBE_OFFSET_FROM_EXTRUDER,
			BedLeveling.index_to_ypos[BedLeveling._zigzag_y_index] + BedLeveling.Y_PROBE_OFFSET_FROM_EXTRUDER,
			pz)


	# inline void gcode_g29() > marlin_main.cpp line 4495
	# alfawise : probleme quand le point est sous le home : alfawise retourne m114 positif au lieu de négatif
	# todo: improve accuracy : do twice the same point and do it again until getting twice the same result
	@staticmethod
	def gcode_g29():
		px = 0
		py = 0

		# Error Handling
		if BedLeveling.realz <= -2:
			BedLeveling.printlog("realZ <= -2 ... Erreur? stop process")
			BedLeveling.bltouch.reset(BLTouchState.BLTOUCH_STOW)
			Parameter.levelingActive = False
			Parameter.levelingHome = False
			BedLeveling.printlog(BedLeveling.z_values)
			BedLeveling.printer.commands(["G28"])
			return

		# todo : improve this part. make sure the sleep is right ... maybe the g29 should be threaded ?
		# wait for the move to be done ...
		if BedLeveling.sleepTime > 2:
			BedLeveling.printlog("sleep 2...")
			time.sleep(2)
		elif BedLeveling.sleepTime < 1:
			BedLeveling.printlog("sleep 0.5...")
			time.sleep(0.5)
		else:
			BedLeveling.printlog("sleep %f..." % BedLeveling.sleepTime)
			time.sleep(BedLeveling.sleepTime)
		BedLeveling.printlog("Sleep OVER")

		if BedLeveling.state == MeshLevelingState.MeshStart:
			Parameter.levelingHome = True
			BedLeveling.do_m114(True)
		elif BedLeveling.state == MeshLevelingState.MeshNext:
			if BedLeveling.probe_index >= BedLeveling.grid_max_points_x * BedLeveling.grid_max_points_y:
				BedLeveling.bltouch.reset(BLTouchState.BLTOUCH_STOW)
				Parameter.levelingActive = False
				Parameter.levelingHome = False
				BedLeveling.available = True
				BedLeveling.printlog(BedLeveling.z_values)
				BedLeveling.printlog("The end!")
				return

			if BedLeveling.first_run:
				BedLeveling.first_run = False
				BedLeveling.do_blocking_move_to_z(BedLeveling.Z_CLEARANCE_DEPLOY_PROBE)
				BedLeveling.zigzag(BedLeveling.Z_CLEARANCE_DEPLOY_PROBE)  # Move close to the bed
				BedLeveling.realz = BedLeveling.Z_CLEARANCE_DEPLOY_PROBE
				BedLeveling.do_m114()
				BedLeveling.printlog("Init!")
			else:  # the head is in position X Y, fast probing
				if BedLeveling.current_position[BedLeveling.Z_AXIS] == BedLeveling.Z_CLEARANCE_DEPLOY_PROBE:
					BedLeveling.printlog("start fast probing")
					BedLeveling.bltouch.reset(BLTouchState.BLTOUCH_DEPLOY)
				if not BedLeveling.bltouch.trigger:
					BedLeveling.printlog("Go Down FAST: M114z=%f, realZ:%f" % (
						BedLeveling.current_position[BedLeveling.Z_AXIS], BedLeveling.realz))
					BedLeveling.realz -= 0.5
					BedLeveling.do_blocking_move_to_z(-0.5, True)
					BedLeveling.do_m114()
				else:  # bltouch touch bed.
					BedLeveling.realz += 1
					BedLeveling.state = MeshLevelingState.MeshProbe
					BedLeveling.first_run = True
					BedLeveling.do_blocking_move_to_z(1, True)
					BedLeveling.do_m114()

		elif BedLeveling.state == MeshLevelingState.MeshProbe:  # slow probing
			if BedLeveling.first_run:
				BedLeveling.printlog("curZ=%f, prevZ=%f, RealZ=%f" % (
					BedLeveling.current_position[BedLeveling.Z_AXIS], BedLeveling.prev_position[BedLeveling.Z_AXIS],
					BedLeveling.realz))
				BedLeveling.bltouch.reset(BLTouchState.BLTOUCH_DEPLOY)
				BedLeveling.first_run = False
				BedLeveling.printlog("start slow probing")
			if not BedLeveling.bltouch.trigger:
				BedLeveling.realz -= 0.1
				BedLeveling.printlog("Go Down SlOW: M114z=%f, realZ:%f" % (
					BedLeveling.current_position[BedLeveling.Z_AXIS], BedLeveling.realz))
				BedLeveling.do_blocking_move_to_z(-0.1, True)
				BedLeveling.do_m114()
			else:  # bltouch touch bed again.
				BedLeveling.state = MeshLevelingState.MeshNext
				BedLeveling.first_run = True
				BedLeveling.probe_index += 1
				BedLeveling.printlog("index: %d | X:%f, Y:%f; Z:%f, RealZ:%f" % (
					BedLeveling.probe_index - 1, BedLeveling.current_position[0], BedLeveling.current_position[1],
					BedLeveling.current_position[2], BedLeveling.realz))

				BedLeveling.set_z(BedLeveling._zigzag_x_index, BedLeveling._zigzag_y_index,
								  BedLeveling.realz + BedLeveling.Z_PROBE_OFFSET_FROM_EXTRUDER)
				BedLeveling.do_m114()
				BedLeveling.bltouch.reset(BLTouchState.BLTOUCH_STOW)

		elif BedLeveling.state == MeshLevelingState.MeshSet:
			pass
		#  BedLeveling.probe_index += 1
		elif BedLeveling.state == MeshLevelingState.MeshSetZOffset:
			pass
		elif BedLeveling.state == MeshLevelingState.MeshReset:
			BedLeveling.reset()

	##~~  using mesh map build with g29 to improve Z accuracy
	#  based on marlin : mesh_bed_leveling.h line 94 to 115
	@staticmethod
	def constrain(val, min_val, max_val):
		return min(max_val, max(min_val, val))

	@staticmethod
	def cell_index_x(x):
		cx = (float(x) - BedLeveling.min_x) * (1.0 / BedLeveling.mesh_x_dist)
		return int(BedLeveling.constrain(cx, 0, BedLeveling.grid_max_points_x - 2))

	@staticmethod
	def cell_index_y(y):
		cy = (float(y) - BedLeveling.min_y) * (1.0 / BedLeveling.mesh_y_dist)
		return int(BedLeveling.constrain(cy, 0, BedLeveling.grid_max_points_y - 2))

	@staticmethod
	def calc_z0(a0, a1, z1, a2, z2):
		delta_z = (1.0 * (z2 - z1)) / (a2 - a1)
		delta_a = float(a0) - float(a1)
		return z1 + delta_a * delta_z

	@staticmethod
	def get_z(x0, y0):
		cx = BedLeveling.cell_index_x(x0)
		cy = BedLeveling.cell_index_y(y0)

		z1 = BedLeveling.calc_z0(x0,
								 BedLeveling.index_to_xpos[cx],
								 BedLeveling.z_values[cx][cy],
								 BedLeveling.index_to_xpos[cx + 1],
								 BedLeveling.z_values[cx + 1][cy])
		z2 = BedLeveling.calc_z0(x0,
								 BedLeveling.index_to_xpos[cx],
								 BedLeveling.z_values[cx][cy + 1],
								 BedLeveling.index_to_xpos[cx + 1],
								 BedLeveling.z_values[cx + 1][cy + 1])

		z0 = BedLeveling.calc_z0(y0,
								 BedLeveling.index_to_ypos[cy],
								 z1,
								 BedLeveling.index_to_ypos[cy + 1],
								 z2)

		return BedLeveling.Z_PROBE_OFFSET_FROM_EXTRUDER + z0
