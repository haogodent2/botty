import keyboard
from ui import skills
import time, random, math
from utils.custom_mouse import mouse
from char import IChar, CharacterCapabilities
from pather import Pather
from logger import Logger
from config import Config
from utils.misc import wait
from screen import convert_abs_to_screen, convert_abs_to_monitor, convert_screen_to_monitor, grab
from pather import Pather
from automap_finder import toggle_automap
#import cv2 #for Diablo
from item.pickit import PickIt #for Diablo

class Paladin(IChar):
    def __init__(self, skill_hotkeys: dict, pather: Pather, pickit: PickIt):
        Logger.info("Setting up Paladin")
        super().__init__(skill_hotkeys)
        self._pather = pather
        self._pickit = pickit #for Diablo
        self._picked_up_items = False #for Diablo

    def pre_buff(self):
        if Config().char["cta_available"]:
            self._pre_buff_cta()
        keyboard.send(self._skill_hotkeys["holy_shield"])
        wait(0.04, 0.1)
        mouse.click(button="right")
        wait(self._cast_duration, self._cast_duration + 0.06)

    def pre_move(self):
        # select teleport if available
        super().pre_move()
        # in case teleport hotkey is not set or teleport can not be used, use vigor if set
        should_cast_vigor = self._skill_hotkeys["vigor"] and not skills.is_right_skill_selected(["VIGOR"])
        can_teleport = self.capabilities.can_teleport_natively and skills.is_right_skill_active()
        if should_cast_vigor and not can_teleport:
            keyboard.send(self._skill_hotkeys["vigor"])
            wait(0.15, 0.25)

    def _log_cast(self, skill_name: str, cast_pos_abs: tuple[float, float], spray: int, min_duration: float, aura: str):
        msg = f"Casting skill {skill_name}"
        if cast_pos_abs:
            msg += f" at screen coordinate {convert_abs_to_screen(cast_pos_abs)}"
        if spray:
            msg += f" with spray of {spray}"
        if min_duration:
            msg += f" for {round(min_duration, 1)}s"
        if aura:
            msg += f" with {aura} active"
        Logger.debug(msg)

    def _click_cast(self, cast_pos_abs: tuple[float, float], spray: int, mouse_click_type: str = "left"):
        if cast_pos_abs:
            x = cast_pos_abs[0]
            y = cast_pos_abs[1]
            if spray:
                x += (random.random() * 2 * spray - spray)
                y += (random.random() * 2 * spray - spray)
            pos_m = convert_abs_to_monitor((x, y))
            mouse.move(*pos_m, delay_factor=[0.1, 0.2])
            wait(0.06, 0.08)
        mouse.press(button = mouse_click_type)
        wait(0.06, 0.08)
        mouse.release(button = mouse_click_type)

    def _cast_skill_with_aura(self, skill_name: str, cast_pos_abs: tuple[float, float] = None, spray: int = 0, min_duration: float = 0, aura: str = ""):

        # set aura if needed
        if aura:
            self._select_skill(aura, mouse_click_type = "right")

        # ensure character stands still
        keyboard.send(Config().char["stand_still"], do_release=False)

        # cast left hand skill
        start = time.time()
        if min_duration:
            while (time.time() - start) <= min_duration:
                self._click_cast(cast_pos_abs, spray)
        else:
            self._click_cast(cast_pos_abs, spray)

        # release stand still key
        keyboard.send(Config().char["stand_still"], do_press=False)

    def _cast_skill_no_aura(self, skill_name: str, cast_pos_abs: tuple[float, float] = None, spray: int = 0, min_duration: float = 0):
    #self._log_cast(skill_name, cast_pos_abs, spray, min_duration, aura)

        # ensure character stands still
        keyboard.send(Config().char["stand_still"], do_release=False)

        # set right hand skill
        self._select_skill(skill_name, mouse_click_type = "right")

        wait(0.04)

        # cast right hand skill
        start = time.time()
        if min_duration:
            while (time.time() - start) <= min_duration:
                self._click_cast(cast_pos_abs, spray, "right")
        else:
            self._click_cast(cast_pos_abs, spray, "right")

        # release stand still key
        keyboard.send(Config().char["stand_still"], do_press=False)


    def _charge_to(self, pos: tuple[float, float]):
        if self._skill_hotkeys["charge"]:
            Logger.debug(f"Charge to {pos}")
            self._select_skill("vigor", "right")
            keyboard.send(self._skill_hotkeys["charge"])
            self._set_active_skill("left", "charge")
            pos_m = convert_abs_to_monitor(pos)
            mouse.move(*pos_m)
            keyboard.press(Config().char["stand_still"])
            wait(0.05,0.07)
            mouse.press("left")
            wait(0.12,0.15)
            mouse.release("left")
            keyboard.release(Config().char["stand_still"])

    def _activate_redemption_aura(self, delay = [0.6, 0.8]):
        self._select_skill("redemption", delay=delay)

    def _activate_cleanse_aura(self, delay = [0.3, 0.4]):
        self._select_skill("cleansing", delay=delay)

    def _activate_cleanse_redemption(self):
        self._activate_cleanse_aura()
        self._activate_redemption_aura()

    def run_to_cs(self) -> bool:
        # Charge to first jumping spot
        self._select_skill("vigor")
        if not self._select_skill("charge"):
            return False
        x, y = convert_screen_to_monitor((1270, 30))
        mouse.move(x, y)
        keyboard.send(Config().char["stand_still"], do_release=False)
        start_time = time.time()
        mouse.press("left")
        toggle_automap(True)
        prev_dist = 1000
        while time.time() - start_time < 5.0:
            pos = self._pather.find_abs_node_pos(1602, grab(), threshold=0.9, grayscale=False)
            if pos is not None:
                new_dist = math.dist(pos, (0,0))
                if prev_dist <= new_dist or new_dist < 30:
                    break
                prev_dist = new_dist
            time.sleep(0.1)
        mouse.release("left")
        keyboard.send(Config().char["stand_still"], do_press=False)
        time.sleep(0.25)

        # Teleport to cs entrance
        path_to_cs_entrance = [convert_abs_to_screen((620, -350))] * 7
        return self._pather.traverse_nodes_fixed(path_to_cs_entrance, self)
