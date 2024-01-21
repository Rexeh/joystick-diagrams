"""Star Citizen XML Parser for use with Joystick Diagrams."""
import logging
import os
from pathlib import Path
from typing import Union
from xml.dom import minidom

from joystick_diagrams.input.profile_collection import ProfileCollection

_logger = logging.getLogger(__name__)


HAT_FORMAT_LOOKUP = {"up": "U", "down": "D", "left": "L", "right": "R"}

PROFILE_MAPPINGS = {
    "seat_general": "Spaceship",
    "spaceship_general": "Spaceship",
    "spaceship_view": "Spaceship",
    "spaceship_movement": "Spaceship",
    "spaceship_quantum": "Spaceship",
    "spaceship_docking": "Spaceship",
    "spaceship_targeting": "Weapons",
    "spaceship_targeting_advanced": "Weapons",
    "spaceship_target_hailing": "Weapons",
    "spaceship_radar": "Spaceship Scanning",
    "spaceship_scanning": "Spaceship Scanning",
    "spaceship_mining": "Spaceship Mining",
    "spaceship_salvage": "Spaceship Salavage",
    "turret_movement": "Weapons",
    "turret_advanced": "Weapons",
    "spaceship_weapons": "Weapons",
    "spaceship_missiles": "Weapons",
    "spaceship_defensive": "Weapons",
    "vehicle_capacitor_assignment": "Spaceship",
    "spaceship_auto_weapons": "Weapons",
    "spaceship_power": "Spaceship",
    "spaceship_hud": "Spaceship",
    "lights_controller": "Spaceship",
    "stopwatch": "Spaceship",
    "player": "Spaceship",
    "prone": "Spaceship",
    "mapui": "Spaceship",
    "tractor_beam": "Spaceship",
    "zero_gravity_eva": "Spaceship",
    "zero_gravity_traversal": "Spaceship",
    "vehicle_general": "Spaceship",
    "vehicle_driver": "Spaceship",
    "spectator": "Spaceship",
    "default": "Spaceship",
    "player_emotes": "Spaceship",
    "player_input_optical_tracking": "Spaceship",
    "player_choice": "Spaceship",
    "view_director_mode": "Spaceship",
    "remoterigidentitycontroller": "Spaceship",
    "server_renderer": "Spaceship",
}


class StarCitizen:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self.__load_file()
        self.hat = None
        self.devices = {}
        self.button_array = {}
        self.action_map_bypass = {"Fire 1", "Fire 2"}
        # Force some Labels, this ideally need to be declared elsewhere or from an external file
        self.custom_labels = {
            "attack1": "z_attack",
            "combatheal": "z_combat_heal",
            "combathealtarget": "z_heal_target",
            "consume": "z_consume",
            "customize": "z_customize",
            "drop": "z_drop",
            "emote_agree": "z_emote_agree",
            "emote_angry": "z_emote_angry",
            "emote_atease": "z_emote_atease",
            "emote_attention": "z_emote_attention",
            "emote_blah": "z_emote_blah",
            "emote_bored": "z_emote_bored",
            "emote_bow": "z_emote_bow",
            "emote_burp": "z_emote_burp",
            "emote_cheer": "z_emote_cheer",
            "emote_chicken": "z_emote_chicken",
            "emote_clap": "z_emote_clap",
            "emote_come": "z_emote_come",
            "emote_cry": "z_emote_cry",
            "emote_cs_forward": "z_emote_cs_forward",
            "emote_cs_left": "z_emote_cs_left",
            "emote_cs_no": "z_emote_cs_no",
            "emote_cs_right": "z_emote_cs_right",
            "emote_cs_stop": "z_emote_cs_stop",
            "emote_cs_yes": "z_emote_cs_yes",
            "emote_dance": "z_emote_dance",
            "emote_disagree": "z_emote_disagree",
            "emote_failure": "z_emote_failure",
            "emote_flex": "z_emote_flex",
            "emote_flirt": "z_emote_flirt",
            "emote_gasp": "z_emote_gasp",
            "emote_gloat": "z_emote_gloat",
            "emote_greet": "z_emote_greet",
            "emote_laugh": "z_emote_laugh",
            "emote_launch": "z_emote_launch",
            "emote_point": "z_emote_point",
            "emote_rude": "z_emote_rude",
            "emote_salute": "z_emote_salute",
            "emote_sit": "z_emote_sit",
            "emote_sleep": "z_emote_sleep",
            "emote_smell": "z_emote_smell",
            "emote_taunt": "z_emote_taunt",
            "emote_threaten": "z_emote_threaten",
            "emote_wait": "z_emote_wait",
            "emote_wave": "z_emote_wave",
            "emote_whistle": "z_emote_whistle",
            "eva_boost": "z_eva_boost",
            "eva_brake": "z_eva_brake",
            "eva_detach": "z_eva_detach",
            "eva_launch": "z_eva_launch",
            "eva_push_back": "z_eva_push_back",
            "eva_push_forward": "z_eva_push_forward",
            "eva_roll": "z_eva_roll",
            "eva_roll_left": "z_eva_roll_left",
            "eva_roll_right": "z_eva_roll_right",
            "eva_strafe_back": "z_eva_strafe_back",
            "eva_strafe_down": "z_eva_strafe_down",
            "eva_strafe_forward": "z_eva_strafe_fwd",
            "eva_strafe_lateral": "z_eva_strafe_lat",
            "eva_strafe_left": "z_eva_strafe_left",
            "eva_strafe_longitudinal": "z_eva_strafe_long.",
            "eva_strafe_right": "z_eva_strafe_right",
            "eva_strafe_up": "z_eva_strafe_up",
            "eva_strafe_vertical": "z_eva_strafe_vert.",
            "eva_toggle_headlook_mode": "z_eva_headlook_mode",
            "eva_view_pitch": "z_eva_view_pitch",
            "eva_view_pitch_down": "z_eva_view_down",
            "eva_view_pitch_up": "z_eva_view_pitch_up",
            "eva_view_yaw": "z_eva_view_yaw",
            "eva_view_yaw_left": "z_eva_view_left",
            "eva_view_yaw_right": "z_eva_yaw_right",
            "fixed_speed_decrement": "z_fixed_speed_-",
            "fixed_speed_increment": "z_fixed_speed_+",
            "flashui_backspace": "z_flashui_backspace",
            "flashui_down": "z_flashui_down",
            "flashui_kp_2": "z_flashui_kp_2",
            "flashui_kp_3": "z_flashui_kp_3",
            "flashui_kp_4": "z_flashui_kp_4",
            "flashui_kp_7": "z_flashui_kp_7",
            "flashui_left": "z_flashui_left",
            "flashui_return": "z_flashui_return",
            "flashui_right": "z_flashui_right",
            "flashui_up": "z_flashui_up",
            "focus_on_chat_textinput": "z_focus_chat_input",
            "foip_cyclechannel": "z_foip_cyclechannel",
            "foip_pushtotalk": "z_foip_PTT",
            "foip_pushtotalk_proximity": "z_PTT_proximity",
            "foip_recalibrate": "z_foip_recalibrate",
            "foip_viewownplayer": "z_foip_view_self",
            "force_respawn": "z_force_respawn",
            "free_thirdperson_camera": "z_3rd_person_cam",
            "gp_crouch": "z_crouch",
            "gp_movex": "z_move_x",
            "gp_movey": "z_move_y",
            "gp_rotatepitch": "z_rotate_pitch",
            "gp_rotateyaw": "z_rotate_yaw",
            "headtrack_camera_enabled": "z_headtrack_camera",
            "headtrack_enabled": "z_headtrack_enabled",
            "headtrack_hold": "z_headtrack_hold",
            "headtrack_recenter_device": "z_headtrack_center",
            "holster": "z_holster",
            "inspect": "z_inspect",
            "jump": "z_jump",
            "leanleft": "z_lean_left",
            "leanright": "z_lean_right",
            "melee_AttackHeavyLeft": "z_Attack_Heavy_Left",
            "melee_AttackHeavyRight": "z_Attack_Right_+",
            "melee_AttackLightLeft": "z_Attack_Light_Left",
            "melee_AttackLightRight": "z_Attack_Right_-",
            "melee_block": "z_melee_block",
            "moveback": "z_move_back",
            "moveforward": "z_move_forward",
            "moveleft": "z_move_left",
            "moveright": "z_move_right",
            "nextitem": "z_nextitem",
            "nextweapon": "z_nextweapon",
            "pc_camera_orbit": "z_camera_orbit",
            "pc_focus": "z_focus",
            "pc_interaction_mode": "z_interaction_mode",
            "pc_interaction_select": "z_interaction_sel",
            "pc_item_primary": "z_item_primary",
            "pc_item_secondary": "z_item_secondary",
            "pc_personal_back": "z_personal_back",
            "pc_personal_thought": "z_personal_thought",
            "pc_pit_emotes": "z_emotes",
            "pc_pit_empty_backpack": "z_empty_backpack",
            "pc_pit_flight_systems": "z_flight_systems",
            "pc_pit_inventory": "z_inventory",
            "pc_pit_item_actions": "z_item_actions",
            "pc_pit_item_drop": "z_item_drop",
            "pc_pit_item_unstown": "z_item_unstown",
            "pc_pit_miningmode_actions": "z_miningmode_actions",
            "pc_pit_mobiglas_actions": "z_mobiglas_actions",
            "pc_pit_player_actions": "z_player_actions",
            "pc_pit_remote_turrets": "z_remote_turrets",
            "pc_pit_ship_systems": "z_ship_systems",
            "pc_pit_vehicle_actions": "z_vehicle_actions",
            "pc_pit_weapon_selection": "z_weapon_selection",
            "pc_pit_weapons_systems": "z_weapons_systems",
            "pc_qs_consumables": "z_consumables",
            "pc_qs_flight_mode": "z_flight_mode",
            "pc_qs_grenades": "z_grenades",
            "pc_qs_weapons_pistol": "z_weapons_pistol",
            "pc_qs_weapons_primary": "z_weapons_primary",
            "pc_qs_weapons_secondary": "z_weapons_secondary",
            "pc_screen_focus_down": "z_focus_down",
            "pc_screen_focus_left": "z_focus_left",
            "pc_screen_focus_right": "z_focus_right",
            "pc_screen_focus_up": "z_focus_up",
            "pc_select": "z_select",
            "pc_throw_decrease": "z_throw_-",
            "pc_throw_increase": "z_throw_+",
            "pc_ui_back": "z_ui_back",
            "pc_zoom_in": "z_zoom_in",
            "pc_zoom_out": "z_zoom_out",
            "pl_exit": "z_exit",
            "pl_hud_open_scoreboard": "z_scoreboard",
            "port_modification_select": "z_port_modification",
            "prevItem": "z_prevItem",
            "prevweapon": "z_prevweapon",
            "prone": "z_prone",
            "prone_rollleft": "z_prone_rollleft",
            "prone_rollright": "z_prone_rollright",
            "ready": "z_ready",
            "refillgastank": "z_refill_gas_tank",
            "reload": "z_reload",
            "respawn": "z_respawn",
            "retry": "z_retry",
            "selectgadget": "z_select_gadget",
            "selectMeleeWeapon": "z_Melee_Weapon",
            "selectpistol": "z_select_pistol",
            "selectprimary": "z_select_primary",
            "selectsecondary": "z_select_secondary",
            "selectUnarmedCombat": "z_Unarmed_Combat",
            "selectUtilityItem": "z_Utility_Item",
            "spectate_gen_nextcamera": "z_spectate_cam_+",
            "spectate_gen_nextmode": "z_spectate_mode_+",
            "spectate_gen_prevmode": "z_spectate_mode_-",
            "spectate_next_target": "z_spec_next_target",
            "spectate_prev_target": "z_spec_prev_target",
            "spectate_rotatepitch": "z_spectate_pitch",
            "spectate_rotatepitch_mouse": "z_spectate_pitch",
            "spectate_rotateyaw": "z_spectate_yaw",
            "spectate_rotateyaw_mouse": "z_spectate_yaw",
            "spectate_toggle_hud": "z_spectate_hud",
            "spectate_toggle_lock_target": "z_spec_lock_target",
            "spectate_toggle_thirdperson": "z_spec_3rd_person",
            "spectate_zoom": "z_spectate_zoom",
            "spectate_zoom_in": "z_spectate_zoom_+",
            "spectate_zoom_out": "z_spectate_zoom_-",
            "sprint": "z_sprint",
            "stabilize": "z_stabilize",
            "thirdperson": "z_third_person",
            "throw_overhand": "z_throw_overhand",
            "throw_underhand": "z_throw_underhand",
            "toggle_chat": "z_chat",
            "toggle_contact": "z_contact",
            "toggle_flashlight": "z_flashlight",
            "toggleEquipHelmet": "z_Equip_Helmet",
            "tractor_beam_decrease_distance": "z_tractor_dist_-",
            "tractor_beam_increase_distance": "z_tractor_dist_+",
            "turret_change_firemode": "z_turret_firemode",
            "turret_gyromode": "z_turret_gyromode",
            "turret_limiter_abs": "z_turret_limit_abs",
            "turret_limiter_rel": "z_turret_limit_rel",
            "turret_limiter_rel_decrease": "z_turret_limit_rel-",
            "turret_limiter_rel_increase": "z_turret_limit_rel+",
            "turret_limiter_toggle": "z_turret_limiter",
            "turret_pitch": "z_turret_pitch",
            "turret_pitch_down": "z_turret_pitch_down",
            "turret_pitch_up": "z_turret_pitch_up",
            "turret_recenter": "z_turret_recenter",
            "turret_remote_exit": "z_remote_turret_exit",
            "turret_toggle_esp": "z_turret_esp",
            "turret_toggle_mouse_mode": "z_turret_mouse_mode",
            "turret_yaw": "z_turret_yaw",
            "turret_yaw_left": "z_turret_yaw_left",
            "turret_yaw_right": "z_turret_yaw_right",
            "u_exit": "z_exit",
            "ui_hide_hint": "z_hide_hint",
            "use": "z_use",
            "v_accel_range_abs": "z_accel_range_abs",
            "v_accel_range_down": "z_accel_range_-",
            "v_accel_range_rel": "z_accel_range_rel",
            "v_accel_range_up": "z_accel_range_+",
            "v_afterburner": "z_afterburner",
            "v_attack1": "z_fire1",
            "v_attack1_group1": "z_fire1",
            "v_attack1_group2": "z_fire2",
            "v_attack2": "z_fire2",
            "v_autoland": "z_autoland",
            "v_boost": "z_boost",
            "v_brake": "z_brake",
            "v_close_all_doors": "z_close_all_doors",
            "v_cooler_throttle_down": "z_cooler_+",
            "v_cooler_throttle_up": "z_cooler_-",
            "v_cycle_pitch_ladder_mode": "z_pitch_ladder",
            "v_dec_ping_focus_angle": "z_ping_angle_-",
            "v_decrease_mining_throttle": "z_mining_power_-",
            "v_dock_toggle_view": "z_dock_view",
            "v_eject": "z_eject",
            "v_eject_cinematic": "z_eject_cinematic",
            "v_emergency_exit": "z_emergency_exit",
            "v_enter_remote_turret_1": "z_remote_turret_1",
            "v_enter_remote_turret_2": "z_remote_turret_2",
            "v_enter_remote_turret_3": "z_remote_turret_3",
            "v_exit": "z_exit",
            "v_flightready": "z_flight ready",
            "v_horn": "z_horn",
            "v_hud_cancel": "z_hud_cancel",
            "v_hud_confirm": "z_hud_confirm",
            "v_hud_focused_cycle_mode_back": "z_focus_mode_-",
            "v_hud_focused_cycle_mode_fwd": "z_focus_mode_+",
            "v_hud_interact_toggle": "z_hud_interact",
            "v_hud_left_panel_down": "z_left_panel_down",
            "v_hud_left_panel_left": "z_left_panel_left",
            "v_hud_left_panel_right": "z_left_panel_right",
            "v_hud_left_panel_up": "z_left_panel_up",
            "v_hud_open_scoreboard": "z_open_scoreboard",
            "v_ifcs_speed_limiter_reset_scm": "z_speed_limit_reset",
            "v_ifcs_toggle_cruise_control": "z_cruise_control",
            "v_ifcs_toggle_esp": "z_esp",
            "v_ifcs_toggle_gforce_safety": "z_gforce_safety",
            "v_ifcs_toggle_speed_limiter": "z_speed_limiter",
            "v_ifcs_toggle_vector_decoupling": "z_vector_decoupling",
            "v_inc_ping_focus_angle": "z_ping_angle_+",
            "v_increase_mining_throttle": "z_mining_power_+",
            "v_invoke_docking": "z_invoke_docking",
            "v_invoke_ping": "z_invoke_ping",
            "v_jettison_volatile_cargo": "z_jettison_volatile",
            "v_lights": "z_lights",
            "v_lock_all_doors": "z_lock_doors",
            "v_lock_rotation": "z_lock_rotation",
            "v_look_ahead_enable": "z_look_ahead",
            "v_look_ahead_start_target_tracking": "z_target_tracking",
            "v_mgv_switch_brake_on_idle": "z_brake_on_idle",
            "v_mining_throttle": "z_mining_power",
            "v_mining_use_consumable1": "z_mining_use_1",
            "v_mining_use_consumable2": "z_mining_use_2",
            "v_mining_use_consumable3": "z_mining_use_3",
            "v_move": "z_move",
            "v_move_back": "z_move_back",
            "v_move_forward": "z_move_forward",
            "v_open_all_doors": "z_open_all_doors",
            "v_pitch": "z_pitch",
            "v_pitch_down": "z_pitch_down",
            "v_pitch_mouse": "z_pitch_mouse",
            "v_pitch_up": "z_pitch_up",
            "v_power_focus_shields": "z_power_shields_+",
            "v_power_focus_thrusters": "z_power_thrusters_+",
            "v_power_focus_weapons": "z_power_weapons_+",
            "v_power_reset_focus": "z_power_reset_focus",
            "v_power_throttle_down": "z_throttle_down",
            "v_power_throttle_max": "z_throttle_max",
            "v_power_throttle_min": "z_throttle_min",
            "v_power_throttle_up": "z_throttle_up",
            "v_power_toggle": "z_power_on/off",
            "v_power_toggle_shields": "z_shields_on/off",
            "v_power_toggle_thrusters": "z_thrusters_on/off",
            "v_power_toggle_weapons": "z_weapons_on/off",
            "v_radar_cycle_focus_back": "z_radar_focus_-",
            "v_radar_cycle_focus_fwd": "z_radar_focus_+",
            "v_radar_cycle_mode_back": "z_radar_mode_-",
            "v_radar_cycle_mode_fwd": "z_radar_mode_+",
            "v_radar_cycle_zoom_back": "z_radar_zoom_-",
            "v_radar_cycle_zoom_fwd": "z_radar_zoom_+",
            "v_radar_toggle_active_or_passive": "z_radar_act/pas",
            "v_radar_toggle_onoff": "z_radar_on/off",
            "v_radar_toggle_view_focus": "z_radar_view_focus",
            "v_roll": "z_roll",
            "v_roll_left": "z_roll_left",
            "v_roll_right": "z_roll_right",
            "v_scanning_trigger_scan": "z_scan",
            "v_self_destruct": "z_self_destruct",
            "v_shield_raise_level_back": "z_shield_back_+",
            "v_shield_raise_level_down": "z_shield_down_+",
            "v_shield_raise_level_forward": "z_shield_forward_+",
            "v_shield_raise_level_left": "z_shield_left_+",
            "v_shield_raise_level_right": "z_shield_right_+",
            "v_shield_raise_level_up": "z_shield_up_+",
            "v_shield_reset_level": "z_shield_reset",
            "v_space_brake": "z_space_brake",
            "v_speed_range_abs": "z_speed_range_abs",
            "v_speed_range_down": "z_speed_range_-",
            "v_speed_range_rel": "z_speed_range_rel",
            "v_speed_range_up": "z_speed_range_+",
            "v_starmap": "z_starmap",
            "v_strafe_back": "z_strafe_back",
            "v_strafe_down": "z_strafe_down",
            "v_strafe_forward": "z_strafe_forward",
            "v_strafe_lateral": "z_strafe_lateral",
            "v_strafe_left": "z_strafe_left",
            "v_strafe_longitudinal": "z_strafe_long.",
            "v_strafe_longitudinal_invert": "z_strafe_inv_long.",
            "v_strafe_right": "z_strafe_right",
            "v_strafe_up": "z_strafe_up",
            "v_strafe_vertical": "z_strafe_vert.",
            "v_target_cycle_all_back": "z_target_all_-",
            "v_target_cycle_all_fwd": "z_target_all_+",
            "v_target_cycle_all_reset": "z_target_reset",
            "v_target_cycle_attacker_back": "z_target_attacker_-",
            "v_target_cycle_attacker_fwd": "z_target_attacker_+",
            "v_target_cycle_attacker_reset": "z_target_attacker_rst",
            "v_target_cycle_friendly_back": "z_target_friendly_-",
            "v_target_cycle_friendly_fwd": "z_target_friendly_+",
            "v_target_cycle_friendly_reset": "z_target_friendly_rst",
            "v_target_cycle_hostile_back": "z_target_hostile_-",
            "v_target_cycle_hostile_fwd": "z_target_hostile_+",
            "v_target_cycle_hostile_reset": "z_target_hostile_rst",
            "v_target_cycle_in_view_back": "z_cycle_in_view_bck",
            "v_target_cycle_in_view_fwd": "z_cycle_in_view_fwd",
            "v_target_cycle_in_view_reset": "z_cycle_in_view_reset",
            "v_target_cycle_pinned_back": "z_target_pinned_-",
            "v_target_cycle_pinned_fwd": "z_target_pinned_+",
            "v_target_cycle_pinned_reset": "z_target_pinned_rst",
            "v_target_cycle_reticle_mode": "z_target_reticle",
            "v_target_cycle_selection_back": "z_target_-",
            "v_target_cycle_selection_fwd": "z_target_+",
            "v_target_cycle_selection_reset": "z_target_se_rst",
            "v_target_cycle_subitem_back": "z_target_subitem_-",
            "v_target_cycle_subitem_fwd": "z_target_subitem_+",
            "v_target_cycle_subitem_reset": "z_target_subitem_rst",
            "v_target_hail": "z_hail",
            "v_target_lock_selected": "z_target_lock",
            "v_target_match_vel": "z_match_vel",
            "v_target_pin_selected": "z_target_pin",
            "v_target_pin_selected_hold": "z_target_pin_hold",
            "v_target_remove_all_pins": "z_target_remove_pins",
            "v_target_toggle_lock_index_1": "z_target_lock_1",
            "v_target_toggle_lock_index_2": "z_target_lock_2",
            "v_target_toggle_lock_index_3": "z_target_lock_3",
            "v_target_toggle_pin_index_1": "z_target_pin_1",
            "v_target_toggle_pin_index_1_hold": "z_target_pin_1_hold",
            "v_target_toggle_pin_index_2": "z_target_pin_2",
            "v_target_toggle_pin_index_2_hold": "z_target_pin_2_hold",
            "v_target_toggle_pin_index_3": "z_target_pin_3",
            "v_target_toggle_pin_index_3_hold": "z_target_pin_3_hold",
            "v_target_tracking_auto_zoom": "z_tracking_auto_zoom",
            "v_target_unlock_selected": "z_target_unlock",
            "v_target_unpin_selected": "z_target_unpin",
            "v_target_unpin_selected_hold": "z_target_unpin_hold",
            "v_toggle_all_doorlocks": "z_doorlocks_on/off",
            "v_toggle_all_doors": "z_doors_open/close",
            "v_toggle_cabin_lights": "z_cabin_lights",
            "v_toggle_docking_mode": "z_docking_mode",
            "v_toggle_landing_system": "z_landing_system",
            "v_toggle_mining_laser_fire": "z_mining_laser_fire",
            "v_toggle_mining_laser_type": "z_mining_laser_type",
            "v_toggle_mining_mode": "z_mining_mode",
            "v_toggle_qdrive_engagement": "z_quantum_engage",
            "v_toggle_qdrive_spooling": "z_quantum_spooling",
            "v_toggle_running_lights": "z_running_lights",
            "v_toggle_scan_mode": "z_scan_mode",
            "v_toggle_vtol": "z_vtol",
            "v_toggle_yaw_roll_swap": "z_yaw/roll_swap",
            "v_unlock_all_doors": "z_unlock_doors",
            "v_view_cycle_back": "z_view_cycle_back",
            "v_view_cycle_fwd": "z_view_cycle_fwd",
            "v_view_cycle_internal_back": "z_cycle_int_bck",
            "v_view_cycle_internal_fwd": "z_cycle_int_fwd",
            "v_view_dynamic_zoom_abs": "z_view_zoom_abs",
            "v_view_dynamic_zoom_abs_toggle": "z_view_zoom_abs",
            "v_view_dynamic_zoom_rel": "z_view_zoom_rel",
            "v_view_dynamic_zoom_rel_in": "z_view_zoom_rel_+",
            "v_view_dynamic_zoom_rel_out": "z_view_zoom_rel_-",
            "v_view_freelook_mode": "z_freelook_mode",
            "v_view_interact": "z_view_interact",
            "v_view_look_behind": "z_look_behind",
            "v_view_mode": "z_view_mode",
            "v_view_option": "z_view_option",
            "v_view_pitch": "z_view_pitch",
            "v_view_pitch_down": "z_view_pitch_down",
            "v_view_pitch_up": "z_view_pitch_up",
            "v_view_yaw": "z_view_yaw",
            "v_view_yaw_left": "z_view_yaw_left",
            "v_view_yaw_right": "z_view_yaw_right",
            "v_view_zoom_in": "z_view_zoom_+",
            "v_view_zoom_out": "z_view_zoom_-",
            "v_weapon_arm_missile": "z_arm_missile",
            "v_weapon_countermeasure_decoy_burst_decrease": "z_decoy_burst_+",
            "v_weapon_countermeasure_decoy_burst_increase": "z_decoy_burst_-",
            "v_weapon_countermeasure_decoy_launch": "z_decoy",
            "v_weapon_countermeasure_decoy_launch_panic": "z_decoy_panic",
            "v_weapon_countermeasure_noise_launch": "z_noise",
            "v_weapon_cycle_aimmode": "z_cycle_aimmode",
            "v_weapon_cycle_missile_back": "z_cycle_missile_+",
            "v_weapon_cycle_missile_fwd": "z_cycle_missile_-",
            "v_weapon_launch_missile": "z_missile",
            "v_weapon_launch_missile_cinematic": "z_missile_cinematic",
            "v_weapon_manual_gimbal_cycle_source": "z_gimbal_cycle_src",
            "v_weapon_manual_gimbal_lock_vector": "z_gimbal_lock_vector",
            "v_weapon_toggle_ai": "z_weapon_ai",
            "v_weapon_unarm_all_missiles": "z_unarm_missiles",
            "v_yaw": "z_yaw",
            "v_yaw_left": "z_yaw_left",
            "v_yaw_mouse": "z_yaw_mouse",
            "v_yaw_right": "z_yaw_right",
            "view_fov_in": "z_view_fov_+",
            "view_fov_out": "z_view_fov_-",
            "view_fstop_in": "z_view_fstop_+",
            "view_fstop_out": "z_view_fstop_-",
            "view_restore_defaults": "z_restore_defaults",
            "visor_wipe": "z_visor_wipe",
            "walk": "z_walk",
            "weapon_auxiliary_action": "z_auxiliary_action",
            "weapon_change_firemode": "z_change_firemode",
            "weapon_melee": "z_weapon_melee",
            "weapon_zeroing_decrease": "z_weapon_zeroing_-",
            "weapon_zeroing_increase": "z_weapon_zeroing_+",
            "zoom": "z_zoom",
            "zoom_in": "z_zoom_in",
            "zoom_in_out": "z_zoom_+/-",
            "zoom_out": "z_zoom_out",
        }

    def __load_file(self) -> str:
        if os.path.exists(self.file_path):
            if (os.path.splitext(self.file_path))[1] == ".xml":
                data = Path(self.file_path).read_text(encoding="utf-8")
                try:
                    self.__validate_file(data)
                except Exception:
                    raise Exception("File is not a valid Star Citizen XML")  # TODO remove base exception
                else:
                    return data
            else:
                raise Exception("File must be an XML file")  # TODO remove base exception
        else:
            raise FileNotFoundError("File not found")

    def __validate_file(self, data) -> bool:
        try:
            parsed_xml = minidom.parseString(data)
        except ValueError:
            raise Exception("File is not a valid Star Citizen XML")  # TODO remove base exception
        else:
            if (
                len(parsed_xml.getElementsByTagName("ActionMaps")) == 1
                and len(parsed_xml.getElementsByTagName("options")) > 0
                and len(parsed_xml.getElementsByTagName("actionmap")) > 0
            ):
                return True

            raise Exception

    def get_human_readable_name(self, name) -> str:
        if name in self.custom_labels:
            return self.name_format(self.custom_labels.get(name))

        return self.name_format(name)

    def name_format(self, name: str) -> str:
        name_parts = name.split("_")
        if len(name_parts) == 1:
            return name_parts[0].capitalize()
        else:
            return (" ".join(name_parts[1:])).capitalize()

    def process_name(self, name: str) -> str:
        _logger.debug(f"Bind Name: {name}")

        return self.get_human_readable_name(name)

    def parse_file_data(self, data: str):
        return minidom.parseString(data)

    def create_device_lookup(self, options) -> None:
        """Create lookup table for bind strings to resolve easier."""
        _prefixes = {"joystick": "js", "keyboard": "kb", "mouse": "mo"}

        def parse_product(product_str: str) -> tuple[str, str]:
            product_name = product_str[0:-38].strip()
            product_guid = product_str[-37:-1].strip()
            return (product_name, product_guid)

        for option in options:
            _type = option.getAttribute("type")
            _inst = option.getAttribute("instance")

            _product = option.getAttribute("Product")

            _name, _guid = parse_product(_product)

            device_identifier = f"{_prefixes[_type]}{_inst}"
            self.devices[device_identifier] = {"name": _name, "guid": _guid}

        _logger.debug(f"Created device lookups: {self.devices} ")

    def parse(self) -> ProfileCollection:
        # Get XML Data
        parse = self.parse_file_data(self.data)

        profile_collection = ProfileCollection()

        # Get Joystick Information to aid device creation
        self.create_device_lookup(parse.getElementsByTagName("options"))

        # Get the ActionMaps (Profiles)
        profiles = parse.getElementsByTagName("actionmap")

        # For each Profile get the binds for the devices
        for profile in profiles:
            profile_name = get_profile_name_map(profile.getAttribute("name"))
            profile_obj = profile_collection.create_profile(profile_name)

            # Get all the action nodes for a profile
            actions = profile.getElementsByTagName("action")

            # Look through the actions for a given profile
            for action in actions:
                # Command for action STR
                name = self.process_name(action.getAttribute("name"))

                # Get the binds for the ACTION
                binds = action.getElementsByTagName("rebind")

                # iterate each bind
                for bind in binds:
                    bind_input = bind.getAttribute("input")

                    resolved_input = resolve_input(bind_input)

                    if not resolved_input:  # No binding available
                        continue

                    device_id, input, modifiers = resolved_input

                    # Resolve the devices and create in the profile if needed
                    device_lookup = self.devices.get(device_id)

                    if not device_lookup:
                        _logger.error("A device with a bind was not found in the list of devices.")
                        continue

                    _active_device = profile_obj.add_device(device_lookup.get("guid"), device_lookup.get("name"))

                    if modifiers:
                        _active_device.add_modifier_to_input(input, {modifiers}, name)
                    else:
                        _active_device.create_input(input, name)

        return profile_collection


def get_profile_name_map(name: str) -> str:
    """Return a mapped profile name  for a given name.

    Allows multiple profiles to be grouped into one
    """
    _name = PROFILE_MAPPINGS.get(name)

    # Handle unexpected new mappings with default
    if _name is None:
        _logger.warning("No map found for a Star Citizen profile {name}. This should be raised as a bug.")
        _name = "Spaceship"

    return _name


def extract_modifiers(bind_str: str) -> str | None:
    """Extract modifiers from an input string.

    Assumes only one modifier can exist before a + symbol.
    """
    if "+" in bind_str:
        return bind_str.split("+")[0]

    return None


def resolve_bind(bind_str: str) -> tuple[Union[str, None], str]:
    """Determine bind type and return."""
    _modifiers = extract_modifiers(bind_str)

    if _modifiers:
        _control_input = bind_str.split("+")[1]
    else:
        _control_input = bind_str

    control = find_control_type(_control_input)

    return (_modifiers, control)


def find_control_type(control_input: str) -> str:
    """Determine the type of input from given string.

    - rotz > AXIS
    - buttonX > BUTTON
    - hat_down > HAT SWITCH
    - y > AXISD

    Returns formatted string

    """
    # Buttons
    if "button" in control_input:
        return f"BUTTON_{control_input[6:]}"

    # Hats
    if "hat" in control_input:
        _id = control_input[3]  # Assumes no more than 9 hats on a device - should be ok
        _direction = HAT_FORMAT_LOOKUP[control_input[5:]]
        return f"POV_{_id}_{_direction}"

    # Rotation Axis
    if "rot" in control_input:
        return f"AXIS_R{control_input[3]}"

    # Slider Controls
    if "slider" in control_input:
        return f"AXIS_SLIDER_{control_input[6:]}"

    # Standard AXIS
    if len(control_input) == 1:
        return f"AXIS_{control_input.upper()}"

    _logger.error("No control type found for {control_input}")
    return control_input


def resolve_input(input_str: str) -> tuple[str, str, str | None] | None:
    """Resolve an INPUT string to the a device/binding.

    Returns (device id, bind string, modifiers)
    """
    input_str = input_str.strip()

    _device_id, _binding = input_str[0:3], input_str[4:]

    if not _binding:  # Handles "jsX_ " scenario no mapping
        return None

    _modifiers, _resolved_bind = resolve_bind(_binding)

    return (_device_id, _resolved_bind, _modifiers)


if __name__ == "__main__":
    pass
