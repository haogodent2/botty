from dataclasses import dataclass
import time
import random
import ctypes
import numpy as np
from copy import deepcopy
import unicodedata
import re

from pyparsing import Regex

from logger import Logger
from remote_grabber import remote_grabber
import cv2
import os
from math import cos, sin, dist
import subprocess
from win32con import HWND_TOPMOST, SWP_NOMOVE, SWP_NOSIZE, HWND_NOTOPMOST, WM_CLOSE
from win32gui import GetWindowText, SetWindowPos, EnumWindows, GetClientRect, ClientToScreen, GetForegroundWindow, SetForegroundWindow
from win32api import PostMessage
from win32console import GetConsoleWindow
from win32process import GetWindowThreadProcessId
import psutil

from rapidfuzz.process import extractOne
from rapidfuzz.string_metric import levenshtein

@dataclass
class WindowSpec:
    title_regex: 'str | None' = None
    process_name_regex: 'str | None' = None

    def match(self, hwnd) -> bool:
        result = True
        if self.title_regex is not None:
            result = result and Regex(self.title_regex).matches(GetWindowText(hwnd))
        if self.process_name_regex is not None:
            _, process_id = GetWindowThreadProcessId(hwnd)
            if process_id > 0:
                result = result and Regex(self.process_name_regex).matches(psutil.Process(process_id).name())
        if self.title_regex is None and self.process_name_regex is None:
            result = False
        return result

d2r_hwnd = None
def close_down_bnet_launcher():
    subprocess.call(["taskkill","/F","/IM","Battle.net.exe"], stderr=subprocess.DEVNULL)

def find_d2r_window(spec: WindowSpec, offset = (0, 0)) -> tuple[int, int]:
    offset_x, offset_y = offset
    if os.name == 'nt':
        window_list = []
        EnumWindows(lambda w, l: l.append(w), window_list)
        for hwnd in window_list:
            if spec.match(hwnd):
                global d2r_hwnd
                d2r_hwnd = hwnd
                left, top, right, bottom = GetClientRect(hwnd)
                (left, top), (right, bottom) = ClientToScreen(hwnd, (left, top)), ClientToScreen(hwnd, (right, bottom))
                return (left + offset_x, top + offset_y)
    return None

def set_d2r_always_on_top():
    if os.name == 'nt':
        if d2r_hwnd is None:
            windows_list = []
            EnumWindows(lambda w, l: l.append((w, GetWindowText(w))), windows_list)
            for w in windows_list:
                if w[1] == "Diablo II: Resurrected":
                    hwnd = w[1]
                    break
            else:
                return
        else:
            hwnd = d2r_hwnd
        SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        print("Set D2R to be always on top")
        SetForegroundWindow(hwnd)
    else:
        print('OS not supported, unable to set D2R always on top')

def get_d2r_hwnd():
    windows_list = []
    EnumWindows(lambda w, l: l.append((w, GetWindowText(w))), windows_list)
    for w in windows_list:
        if w[1] == "Diablo II: Resurrected":
            return w[1]
        else:
            return


def restore_d2r_window_visibility():
    if os.name == 'nt':
        hwnd = get_d2r_hwnd()
        SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        print("Restored D2R window visibility")
    else:
        print('OS not supported, unable to set D2R always on top')

def close_down_d2():
    if remote_grabber:
        remote_grabber.close_window()
        restore_d2r_window_visibility()
    else:
        if not d2r_hwnd:
            window_list = []
            EnumWindows(lambda w, l: l.append(w), window_list)
            for hwnd in window_list:
                _, process_id = GetWindowThreadProcessId(hwnd)
                if "D2R.exe" in psutil.Process(process_id).name():
                    d2r_hwnd = hwnd
                    break
        Logger.info(f"Sending WM_CLOSE to HWND {hwnd}...")
        PostMessage(hwnd, WM_CLOSE, 0, 0)

def is_d2r_window_on_focus():
    if os.name == 'nt':
        if d2r_hwnd is None:
            return True
        hwnd = GetForegroundWindow()
        if hwnd == d2r_hwnd:
            return True
        else:
            Logger.info(f"d2r_hwnd={d2r_hwnd}, current foreground={hwnd}")
    return False

def is_console_on_focus():
    if os.name == 'nt':
        if GetConsoleWindow() == GetForegroundWindow():
            return True
    return False

def wait(min_seconds, max_seconds = None):
    if max_seconds is None:
        max_seconds = min_seconds
    time.sleep(random.uniform(min_seconds, max_seconds))
    return

def kill_thread(thread):
    thread_id = thread.ident
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(SystemExit))
    if res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
        Logger.error('Exception raise failure')

def cut_roi(img, roi):
    x, y, w, h = roi
    return img[y:y+h, x:x+w]

def mask_by_roi(img, roi, type: str = "regular"):
    x, y, w, h = roi
    if type == "regular":
        masked = np.zeros(img.shape, dtype=np.uint8)
        masked[y:y+h, x:x+w] = img[y:y+h, x:x+w]
    elif type == "inverse":
        masked = cv2.rectangle(img, (x, y), (x+w, y+h), (0, 0, 0), -1)
    else:
        return None
    return masked

def is_in_roi(roi: list[float], pos: tuple[float, float]):
    x, y, w, h = roi
    is_in_x_range = x < pos[0] < x + w
    is_in_y_range = y < pos[1] < y + h
    return is_in_x_range and is_in_y_range

def trim_black(image):
    y_nonzero, x_nonzero = np.nonzero(image)
    roi = np.min(x_nonzero), np.min(y_nonzero), np.max(x_nonzero) - np.min(x_nonzero), np.max(y_nonzero) - np.min(y_nonzero)
    img = image[np.min(y_nonzero):np.max(y_nonzero), np.min(x_nonzero):np.max(x_nonzero)]
    return img, roi

def erode_to_black(img: np.ndarray, threshold: int = 14):
    # Cleanup image with erosion image as marker with morphological reconstruction
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)[1]
    kernel = np.ones((3, 3), np.uint8)
    marker = thresh.copy()
    marker[1:-1, 1:-1] = 0
    while True:
        tmp = marker.copy()
        marker = cv2.dilate(marker, kernel)
        marker = cv2.min(thresh, marker)
        difference = cv2.subtract(marker, tmp)
        if cv2.countNonZero(difference) <= 0:
            break
    mask_r = cv2.bitwise_not(marker)
    mask_color_r = cv2.cvtColor(mask_r, cv2.COLOR_GRAY2BGR)
    img = cv2.bitwise_and(img, mask_color_r)
    return img

def roi_center(roi: list[float] = None):
    x, y, w, h = roi
    return round(x + w/2), round(y + h/2)

def color_filter(img, color_range):
    color_ranges=[]
    # ex: [array([ -9, 201,  25]), array([ 9, 237,  61])]
    if color_range[0][0] < 0:
        lower_range = deepcopy(color_range)
        lower_range[0][0] = 0
        color_ranges.append(lower_range)
        upper_range = deepcopy(color_range)
        upper_range[0][0] = 180 + color_range[0][0]
        upper_range[1][0] = 180
        color_ranges.append(upper_range)
    # ex: [array([ 170, 201,  25]), array([ 188, 237,  61])]
    elif color_range[1][0] > 180:
        upper_range = deepcopy(color_range)
        upper_range[1][0] = 180
        color_ranges.append(upper_range)
        lower_range = deepcopy(color_range)
        lower_range[0][0] = 0
        lower_range[1][0] = color_range[1][0] - 180
        color_ranges.append(lower_range)
    else:
        color_ranges.append(color_range)
    color_masks = []
    for color_range in color_ranges:
        hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_img, color_range[0], color_range[1])
        color_masks.append(mask)
    color_mask = np.bitwise_or.reduce(color_masks) if len(color_masks) > 0 else color_masks[0]
    filtered_img = cv2.bitwise_and(img, img, mask=color_mask)
    return color_mask, filtered_img

def hms(seconds: int):
    seconds = int(seconds)
    h = seconds // 3600
    m = seconds % 3600 // 60
    s = seconds % 3600 % 60
    return '{:02d}:{:02d}:{:02d}'.format(h, m, s)

def load_template(path):
    if os.path.isfile(path):
        try:
            template_img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            return template_img
        except Exception as e:
            print(e)
            raise ValueError(f"Could not load template: {path}")
    else:
        Logger.error(f"Template does not exist: {path}")
    return None

def alpha_to_mask(img: np.ndarray):
    # create a mask from template where alpha == 0
    if img.shape[2] == 4:
        if np.min(img[:, :, 3]) == 0:
            _, mask = cv2.threshold(img[:,:,3], 1, 255, cv2.THRESH_BINARY)
            return mask
    return None

def list_files_in_folder(path: str):
    r = []
    for root, _, files in os.walk(path):
        for name in files:
            r.append(os.path.join(root, name))
    return r

def rotate_vec(vec: np.ndarray, deg: float) -> np.ndarray:
    theta = np.deg2rad(deg)
    rot_matrix = np.array([[cos(theta), -sin(theta)], [sin(theta), cos(theta)]])
    return np.dot(rot_matrix, vec)

def unit_vector(vec: np.ndarray) -> np.ndarray:
    return vec / dist(vec, (0, 0))

def image_is_equal(img1: np.ndarray, img2: np.ndarray) -> bool:
    shape_equal = img1.shape == img2.shape
    if not shape_equal:
        Logger.debug("image_is_equal: Image shape is not equal")
        return False
    return not(np.bitwise_xor(img1, img2).any())

def arc_spread(cast_dir: tuple[float,float], spread_deg: float=10, radius_spread: tuple[float, float] = [.95, 1.05]):
    """
        Given an x,y vec (target), generate a new target that is the same vector but rotated by +/- spread_deg/2
    """
    cast_dir = np.array(cast_dir)
    length = dist(cast_dir, (0, 0))
    adj = (radius_spread[1] - radius_spread[0])*random.random() + radius_spread[0]
    rot = spread_deg*(random.random() - .5)
    return rotate_vec(unit_vector(cast_dir)*(length+adj), rot)


@dataclass
class BestMatchResult:
    match: str
    score: float
    score_normalized: float

def find_best_match(in_str: str, str_list: list[str]) -> BestMatchResult:
    best_match, best_lev, _ = extractOne(in_str, str_list, scorer=levenshtein)
    best_lev_normalized = 1 - best_lev / max(1, len(in_str))
    return BestMatchResult(best_match, best_lev, best_lev_normalized)

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')
