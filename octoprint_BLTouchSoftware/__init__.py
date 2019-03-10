# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint_BLTouchSoftware.BedLeveling import BedLeveling

import re

from octoprint_BLTouchSoftware.MeshLevelingState import MeshLevelingState

class BltouchsoftwarePlugin(octoprint.plugin.StartupPlugin,
							octoprint.plugin.SettingsPlugin,
							octoprint.plugin.AssetPlugin,
							octoprint.plugin.TemplatePlugin):

	def __init__(self):
		super(BltouchsoftwarePlugin, self).__init__()


	##~~ AssetPlugin mixin
	def get_assets(self):
		return dict(
			js=["js/BLTouchSoftware.js"]
		)

	##~~ SettingsPlugin mixin
	def get_settings_defaults(self):
		return dict(grid_max_points_x=3,
					grid_max_points_y=3,
					z_clearance_deploy_probe=10,  # z clearance for deploy/stow
					x_probe_offset_from_extruder=46,  # x offset: -left  +right  [of the nozzle]
					y_probe_offset_from_extruder=22,  # y offset: -front +behind [the nozzle]
					z_probe_offset_from_extruder=0.45,  # z offset: -below +above  [the nozzle]
					min_probe_edge=10,
					xy_probe_speed=8000,  # x and y axis travel speed(mm / m) between	probes
					homing_feedrate_z=4 * 60,  # z homing speeds (mm/m)
					z_probe_speed_fast=4 * 60,  # feedrate(mm / m)	for the first approach when double-probing
					z_probe_speed_slow=4 * 60 / 2,  # Z_PROBE_SPEED_FAST / 2
					min_x=10,
					min_y=20,
					max_x=290,
					max_y=280,
					min_z=0,
					max_z=400,
					enable=False)

	def on_settings_save(self, data):
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
		self._logger.info("maxx: %d maxy: %d" % (
			self._settings.get(["grid_max_points_x"]), self._settings.get(["grid_max_points_y"])))
		BedLeveling.set_mesh_dist(self._settings.get(["grid_max_points_x"]),
								  self._settings.get(["grid_max_points_y"]))
		BedLeveling.X_PROBE_OFFSET_FROM_EXTRUDER = self._settings.get(["x_probe_offset_from_extruder"])
		BedLeveling.Y_PROBE_OFFSET_FROM_EXTRUDER = self._settings.get(["y_probe_offset_from_extruder"])
		BedLeveling.Z_PROBE_OFFSET_FROM_EXTRUDER = self._settings.get(["z_probe_offset_from_extruder"])
		BedLeveling.Z_CLEARANCE_DEPLOY_PROBE = self._settings.get(["z_clearance_deploy_probe"])
		BedLeveling.XY_PROBE_SPEED = int(settings.get(["xy_probe_speed"]))

	##~~ octoprint.plugin.StartupPlugin

	def on_after_startup(self):
		BedLeveling.X_PROBE_OFFSET_FROM_EXTRUDER = self._settings.get(["x_probe_offset_from_extruder"])
		BedLeveling.Y_PROBE_OFFSET_FROM_EXTRUDER = self._settings.get(["y_probe_offset_from_extruder"])
		BedLeveling.Z_PROBE_OFFSET_FROM_EXTRUDER = self._settings.get(["z_probe_offset_from_extruder"])
		BedLeveling.Z_CLEARANCE_DEPLOY_PROBE = self._settings.get(["z_clearance_deploy_probe"])
		BedLeveling.XY_PROBE_SPEED = int(self._settings.get(["xy_probe_speed"]))
		BedLeveling.set_logger(self._logger)
		BedLeveling.printer = self._printer
		self._logger.info("Loading BLTouch!")
		profile = self._printer_profile_manager.get_default()
		volume = profile["volume"]
		custom_box = volume["custom_box"]
		# see if we have a custom bounding box
		if custom_box:
			BedLeveling.min_x = custom_box["x_min"]
			BedLeveling.max_x = custom_box["x_max"]
			BedLeveling.min_y = custom_box["y_min"]
			BedLeveling.max_y = custom_box["y_max"]
			BedLeveling.min_z = custom_box["z_min"]
			BedLeveling.max_z = custom_box["z_max"]
		elif self._settings.get(["min_x"]) is not None:
			BedLeveling.min_x = self._settings.get(["min_x"])
			BedLeveling.max_x = self._settings.get(["max_x"])
			BedLeveling.min_y = self._settings.get(["min_y"])
			BedLeveling.max_y = self._settings.get(["max_x"])
			BedLeveling.min_z = self._settings.get(["min_z"])
			BedLeveling.max_z = self._settings.get(["max_z"])
		else:
			BedLeveling.min_x = 0
			BedLeveling.max_x = volume["width"]
			BedLeveling.min_y = 0
			BedLeveling.max_y = volume["depth"]
			BedLeveling.min_z = 0
			BedLeveling.max_z = volume["height"]

		BedLeveling.set_mesh_dist(self._settings.get(["grid_max_points_x"]),
								  self._settings.get(["grid_max_points_y"]))
		BedLeveling.bltouch._setmode(2190)
		BedLeveling.bltouch._setmode(1475)

	##~~ octoprint.plugin.TemplatePlugin
	# register settings pages
	def get_template_configs(self):
		return [
			dict(type="settings"),
			dict(type="sidebar", icon="arrows-alt")
		]

	##~~ G28 & G29Hooker
	#  G28: safe homing: home XY then go to the center and Z home
	#  G28 Z : safe Z homing : go to the center and Z home
	#  G29 : start probing
	def rewrite_hooker(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
		if cmd and (cmd == "G28" or cmd == "G28 Z" or cmd == "G28 Z0"):
			self._logger.info("Detect G28")
			px = (BedLeveling.max_x - BedLeveling.min_x + BedLeveling.X_PROBE_OFFSET_FROM_EXTRUDER) / 2
			py = (BedLeveling.max_y - BedLeveling.min_y + BedLeveling.Y_PROBE_OFFSET_FROM_EXTRUDER) / 2
			return ["G91",
					"G1 Z10 F%d" % BedLeveling.XY_PROBE_SPEED,
					"G90",
					"G28 X Y",
					"G91",
					("G1 X%.3f Y%.3f F%d" % (px, py, BedLeveling.XY_PROBE_SPEED)),
					"G90",
					"G28 Z"]
		elif cmd and cmd == "G29":
			BedLeveling.active = True
			BedLeveling.reset()
			BedLeveling.gcode_g29()
			return
		elif cmd and cmd == "M280 P0 S10":
			self._logger.info("BLTOUCH_DEPLOY")
			# BedLeveling.bltouch.probemode(10)  # BLTOUCH_DEPLOY
			BedLeveling.bltouch._setmode(650)
		elif cmd and cmd == "M280 P0 S90":
			self._logger.info("BLTOUCH_STOW")
			# BedLeveling.bltouch.probemode(90)  # BLTOUCH_STOW
			BedLeveling.bltouch._setmode(1475)
		elif cmd and cmd == "M280 P0 S120":
			self._logger.info("BLTOUCH_SELFTEST")
			# BedLeveling.bltouch.probemode(120)  # BLTOUCH_SELFTEST
			BedLeveling.bltouch._setmode(1780)
		elif cmd and cmd == "M280 P0 S160":
			self._logger.info("BLTOUCH_RESET")
			# BedLeveling.bltouch.probemode(160)  # BLTOUCH_RESET
			BedLeveling.bltouch._setmode(2190)
		return cmd

	#  alfawise : ok X:0.0 Y:0.0 Z:0.0 .*
	def read_m114(self, comm, line, *args, **kwargs):
		if BedLeveling.active is True:
			# self._logger.info("===comm:%s, line:%s===" % (comm, line))
			m114 = re.match(r"ok\s*X:\s*(\d+\.\d+)\s*Y:\s*(\d+\.\d+)\s*Z:\s*(\d+\.\d+).*", line, re.IGNORECASE)
			if m114:
				# self._logger.info("M114 result: X:%s|Y:%s|Z:%s" % (m114.group(1), m114.group(2), m114.group(3)))
				BedLeveling.set_current_pos(float(m114.group(1)), float(m114.group(2)), float(m114.group(3)))
				if BedLeveling.state == MeshLevelingState.MeshStart:
					BedLeveling.realz = 0
					BedLeveling.state = MeshLevelingState.MeshNext
				BedLeveling.gcode_g29()
		# else:
		#	self._logger.info("no match m114: %s" % line)
		return line

	##~~ AutoBedLeveling Probe

	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			BLTouchSoftware=dict(
				displayName="Bltouchsoftware Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="Oniric75",
				repo="OctoPrint-Bltouchsoftware",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/Oniric75/OctoPrint-Bltouchsoftware/archive/{target_version}.zip"
			)
		)


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Bltouchsoftware Plugin"


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = BltouchsoftwarePlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.rewrite_hooker,
		# "octoprint.comm.protocol.gcode.sending": __plugin_implementation__.G29_loop,
		"octoprint.comm.protocol.gcode.received": __plugin_implementation__.read_m114
	}
