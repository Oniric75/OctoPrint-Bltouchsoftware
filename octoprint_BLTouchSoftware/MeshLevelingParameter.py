# coding=utf-8
from __future__ import absolute_import


class MeshLevelingState:
	MeshReport = 0
	MeshStart = 1
	MeshNext = 2
	MeshProbe = 3
	MeshSet = 4
	MeshSetZOffset = 5
	MeshReset = 6


class Parameter:
	levelingActive = False
	levelingFirstRun = False
	safe_mode = False

	current_position = None
	prev_position = None
	min_x = 0  # dist from side : settings ok
	min_y = 0  # dist from side : settings ok
	min_z = 0  # dist from side : settings ok
	max_x = 0  # dist from side : settings ok
	max_y = 0  # dist from side : settings ok
	max_z = 0  # dist from side : settings ok
	grid_max_points_x = 0  # number of probe grid x. DEFAULT : 3	settings ok
	grid_max_points_y = 0  # number of probe grid y. DEFAULT : 3	settings ok
	mesh_x_dist = 0  # space between probing point, calculated from max points x, settings N/A
	mesh_y_dist = 0  # space between probing point, calculated from max points y	 settings N/A
	realz = 0  # used to keep track of Z while probing

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


class AXIS:
	X_AXIS = 0  # index for X_AXIS: used for Marlin clearness
	Y_AXIS = 1  # index for Y_AXIS: used for Marlin clearness
	Z_AXIS = 2  # index for Z_AXIS: used for Marlin clearness
