# Sanitized printing candidate section inventory

Coordinator inspection: 2026-09-18; source: private resolved migration inventory
and candidate captured 2026-09-08. Only section names are reproduced. No private
values, calibration, serial paths, credentials or raw configuration are included.
This is a source inventory, not a new validation or installable configuration.
The exact 30 retained names agree with the candidate section headers; 86 sections
are omitted. Host/MCU revision context and earlier file-output evidence remain in
[sensor bring-up](../hardware/test-sv08-01-sensor-bringup.md).

## Retained candidate sections

```text
mcu
mcu extra_mcu
printer
probe
bed_mesh
quad_gantry_level
stepper_x
tmc2209 stepper_x
stepper_y
tmc2209 stepper_y
stepper_z
tmc2209 stepper_z
stepper_z1
tmc2209 stepper_z1
stepper_z2
tmc2209 stepper_z2
stepper_z3
tmc2209 stepper_z3
thermistor my_thermistor_e
extruder
tmc2209 extruder
verify_heater extruder
filament_switch_sensor filament_sensor
thermistor my_thermistor
heater_bed
verify_heater heater_bed
fan_generic fan0
fan_generic fan1
fan_generic fan3
heater_fan hotend_fan
```

## Omitted sections from the resolved factory configuration

Omission does not mean every item is optional. Required print controls and host
interfaces must be restored through upstream-compatible configuration and review.

```text
virtual_sdcard
pause_resume
display_status
respond
gcode_macro CANCEL_PRINT
gcode_macro PAUSE
gcode_macro RESUME
gcode_macro SET_PAUSE_NEXT_LAYER
gcode_macro SET_PAUSE_AT_LAYER
gcode_macro SET_PRINT_STATS_INFO
gcode_macro _TOOLHEAD_PARK_PAUSE_CANCEL
gcode_macro _CLIENT_EXTRUDE
gcode_macro _CLIENT_RETRACT
gcode_macro GET_TIMELAPSE_SETUP
gcode_macro _SET_TIMELAPSE_SETUP
gcode_macro TIMELAPSE_TAKE_FRAME
gcode_macro _TIMELAPSE_NEW_FRAME
delayed_gcode _WAIT_TIMELAPSE_TAKE_FRAME
gcode_macro HYPERLAPSE
delayed_gcode _HYPERLAPSE_LOOP
gcode_macro TIMELAPSE_RENDER
delayed_gcode _WAIT_TIMELAPSE_RENDER
gcode_macro TEST_STREAM_DELAY
gcode_shell_command get_ip
gcode_macro _GET_IP
gcode_macro G31
gcode_macro PRINT_START
gcode_macro PRINT_END
gcode_shell_command clear_plr
gcode_shell_command SYNC
gcode_macro save_last_file
gcode_macro clear_last_file
gcode_shell_command POWER_LOSS_RESUME
gcode_macro RESUME_INTERRUPTED
gcode_macro LOG_Z
gcode_macro BEEP
gcode_macro mainled_on
gcode_macro mainled_off
gcode_shell_command FACTORY_RESETS
force_move
gcode_macro _global_var
gcode_macro _IDLE_TIMEOUT
gcode_macro _ALL_FAN_OFF
gcode_macro CLEAN_NOZZLE
gcode_macro _CALIBRATION_ZOFFSET
delayed_gcode _auto_zoffset
gcode_macro _Delay_Calibrate
delayed_gcode TEST_BELT
gcode_macro QUAD_GANTRY_LEVEL
gcode_macro PROBE_CALIBRATE
gcode_macro BED_MESH_CALIBRATE
gcode_macro G34
delayed_gcode bed_mesh_init
delayed_gcode _print_start_wait
gcode_macro START_PRINT
gcode_macro END_PRINT
delayed_gcode _resume_wait
gcode_macro LOAD_FILAMENT
gcode_macro UNLOAD_FILAMENT
gcode_macro M109
gcode_macro M190
gcode_macro M106
gcode_macro M107
gcode_macro M600
gcode_macro _OBICO_LAYER_CHANGE
delayed_gcode _WAIT_OBICO_LAYER_CHANGE
gcode_macro OBICO_LINK_STATUS
gcode_macro _OBICO_RELINK
adxl345
exclude_object
resonance_tester
temperature_sensor mcu_temp
temperature_sensor Host_temp
temperature_sensor Toolhead_Temp
input_shaper
probe_pressure
homing_override
z_offset_calibration
board_pins
display
output_pin beeper
neopixel Screen_Colour
gcode_arcs
output_pin main_led
idle_timeout
save_variables
```

## Execution boundary

`virtual_sdcard`, `pause_resume`, `display_status`, `respond`, standard print
controls, and persistent artifact paths still need a closed upstream configuration
before printing. Physical values and saved calibration remain unvalidated.
The next worker uses this inventory plus pinned public sources; it does not need
the private candidate or more human inventory to prepare a bounded proposal.
Actual electrical, input, motion and thermal evidence remains H01/H05/H06 in the
[shared queue](../hardware/coordinated-human-tasks.md).
