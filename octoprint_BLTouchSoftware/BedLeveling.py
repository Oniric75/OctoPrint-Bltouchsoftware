# coding=utf-8
from __future__ import absolute_import


class BedLeveling():
	index_to_xpos = None  # [grid_max_points_x] : list of x position for each probe x point
	index_to_ypos = None  # [grid_max_points_y] : list of x position for each probe y point
	min_x = 0
	min_y = 0
	min_z = 0
	max_x = 0
	max_y = 0
	max_z = 0
	grid_max_points_x = 0  # number of probe grid x
	grid_max_points_y = 0  # number of probe grid y
	mesh_x_dist = 0
	mesh_y_dist = 0
	z_offset = 0
	z_values = None  # [grid_max_point_x][grid_max_point_y]

	__logger = None

	@staticmethod
	def set_logger(logger):
		if logger is not None:
			BedLeveling.__logger = logger

	@staticmethod
	def printlog(log):
		if BedLeveling.__logger is None:
			return
		BedLeveling.__logger.info(log)

	@staticmethod
	def set_z(px, py, z):
		if BedLeveling.z_values is None:
			BedLeveling.reset_zvalues()
		BedLeveling.z_values[px][py] = z

	@staticmethod
	def set_mesh_dist(grid_max_points_x, grid_max_points_y):
		BedLeveling.printlog('Init Probing map')
		BedLeveling.grid_max_points_x = int(grid_max_points_x)
		BedLeveling.grid_max_points_y = int(grid_max_points_y)

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
		BedLeveling.reset_zvalues()

	@staticmethod
	def reset_zvalues():
		BedLeveling._z_value = None
		BedLeveling.z_values = [[0 for y in range(BedLeveling.grid_max_points_y)] for x in
								range(BedLeveling.grid_max_points_x)]

# inline void gcode_G29() {
