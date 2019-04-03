# coding=utf-8
from __future__ import absolute_import


class MeshLevelingState():
	MeshReport = 0
	MeshStart = 1
	MeshNext = 2
	MeshProbe = 3
	MeshSet = 4
	MeshSetZOffset = 5
	MeshReset = 6


class Parameter():
	levelingActive = False
	safe_mode = False
