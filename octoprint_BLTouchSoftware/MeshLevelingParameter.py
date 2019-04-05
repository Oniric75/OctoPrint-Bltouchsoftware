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


class AXIS:
	X_AXIS = 0  # index for X_AXIS: used for Marlin clearness
	Y_AXIS = 1  # index for Y_AXIS: used for Marlin clearness
	Z_AXIS = 2  # index for Z_AXIS: used for Marlin clearness
