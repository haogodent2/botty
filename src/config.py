import configparser
import string
import threading
import numpy as np
import os
from dataclasses import dataclass
from logger import Logger
config_lock = threading.Lock()

def _default_iff(value, iff, default = None):
    return default if value == iff else value

def only_lowercase_letters(value):
    if not (x := ''.join(filter( lambda x: x in 'abcdefghijklmnopqrstuvwxyz', value ))):
        x = "botty"
    return x

class Config:
    data_loaded = False

    configs = {}

    # config data
    general = {}
    advanced_options = {}
    gamble = {}
    ui_roi = {}
    ui_pos = {}
    routes = {}
    routes_order = []
    char = {}
    colors = {}
    shop = {}
    path = {}
    blizz_sorc = {}
    light_sorc = {}
    nova_sorc = {}
    hydra_sorc = {}
    hammerdin = {}
    fohdin = {}
    trapsin = {}
    barbarian = {}
    poison_necro = {}
    bone_necro = {}
    necro = {}
    basic = {}
    basic_ranged = {}

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            with config_lock:
                if not cls._instance.data_loaded:
                    cls._instance.data_loaded = True
                    cls._instance.load_data()
        return cls._instance

    def _select_optional(self, section: string, key: string, default = None):
        try:
            return self._select_val(section=section, key=key)
        except:
            return default

    def _select_val(self, section: str, key: str = None):
        found_in = ""
        try:
            if section in self.configs["custom"]["parser"] and key in self.configs["custom"]["parser"][section]:
                found_val = self.configs["custom"]["parser"][section][key]
                found_in = "custom"
            elif section in self.configs["config"]["parser"]:
                found_val = self.configs["config"]["parser"][section][key]
                found_in = "config"
            elif section in self.configs["shop"]["parser"]:
                found_val = self.configs["shop"]["parser"][section][key]
                found_in = "shop"
            else:
                found_val = self.configs["game"]["parser"][section][key]
                found_in = "game"

            for var_name in self.configs[found_in]["vars"]: # set variable.
                if var_name in found_val:
                    var_val = self.configs[found_in]["vars"][var_name]
                    found_val = found_val.replace(var_name, var_val)
            return found_val
        except KeyError:
            Logger.error(f"Key '{key}' not found in section '{section}'")
            Logger.error("Closing in 10 seconds..")
            wait(10)
            os._exit(1)

    def turn_off_goldpickup(self):
        Logger.info("All stash tabs and character are full of gold, turn off gold pickup")
        with config_lock:
            self.char["stash_gold"] = False

    def turn_on_goldpickup(self):
        Logger.info("All stash tabs and character are no longer full of gold. Turn gold stashing back on.")
        self.char["stash_gold"] = True

    def load_data(self):
        self.configs = {
            "config": {"parser": configparser.ConfigParser(), "vars": {}},
            "game": {"parser": configparser.ConfigParser(), "vars": {}},
            "shop": {"parser": configparser.ConfigParser(), "vars": {}},
            "transmute": {"parser": configparser.ConfigParser(), "vars": {}},
            "custom": {"parser": configparser.ConfigParser(), "vars": {}},
        }
        self.configs["config"]["parser"].read('config/params.ini')
        self.configs["game"]["parser"].read('config/game.ini')
        self.configs["shop"]["parser"].read('config/shop.ini')
        self.configs["transmute"]["parser"].read('config/transmute.ini')

        if os.environ.get('RUN_ENV') != "test" and os.path.exists('config/custom.ini'):
            try:
                self.configs["custom"]["parser"].read('config/custom.ini')
            except configparser.MissingSectionHeaderError:
                Logger.error("custom.ini missing section header, defaulting to params.ini")

        for config_name in self.configs:
            config = self.configs[config_name]
            try:
                for var in config["parser"]["variables"]:
                    config["vars"][var] = config["parser"]["variables"][var] # set var name to var value
            except KeyError: # "" header section was not found for this config file.
                pass



        self.general = {
            "sandbox_ip": str(self._select_val("general", "sandbox_ip")),
            "saved_games_folder": self._select_val("general", "saved_games_folder"),
            "name": _default_iff(self._select_val("general", "name"), "", "botty"),
            "max_game_length_s": float(self._select_val("general", "max_game_length_s")),
            "max_consecutive_fails": int(self._select_val("general", "max_consecutive_fails")),
            "max_runtime_before_break_m": float(_default_iff(self._select_val("general", "max_runtime_before_break_m"), '', 0)),
            "break_length_m": float(_default_iff(self._select_val("general", "break_length_m"), '', 0)),
            "randomize_runs": bool(int(self._select_val("general", "randomize_runs"))),
            "difficulty": self._select_val("general", "difficulty"),
            "message_api_type": self._select_val("general", "message_api_type"),
            "custom_message_hook": self._select_val("general", "custom_message_hook"),
            "custom_loot_message_hook": self._select_val("general", "custom_loot_message_hook"),
            "discord_status_count": False if not self._select_val("general", "discord_status_count") else int(self._select_val("general", "discord_status_count")),
            "discord_log_chicken": bool(int(self._select_val("general", "discord_log_chicken"))),
            "info_screenshots": bool(int(self._select_val("general", "info_screenshots"))),
            "pickit_screenshots": bool(int(self._select_val("general", "pickit_screenshots"))),
            "d2r_path": _default_iff(self._select_val("general", "d2r_path"), "", "C:\Program Files (x86)\Diablo II Resurrected"),
            "restart_d2r_when_stuck": bool(int(self._select_val("general", "restart_d2r_when_stuck"))),
        }

        self.routes = {}
        order_str = self._select_val("routes", "order")
        self.routes_order = [x.strip() for x in order_str.split(",")]
        del self.configs["config"]["parser"]["routes"]["order"]
        for key in self.routes_order:
            self.routes[key] = True
        # Botty only knows "run_shenk" but in orders we split run_eldritch and run_eldritch_shenk
        self.routes_order = ["run_shenk" if x in ["run_eldritch", "run_eldritch_shenk"] else x for x in self.routes_order]

        self.char = {
            "type": self._select_val("char", "type"),
            "show_items": self._select_val("char", "show_items"),
            "inventory_screen": self._select_val("char", "inventory_screen"),
            "teleport": self._select_val("char", "teleport"),
            "stand_still": self._select_val("char", "stand_still"),
            "show_automap": self._select_val("char", "show_automap"),
            "clear_screen": self._select_val("char", "clear_screen"),
            "force_move": self._select_val("char", "force_move"),
            "num_loot_columns": int(self._select_val("char", "num_loot_columns")),
            "take_health_potion": float(self._select_val("char", "take_health_potion")),
            "take_mana_potion": float(self._select_val("char", "take_mana_potion")),
            "take_rejuv_potion_health": float(self._select_val("char", "take_rejuv_potion_health")),
            "take_rejuv_potion_mana": float(self._select_val("char", "take_rejuv_potion_mana")),
            "heal_merc": float(self._select_val("char", "heal_merc")),
            "heal_rejuv_merc": float(self._select_val("char", "heal_rejuv_merc")),
            "chicken": float(self._select_val("char", "chicken")),
            "merc_chicken": float(self._select_val("char", "merc_chicken")),
            "town_portal": self._select_val("char", "town_portal"),
            "belt_rows": int(self._select_val("char", "belt_rows")),
            "show_belt": self._select_val("char", "show_belt"),
            "potion1": self._select_val("char", "potion1"),
            "potion2": self._select_val("char", "potion2"),
            "potion3": self._select_val("char", "potion3"),
            "potion4": self._select_val("char", "potion4"),
            "belt_rejuv_columns": int(self._select_val("char", "belt_rejuv_columns")),
            "belt_hp_columns": int(self._select_val("char", "belt_hp_columns")),
            "belt_mp_columns": int(self._select_val("char", "belt_mp_columns")),
            "stash_gold": bool(int(self._select_val("char", "stash_gold"))),
            "use_merc": bool(int(self._select_val("char", "use_merc"))),
            "open_chests": bool(int(self._select_val("char", "open_chests"))),
            "fill_shared_stash_first": bool(int(self._select_val("char", "fill_shared_stash_first"))),
            "pre_buff_every_run": int(self._select_val("char", "pre_buff_every_run")),
            "cta_available": bool(int(self._select_val("char", "cta_available"))),
            "weapon_switch": self._select_val("char", "weapon_switch"),
            "battle_orders": self._select_val("char", "battle_orders"),
            "battle_command": self._select_val("char", "battle_command"),
            "casting_frames": int(self._select_val("char", "casting_frames")),
            "attack_frames": float(self._select_val("char", "attack_frames")),
            "atk_len_arc": float(self._select_val("char", "atk_len_arc")),
            "atk_len_trav": float(self._select_val("char", "atk_len_trav")),
            "atk_len_pindle": float(self._select_val("char", "atk_len_pindle")),
            "necro_wait": float(self._select_val("char", "necro_wait")),
            "atk_len_eldritch": float(self._select_val("char", "atk_len_eldritch")),
            "atk_len_shenk": float(self._select_val("char", "atk_len_shenk")),
            "atk_len_nihlathak": float(self._select_val("char", "atk_len_nihlathak")),
            "atk_len_diablo_vizier": float(self._select_val("char", "atk_len_diablo_vizier")),
            "atk_len_diablo_deseis": float(self._select_val("char", "atk_len_diablo_deseis")),
            "atk_len_diablo_infector": float(self._select_val("char", "atk_len_diablo_infector")),
            "atk_len_diablo": float(self._select_val("char", "atk_len_diablo")),
            "atk_len_cs_trashmobs": float(self._select_val("char", "atk_len_cs_trashmobs")),
            "runs_per_stash": False if not self._select_val("char", "runs_per_stash") else int(self._select_val("char", "runs_per_stash")),
            "runs_per_repair": False if not self._select_val("char", "runs_per_repair") else int(self._select_val("char", "runs_per_repair")),
            "gamble_items": False if not self._select_val("char", "gamble_items") else self._select_val("char", "gamble_items").replace(" ","").split(","),
            "random_sleep_range": float(self._select_val("char", "random_sleep_range")),
            "shop_anya": bool(int(self._select_val("char", "shop_anya"))),
            "sell_junk": bool(int(self._select_val("char", "sell_junk"))),
            "enable_no_pickup": bool(int(self._select_val("char", "enable_no_pickup"))),
            "edge_available": bool(int(self._select_val("char", "edge_available"))),
            "safer_routines": bool(int(self._select_val("char", "safer_routines"))),
            "mob_detection": bool(int(self._select_val("char", "mob_detection"))),
            "dia_town_visits": bool(int(self._select_val("char", "dia_town_visits"))),
            "dia_kill_trash": bool(int(self._select_val("char", "dia_kill_trash"))),
            "dia_leecher_tp_cs": bool(int(self._select_val("char", "dia_leecher_tp_cs"))),
            "dia_leecher_tp_pent": bool(int(self._select_val("char", "dia_leecher_tp_pent"))),
        }
        # Sorc base config
        sorc_base_cfg = dict(self.configs["config"]["parser"]["sorceress"])
        if "sorceress" in self.configs["custom"]["parser"]:
            sorc_base_cfg.update(dict(self.configs["custom"]["parser"]["sorceress"]))
        # blizz sorc
        self.blizz_sorc = dict(self.configs["config"]["parser"]["blizz_sorc"])
        if "blizz_sorc" in self.configs["custom"]["parser"]:
            self.blizz_sorc.update(dict(self.configs["custom"]["parser"]["blizz_sorc"]))
        self.blizz_sorc.update(sorc_base_cfg)
        # light sorc
        self.light_sorc = dict(self.configs["config"]["parser"]["light_sorc"])
        if "light_sorc" in self.configs["custom"]["parser"]:
            self.light_sorc.update(dict(self.configs["custom"]["parser"]["light_sorc"]))
        self.light_sorc.update(sorc_base_cfg)
        # nova sorc
        self.nova_sorc = dict(self.configs["config"]["parser"]["nova_sorc"])
        if "nova_sorc" in self.configs["custom"]["parser"]:
            self.nova_sorc.update(dict(self.configs["custom"]["parser"]["nova_sorc"]))
        self.nova_sorc.update(sorc_base_cfg)
        # hydra sorc
        self.hydra_sorc = dict(self.configs["config"]["parser"]["hydra_sorc"])
        if "hydra_sorc" in self.configs["custom"]["parser"]:
            self.hydra_sorc.update(dict(self.configs["custom"]["parser"]["hydra_sorc"]))
        self.hydra_sorc.update(sorc_base_cfg)

        # Paladin base config
        paladin_base_cfg = dict(self.configs["config"]["parser"]["paladin"])
        if "paladin" in self.configs["custom"]["parser"]:
            paladin_base_cfg.update(dict(self.configs["custom"]["parser"]["paladin"]))
        # Hammerdin config
        self.hammerdin = self.configs["config"]["parser"]["hammerdin"]
        if "hammerdin" in self.configs["custom"]["parser"]:
            self.hammerdin.update(self.configs["custom"]["parser"]["hammerdin"])
        self.hammerdin.update(paladin_base_cfg)
        # FoHdin config
        self.fohdin = dict(self.configs["config"]["parser"]["fohdin"])
        if "fohdin" in self.configs["custom"]["parser"]:
            self.fohdin.update(self.configs["custom"]["parser"]["fohdin"])
        self.fohdin.update(paladin_base_cfg)

        # Assassin config
        self.trapsin = self.configs["config"]["parser"]["trapsin"]
        if "trapsin" in self.configs["custom"]["parser"]:
            self.trapsin.update(self.configs["custom"]["parser"]["trapsin"])

        # Barbarian config
        self.barbarian = self.configs["config"]["parser"]["barbarian"]
        if "barbarian" in self.configs["custom"]["parser"]:
            self.barbarian.update(self.configs["custom"]["parser"]["barbarian"])
        self.barbarian = dict(self.barbarian)
        self.barbarian["cry_frequency"] = float(self.barbarian["cry_frequency"])

        # Basic config
        self.basic = self.configs["config"]["parser"]["basic"]
        if "basic" in self.configs["custom"]["parser"]:
            self.basic.update(self.configs["custom"]["parser"]["basic"])

        # Basic Ranged config
        self.basic_ranged = self.configs["config"]["parser"]["basic_ranged"]
        if "basic_ranged" in self.configs["custom"]["parser"]:
            self.basic_ranged.update(self.configs["custom"]["parser"]["basic_ranged"])

        # Necro config
        self.necro = self.configs["config"]["parser"]["necro"]
        if "necro" in self.configs["custom"]["parser"]:
            self.necro.update(self.configs["custom"]["parser"]["necro"])

        self.poison_necro = self.configs["config"]["parser"]["poison_necro"]
        if "poison_necro" in self.configs["custom"]["parser"]:
            self.poison_necro.update(self.configs["custom"]["parser"]["poison_necro"])

        self.bone_necro = self.configs["config"]["parser"]["bone_necro"]
        if "bone_necro" in self.configs["custom"]["parser"]:
            self.bone_necro.update(self.configs["custom"]["parser"]["bone_necro"])

        self.advanced_options = {
            "pathing_delay_factor": min(max(int(self._select_val("advanced_options", "pathing_delay_factor")), 1), 10),
            "message_headers": self._select_val("advanced_options", "message_headers"),
            "message_body_template": self._select_val("advanced_options", "message_body_template"),
            "graphic_debugger_layer_creator": bool(int(self._select_val("advanced_options", "graphic_debugger_layer_creator"))),
            "logg_lvl": self._select_val("advanced_options", "logg_lvl"),
            "exit_key": self._select_val("advanced_options", "exit_key"),
            "resume_key": self._select_val("advanced_options", "resume_key"),
            "auto_settings_key": self._select_val("advanced_options", "auto_settings_key"),
            "restore_settings_from_backup_key": self._select_val("advanced_options", "restore_settings_from_backup_key"),
            "settings_backup_key": self._select_val("advanced_options", "settings_backup_key"),
            "graphic_debugger_key": self._select_val("advanced_options", "graphic_debugger_key"),
            "hwnd_window_title": _default_iff(Config()._select_val("advanced_options", "hwnd_window_title"), ''),
            "hwnd_window_process": _default_iff(Config()._select_val("advanced_options", "hwnd_window_process"), ''),
            "window_client_area_offset": tuple(map(int, Config()._select_val("advanced_options", "window_client_area_offset").split(","))),
            "ocr_during_pickit": bool(int(self._select_val("advanced_options", "ocr_during_pickit"))),
            "launch_options": self._select_val("advanced_options", "launch_options").replace("<name>", only_lowercase_letters(self.general["name"].lower())),
            "override_capabilities": _default_iff(Config()._select_optional("advanced_options", "override_capabilities"), ""),
            "gather_mob_screenshots_for_modelling": _default_iff(Config()._select_optional("advanced_options", "gather_mob_screenshots_for_modelling"), ""),
        }

        self.colors = {}
        for key in self.configs["game"]["parser"]["colors"]:
            self.colors[key] = np.split(np.array([int(x) for x in self._select_val("colors", key).split(",")]), 2)

        self.ui_pos = {}
        for key in self.configs["game"]["parser"]["ui_pos"]:
            self.ui_pos[key] = int(self._select_val("ui_pos", key))

        self.ui_roi = {}
        for key in self.configs["game"]["parser"]["ui_roi"]:
            self.ui_roi[key] = np.array([int(x) for x in self._select_val("ui_roi", key).split(",")])
        open_width = int(self.ui_pos["slot_width"] * self.char["num_loot_columns"])
        # calc roi for restricted inventory area
        self.ui_roi["restricted_inventory_area"] = self.ui_roi["right_inventory"].copy()
        self.ui_roi["restricted_inventory_area"][0] += open_width # left
        self.ui_roi["restricted_inventory_area"][2] -= open_width # width
        # calc roi for open inventory area
        self.ui_roi["open_inventory_area"] = self.ui_roi["right_inventory"].copy()
        self.ui_roi["open_inventory_area"][2] = open_width # width

        self.path = {}
        for key in self.configs["game"]["parser"]["path"]:
            self.path[key] = np.reshape(np.array([int(x) for x in self._select_val("path", key).split(",")]), (-1, 2))

        self.shop = {
            "shop_claws": bool(int(self._select_val("claws", "shop_claws"))),
            "shop_skills_ias_gloves": bool(int(self._select_val("gloves", "shop_skills_ias_gloves"))),
            "shop_jewelers_archon_plate": bool(int(self._select_val("armors", "shop_jewelers_archon_plate"))),
            "shop_hammerdin_scepters": bool(int(self._select_val("scepters", "shop_hammerdin_scepters"))),
            "speed_factor": float(self._select_val("scepters", "speed_factor")),
            "apply_pather_adjustment": bool(int(self._select_val("scepters", "apply_pather_adjustment"))),
        }
        stash_destination_str = self._select_val("transmute","stash_destination")
        transmute_str = self._select_val("transmute","transmute")
        self.configs["transmute"]["parser"] = {
            "stash_destination": [int(x.strip()) for x in stash_destination_str.split(",")],
            "transmute_every_x_game": self._select_val("transmute","transmute_every_x_game"),
            "transmute": [x.strip() for x in transmute_str.split(",")],
        }

if __name__ == "__main__":
    from copy import deepcopy
    config = Config()
