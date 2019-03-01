/*
 * View model for OctoPrint-Bltouchsoftware
 *
 * Author: Oniric
 * License: AGPLv3
 */
$(function() {
    function BltouchsoftwareViewModel(parameters) {
        var self = this;

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        // self.settingsViewModel = parameters[1];
        self.settingsViewModel = parameters[0];
		self.printerProfilesViewModel = parameters[1];
		self.controlViewModel = parameters[2];
        self.loginStateViewModel = parameters[3];


        self.started = ko.observable();
        self.stage = ko.observable();
        self.grid_max_points_x = ko.observable();
        self.grid_max_points_y = ko.observable();
        self.z_clearance_deploy_probe = ko.observable();  // z clearance for deploy/stow
		self.x_probe_offset_from_extruder = ko.observable(); // x offset: -left  +right  [of the nozzle]
		self.y_probe_offset_from_extruder = ko.observable();// y offset: -front +behind [the nozzle]
		self.z_probe_offset_from_extruder = ko.observable(); // z offset: -below +above  [the nozzle]
		self.min_probe_edge = ko.observable();
		self.xy_probe_speed = ko.observable(); // x and y axis travel speed(mm / m) between	probes
		self.homing_feedrate_z = ko.observable();  // z homing speeds (mm/m)
		self.z_probe_speed_fast = ko.observable();  // feedrate(mm / m)	for the first approach when double-probing
		self.z_probe_speed_slow = ko.computed(function(){return self.z_probe_speed_fast()/2});
		self.homing_feedrate_xy = ko.computed(function(){return 50*60});  // x & y homing speeds (mm/m)


        self.index_to_xpos = ko.observableArray(); // keep all x position to probe. linked to grid_max_points_x
        self.index_to_ypos = ko.observableArray(); // keep all y position to probe
        self.gcode_cmds = ko.observableArray();


        self.onBeforeBinding = function() {
			self.stage('Start');
			self.started(false);
			self.grid_max_points_x(self.settingsViewModel.settings.plugins.BLTouchSoftware.grid_max_points_x());
			self.grid_max_points_y(self.settingsViewModel.settings.plugins.BLTouchSoftware.grid_max_points_y());
			self.z_clearance_deploy_probe(self.settingsViewModel.settings.plugins.BLTouchSoftware.z_clearance_deploy_probe());
		    self.x_probe_offset_from_extruder(self.settingsViewModel.settings.plugins.BLTouchSoftware.x_probe_offset_from_extruder());
		    self.y_probe_offset_from_extruder(self.settingsViewModel.settings.plugins.BLTouchSoftware.y_probe_offset_from_extruder());
		    self.z_probe_offset_from_extruder(self.settingsViewModel.settings.plugins.BLTouchSoftware.z_probe_offset_from_extruder());
		    self.min_probe_edge(self.settingsViewModel.settings.plugins.BLTouchSoftware.min_probe_edge());
		    self.xy_probe_speed(self.settingsViewModel.settings.plugins.BLTouchSoftware.xy_probe_speed());
		    self.homing_feedrate_z(self.settingsViewModel.settings.plugins.BLTouchSoftware.homing_feedrate_z());
		    self.z_probe_speed_fast=(self.settingsViewModel.settings.plugins.BLTouchSoftware.z_probe_speed_fast());

        }

        self.onEventSettingsUpdated = function (payload) {
            self.grid_max_points_x(self.settingsViewModel.settings.plugins.BLTouchSoftware.grid_max_points_x());
			self.grid_max_points_y(self.settingsViewModel.settings.plugins.BLTouchSoftware.grid_max_points_y());
        }


        self.start_level = function(){
            alert("Click:" + self.grid_max_points_x() + " " + self.settingsViewModel.settings.plugins.BLTouchSoftware.grid_max_points_x());
            if(!self.started()){
					self.started(true);
					self.stage('Next');
					var volume = self.printerProfilesViewModel.currentProfileData().volume;
					console.log(volume);
					if(typeof volume.custom_box !== 'function'){
						console.log('Using custom box options');
						var min_x = parseInt(volume.custom_box.x_min());
						var max_x = parseInt(volume.custom_box.x_max());
						var min_y = parseInt(volume.custom_box.y_min());
						var max_y = parseInt(volume.custom_box.y_max());
					} else {
						console.log('Using width and depth');
						var min_x = 0;
						var max_x = parseInt(volume.width());
						var min_y = 0;
						var max_y = parseInt(volume.depth());
                    }

                    var mesh_x_dist = (max_x - min_x) / parseInt(self.grid_max_points_x()) - 1;
                    var mesh_y_dist = (max_y - min_y) / parseInt(self.grid_max_points_y()) - 1;

                    for (var i = 0; i < parseInt(self.grid_max_points_x()); i++)
                        self.index_to_xpos.push(min_x + i * mesh_x_dist);

                    for (var i = 0; i < parseInt(self.grid_max_points_y()); i++)
                        self.index_to_ypos.push(min_x + i * mesh_y_dist);

                    console.log("xpos=" + self.index_to_xpos());
                    console.log("ypos=" + self.index_to_ypos());

                    var cur = { x_index:0, y_index:0};
                    var pos = {x:0, y:0};
                    for (i = 0; i < parseInt(self.grid_max_points_x()) * parseInt(self.grid_max_points_y()); i++) {
                        console.log("pos=" + pos.x + "," + pos.y + " | cur=" + cur.x_index + ", " + cur.y_index);
                        self.zigzag(cur, pos, i);
                        self.gcode_cmds.push('G28'); // override by plugin server side
                        self.gcode_cmds.push('G1 X' + pos.x + ' Y' + pos.y);

                        OctoPrint.control.sendGcode(self.gcode_cmds()).done (function() {
                            console.log("done?!");
                            OctoPrint.control.sendGcode("M117 pouet");
                            });
                        self.gcode_cmds([]);
                    }

             }

        }

        self.zigzag = function(cur, pos, i) {
            cur.x_index = i % parseInt(self.grid_max_points_x());
            cur.y_index = Math.floor(i / parseInt(self.grid_max_points_x()));
            if (cur.y_index % 2)
                cur.x_index = parseInt(self.grid_max_points_x()) - 1 - cur.x_index;
            pos.x = self.index_to_xpos()[cur.x_index];
            pos.y = self.index_to_ypos()[cur.y_index];

        }
    }
    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: BltouchsoftwareViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: ['settingsViewModel','printerProfilesViewModel','controlViewModel','loginStateViewModel'],
        // Elements to bind to, e.g. #settings_plugin_BLTouchSoftware, #tab_plugin_BLTouchSoftware, ...
        elements: ['#sidebar_plugin_BLTouchSoftware', '#settings_plugin_BLTouchSoftware']
    });
});
