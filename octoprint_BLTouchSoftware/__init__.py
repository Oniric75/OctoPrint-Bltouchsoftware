# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint_BLTouchSoftware.MeshLevelingParameter import Parameter
from octoprint_BLTouchSoftware.BedLevelingv2 import BedLevelingv2
import re
import pickle
import time
from octoprint_BLTouchSoftware.MeshLevelingParameter import MeshLevelingState
from octoprint_BLTouchSoftware.BLTouchGPIO import BLTouchState

from octoprint_BLTouchSoftware.MeshLevelingParameter import AXIS

class BltouchsoftwarePlugin(octoprint.plugin.StartupPlugin,
							octoprint.plugin.SettingsPlugin,
							octoprint.plugin.AssetPlugin,
							octoprint.plugin.TemplatePlugin):

	def __init__(self):
		super(BltouchsoftwarePlugin, self).__init__()
		self.m500path = "/home/pi/meshmap.obj"
		self.G1regex = re.compile(
			r"(G[01]\s*)(F[+-]?\d+(?:\.\d+)?)?\s*(?:X([+-]?\d+(?:\.\d+)?))?\s*(?:Y([+-]?\d+(?:\.\d+)?))?\s*(?:Z([+-]?\d+(?:\.\d+)?))?\s*(E[+-]?\d+(?:\.\d+)?)?(F[+-]?\d+(?:\.\d+)?)?",
			re.IGNORECASE)
		self.BedLeveling = BedLevelingv2()
		self.FirstHome = True

	##~~ AssetPlugin mixin
	def get_assets(self):
		return dict(
			js=["js/BLTouchSoftware.js"]
		)

	##~~ SettingsPlugin mixin
	def get_settings_defaults(self):
		return dict(grid_max_points_x=3,
					grid_max_points_y=3,
					z_clearance_deploy_probe=8,  # z clearance for deploy/stow
					x_probe_offset_from_extruder=46,  # x offset: -left  +right  [of the nozzle]
					y_probe_offset_from_extruder=22,  # y offset: -front +behind [the nozzle]
					z_probe_offset_from_extruder=-0.55,  # z offset: -below +above  [the nozzle]
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
					safe_mode=False,
					enable=False)

	def on_settings_save(self, data):
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
		self._logger.info("maxx: %d maxy: %d" % (
			self._settings.get(["grid_max_points_x"]), self._settings.get(["grid_max_points_y"])))
		self.BedLeveling.set_mesh_dist(self._settings.get(["grid_max_points_x"]),
									   self._settings.get(["grid_max_points_y"]))
		Parameter.X_PROBE_OFFSET_FROM_EXTRUDER = self._settings.get(["x_probe_offset_from_extruder"])
		Parameter.Y_PROBE_OFFSET_FROM_EXTRUDER = self._settings.get(["y_probe_offset_from_extruder"])
		Parameter.Z_PROBE_OFFSET_FROM_EXTRUDER = self._settings.get(["z_probe_offset_from_extruder"])
		Parameter.Z_CLEARANCE_DEPLOY_PROBE = self._settings.get(["z_clearance_deploy_probe"])
		Parameter.XY_PROBE_SPEED = int(self._settings.get(["xy_probe_speed"]))
		Parameter.safe_mode = self._settings.get(["safe_mode"])

	##~~ octoprint.plugin.StartupPlugin

	def on_after_startup(self):
		Parameter.levelingActive = False
		Parameter.levelingHome = False

		Parameter.safe_mode = self._settings.get(["safe_mode"])
		Parameter.X_PROBE_OFFSET_FROM_EXTRUDER = self._settings.get(["x_probe_offset_from_extruder"])
		Parameter.Y_PROBE_OFFSET_FROM_EXTRUDER = self._settings.get(["y_probe_offset_from_extruder"])
		Parameter.Z_PROBE_OFFSET_FROM_EXTRUDER = self._settings.get(["z_probe_offset_from_extruder"])
		Parameter.Z_CLEARANCE_DEPLOY_PROBE = self._settings.get(["z_clearance_deploy_probe"])
		Parameter.XY_PROBE_SPEED = int(self._settings.get(["xy_probe_speed"]))

		self.BedLeveling.setlogger(self._logger)
		self.BedLeveling.setprinter(self._printer)
		self._logger.info("Loading BLTouch!")
		profile = self._printer_profile_manager.get_default()
		volume = profile["volume"]
		custom_box = volume["custom_box"]
		# see if we have a custom bounding box
		if custom_box:
			Parameter.min_x = custom_box["x_min"]
			Parameter.max_x = custom_box["x_max"]
			Parameter.min_y = custom_box["y_min"]
			Parameter.max_y = custom_box["y_max"]
			Parameter.min_z = custom_box["z_min"]
			Parameter.max_z = custom_box["z_max"]
		elif self._settings.get(["min_x"]) is not None and self._settings.get(["min_x"]) != "":
			Parameter.min_x = int(self._settings.get(["min_x"]))
			Parameter.max_x = int(self._settings.get(["max_x"]))
			Parameter.min_y = int(self._settings.get(["min_y"]))
			Parameter.max_y = int(self._settings.get(["max_x"]))
			Parameter.min_z = int(self._settings.get(["min_z"]))
			Parameter.max_z = int(self._settings.get(["max_z"]))
		else:
			Parameter.min_x = 0
			Parameter.max_x = volume["width"]
			Parameter.min_y = 0
			Parameter.max_y = volume["depth"]
			Parameter.min_z = 0
			Parameter.max_z = volume["height"]

		self.BedLeveling.reset()
		self.BedLeveling.set_mesh_dist(self._settings.get(["grid_max_points_x"]),
								  self._settings.get(["grid_max_points_y"]))
		self.BedLeveling.bltouch.probemode(BLTouchState.BLTOUCH_RESET)
		self.BedLeveling.bltouch.probemode(BLTouchState.BLTOUCH_STOW)

		try:
			with open(self.m500path, 'rb') as filehandler:
				self.BedLeveling.z_values = pickle.load(filehandler)
				self._logger.info("meshmap:")
				self._logger.info(self.BedLeveling.z_values)
				self.BedLeveling.available = True
		except IOError:
			self._logger.info("Error: No mesh map found...")

	##~~ octoprint.plugin.TemplatePlugin
	# register settings pages
	def get_template_configs(self):
		return [
			dict(type="settings"),
			dict(type="sidebar", icon="arrows-alt")
		]

	def buildreplacement(self, g1):
		replstr = r"\1"
		self._logger.info("curZ: %f, get_z:%f" % (self.BedLeveling.current_position[AXIS.Z_AXIS],
												  self.BedLeveling.get_z(self.BedLeveling.current_position[AXIS.X_AXIS],
																		 self.BedLeveling.current_position[
																			 AXIS.Y_AXIS])))

		off_z = float(self.BedLeveling.get_z(self.BedLeveling.current_position[AXIS.X_AXIS],
											 self.BedLeveling.current_position[AXIS.Y_AXIS]))
		pz = self.BedLeveling.current_position[AXIS.Z_AXIS] + off_z
		if g1.group(2) is not None:
			replstr += r" %s" % g1.group(2)
		if g1.group(3) is not None:
			replstr += r" X:%s" % g1.group(3)
		if g1.group(4) is not None:
			replstr += r" Y:%s" % g1.group(4)
		if g1.group(5) is not None:
			replstr += r" Z:%0.3f" % (float(g1.group(5)) + off_z)
		else:
			replstr += r" Z:%0.3f" % pz
		if g1.group(6) is not None:
			replstr += r" %s" % g1.group(6)
		if g1.group(7) is not None:
			replstr += r" %s" % g1.group(7)
		return replstr

	##~~ Softwareupdate hook

	##~~ G28 & G29Hooker
	#  G28: safe homing: home XY then go to the center and Z home
	#  G28 Z : safe Z homing : go to the center and Z home
	#  G29 : start probing
	def rewrite_hooker(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
		if gcode and gcode == "G90":
			self.BedLeveling.relative = False
		elif gcode and gcode == "G91":
			self.BedLeveling.relative = True
		elif cmd and cmd == "M280 P0 S10":
			self._logger.info("BLTOUCH_DEPLOY")
			# BedLeveling.bltouch.probemode(10)  # BLTOUCH_DEPLOY
			self.BedLeveling.bltouch.probemode(BLTouchState.BLTOUCH_DEPLOY)
		elif cmd and cmd == "M280 P0 S90":
			self._logger.info("BLTOUCH_STOW")
			# BedLeveling.bltouch.probemode(90)  # BLTOUCH_STOW
			self.BedLeveling.bltouch.probemode(BLTouchState.BLTOUCH_STOW)
		# BedLeveling.bltouch._setmode(1475)
		elif cmd and cmd == "M280 P0 S120":
			self._logger.info("BLTOUCH_SELFTEST")
			# BedLeveling.bltouch.probemode(120)  # BLTOUCH_SELFTEST
			# BedLeveling.bltouch._setmode(1780)
			self.BedLeveling.bltouch.probemode(BLTouchState.BLTOUCH_SELFTEST)
		elif cmd and cmd == "M280 P0 S160":
			self._logger.info("BLTOUCH_RESET")
			# BedLeveling.bltouch.probemode(160)  # BLTOUCH_RESET
			# BedLeveling.bltouch._setmode(2190BLTOUCH_RESET)
			self.BedLeveling.bltouch.probemode(BLTouchState.BLTOUCH_RESET)
		elif self.BedLeveling.available and gcode and (gcode == "G1" or gcode == "G0"):
			# improvement doable ? look into void plan_arc in marlin_main.cpp (planner.apply_leveling)
			G1 = self.G1regex.match(cmd)
			self._logger.info("TRIGGER G0/G1...")

			if G1:
				self.BedLeveling.set_current_pos(G1.group(3), G1.group(4), G1.group(5))
				if not self.BedLeveling.relative:
					newg1 = self.G1regex.sub(self.buildreplacement(G1), cmd)
					self._logger.info("cmd=%s, replaced by: \'%s\'" % (cmd, newg1))
				else:
					self._logger.info("Relative mode : auto leveling off")
			else:
				self._logger.info("Regex Fail ? cmd=\'%s\'" % cmd)

		elif cmd and (cmd == "G28" or cmd == "G28 Z" or cmd == "G28 Z0"):
			self._logger.info("Detect G28: %s" % cmd)
			Parameter.levelingHome = True
			if self.FirstHome:
				self._logger.info("Detect G28 time1 cmd:%s" % cmd)
				self.FirstHome = False
				self.BedLeveling.bltouch.reset()
				self._printer.commands(["G91", "G1 Z10 F%d" % Parameter.XY_PROBE_SPEED, "G90", cmd])
				return
			else:
				time.sleep(2)
				self.FirstHome = True
				px = (Parameter.max_x - Parameter.min_x + Parameter.X_PROBE_OFFSET_FROM_EXTRUDER) / 2
				py = (Parameter.max_y - Parameter.min_y + Parameter.Y_PROBE_OFFSET_FROM_EXTRUDER) / 2
				self.BedLeveling.set_current_pos(px, py, 0)
			# BedLeveling.bltouch._setmode(2190)  # RESET
			# BedLeveling.bltouch._setmode(1475)  # STOW
				self._logger.info("Detect G28 time2 %s" % cmd)
				self.BedLeveling.bltouch.reset(BLTouchState.BLTOUCH_DEPLOY)
				return ["G28 X Y", "G91", "G1 X%.3f Y%.3f F%d" % (px, py, Parameter.XY_PROBE_SPEED), "G90", "G28 Z"]
		elif cmd and cmd == "G29":
			self.BedLeveling.reset()
			self.BedLeveling.state = MeshLevelingState.MeshStart
			self.BedLeveling.g29v2()
			return
		elif gcode and gcode == "M500":
			with open(self.m500path, 'wb+') as filehandler:
				pickle.dump(self.BedLeveling.z_values, filehandler)


		elif cmd and cmd == "ZTest":
			self._logger.info("Ztesting...")
			self.BedLeveling.bltouch.send_zmin_to_printer(True)
			time.sleep(0.5)
			self.BedLeveling.bltouch.send_zmin_to_printer(False)
			return
		return cmd

	#  alfawise : ok X:0.0 Y:0.0 Z:0.0 .*
	def read_m114(self, comm, line, *args, **kwargs):
		if Parameter.levelingActive or Parameter.levelingHome:
			# self._logger.info("===comm:%s, line:%s===" % (comm, line))
			m114 = re.match(r"ok\s*X:\s*(\d+\.\d+)\s*Y:\s*(\d+\.\d+)\s*Z:\s*(\d+\.\d+).*", line, re.IGNORECASE)
			if m114:
				# self._logger.info("M114 result: X:%s|Y:%s|Z:%s" % (m114.group(1), m114.group(2), m114.group(3)))
				self.BedLeveling.set_current_pos(float(m114.group(1)), float(m114.group(2)), float(m114.group(3)))
				if self.BedLeveling.state == MeshLevelingState.MeshStart:
					Parameter.levelingActive = True
				self.BedLeveling.g29v2()
		return line

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
