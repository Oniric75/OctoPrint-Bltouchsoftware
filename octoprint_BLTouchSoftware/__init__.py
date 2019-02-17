# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from BedLeveling import BedLeveling


class BltouchsoftwarePlugin(octoprint.plugin.StartupPlugin,
							octoprint.plugin.SettingsPlugin,
							octoprint.plugin.TemplatePlugin):

	##~~ SettingsPlugin mixin
	def get_settings_defaults(self):
		return dict(grid_max_points_x=3,
					grid_max_points_y=3,
					enable=False)

	def on_settings_save(self, data):
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
		BedLeveling.set_mesh_dist(self._settings.get(["grid_max_points_x"]),
								  self._settings.get(["grid_max_points_y"]))

	##~~ octoprint.plugin.StartupPlugin

	def on_after_startup(self):
		BedLeveling.set_logger(self._logger)
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
		else:
			BedLeveling.min_x = 0
			BedLeveling.max_x = volume["width"]
			BedLeveling.min_y = 0
			BedLeveling.max_y = volume["depth"]
			BedLeveling.min_z = 0
			BedLeveling.max_z = volume["height"]

		BedLeveling.set_mesh_dist(self._settings.get(["grid_max_points_x"]),
								  self._settings.get(["grid_max_points_y"]))

	##~~ octoprint.plugin.TemplatePlugin
	# register settings pages
	def get_template_configs(self):
		return [
			dict(type="settings", template="bltouchsoftware_settings.jinja2", custom_bindings=False)
		]

	##~~ G29Hooker

	def rewrite_g29(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
		if gcode and gcode == "G29":
			if self._logger is not None and self._settings is not None:
				self._logger.info("Detect and replace G29 & %s" % self._settings.get(["grid_max_points_x"]))
			cmd = ""
		return cmd,

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
		"octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.rewrite_g29
	}
