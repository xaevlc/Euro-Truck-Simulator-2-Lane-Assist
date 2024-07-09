from ETS2LA.backend.globalServer import SendCrashReport
from ETS2LA.plugins.runner import PluginRunner
import ETS2LA.backend.settings as settings
import ETS2LA.backend.controls as controls
import ETS2LA.backend.console as console
import ETS2LA.backend.sounds as sounds
import ETS2LA.backend.variables as variables

import numpy as np
import subprocess
import traceback
import ctypes
import time
import cv2
import mss
import os

try:
    from torchvision import transforms
    from bs4 import BeautifulSoup
    import threading
    import requests
    import torch
    TorchAvailable = True
except:
    TorchAvailable = False
    exc = traceback.format_exc()
    SendCrashReport("NavigationDetection - PyTorch import error.", str(exc))
    print("\033[91m" + f"NavigationDetection - PyTorch import Error:\n" + "\033[0m" + str(exc))
    console.RestoreConsole()


runner:PluginRunner = None

sct = mss.mss()
monitor = sct.monitors[(settings.Get("NavigationDetection", ["ScreenCapture", "display"], 0) + 1)]
screen_x = monitor["left"]
screen_y = monitor["top"]
screen_width = monitor["width"]
screen_height = monitor["height"]

controls.RegisterKeybind("Lane change to the left",
                         notBoundInfo="Bind this if you dont want to use the indicators\nto change lanes with the NavigationDetection.",
                         description="Bind this if you dont want to use the indicators\nto change lanes with the NavigationDetection.")

controls.RegisterKeybind("Lane change to the right",
                         notBoundInfo="Bind this if you dont want to use the indicators\nto change lanes with the NavigationDetection.",
                         description="Bind this if you dont want to use the indicators\nto change lanes with the NavigationDetection.")


def ToggleSteering(state:bool, *args, **kwargs):
    global enabled
    enabled = state
    sounds.Play('start' if state else 'end')

############################################################################################################################    
# Settings
############################################################################################################################
def Initialize():
    global Steering
    global ShowImage
    global TruckSimAPI
    global SDKController
    global ScreenCapture

    global UseAI
    global UseCUDA
    global AIDevice
    global LoadAILabel
    global LoadAIProgress

    global map_topleft
    global map_bottomright
    global arrow_topleft
    global arrow_bottomright

    global arrow_percentage

    global navigationsymbol_x
    global navigationsymbol_y

    global enabled
    global offset
    global lefthand_traffic

    global fuel_update_timer
    global fuel_total
    global fuel_current
    global fuel_percentage

    global check_map_timer
    global do_zoom
    global do_blocked
    global mod_enabled
    global allow_playsound
    global allow_playsound_timer

    global controls_last_left
    global controls_last_right

    global left_x_lane
    global right_x_lane
    global left_x_turn
    global right_x_turn
    global left_x_turndrive
    global right_x_turndrive
    global approve_upper_y_left
    global approve_lower_y_left
    global approve_upper_y_right
    global approve_lower_y_right
    
    global detection_offset_lane_y

    global turnincoming_detected
    global turnincoming_direction
    global turnincoming_last_detected

    global indicator_last_left
    global indicator_last_right
    global indicator_left_wait_for_response
    global indicator_right_wait_for_response
    global indicator_left_response_timer
    global indicator_right_response_timer
    global indicator_enable_left
    global indicator_enable_right
    global indicator_changed_by_code

    global lanechanging_do_lane_changing
    global lanechanging_speed
    global lanechanging_width
    global lanechanging_current_lane
    global lanechanging_final_offset

    Steering = runner.modules.Steering
    ShowImage = runner.modules.ShowImage
    TruckSimAPI = runner.modules.TruckSimAPI
    SDKController = runner.modules.SDKController
    ScreenCapture = runner.modules.ScreenCapture

    Steering.OFFSET = 0
    Steering.SMOOTH_TIME = 0.5
    Steering.IGNORE_SMOOTH = False
    Steering.SENSITIVITY = 0.65

    if 'UseAI' in globals():
        if UseAI == False and settings.Get("NavigationDetection", "UseNavigationDetectionAI", False) == True:
            if TorchAvailable == True:
                LoadAIModel()
            else:
                print("TrafficLightDetectionAI not available due to missing dependencies.")
                console.RestoreConsole()
    elif settings.Get("NavigationDetection", "UseNavigationDetectionAI", False) == True:
        if TorchAvailable == True:
            LoadAIModel()
        else:
            print("TrafficLightDetectionAI not available due to missing dependencies.")
            console.RestoreConsole()
    UseAI = settings.Get("NavigationDetection", "UseNavigationDetectionAI", False)
    UseCUDA = settings.Get("NavigationDetection", "TryCUDA", False)
    AIDevice = torch.device('cuda' if torch.cuda.is_available() and UseCUDA == True else 'cpu')
    LoadAILabel = "Loading..."
    LoadAIProgress = 0

    map_topleft = settings.Get("NavigationDetection", "map_topleft", "unset")
    map_bottomright = settings.Get("NavigationDetection", "map_bottomright", "unset")
    arrow_topleft = settings.Get("NavigationDetection", "arrow_topleft", "unset")
    arrow_bottomright = settings.Get("NavigationDetection", "arrow_bottomright", "unset")
    arrow_percentage = settings.Get("NavigationDetection", "arrow_percentage", "unset")

    if map_topleft == "unset":
        map_topleft = None
    if map_bottomright == "unset":
        map_bottomright = None
    if arrow_topleft == "unset":
        arrow_topleft = None
    if arrow_bottomright == "unset":
        arrow_bottomright = None
    if arrow_percentage == "unset":
        arrow_percentage = None
    
    if arrow_topleft != None and arrow_bottomright != None and map_topleft != None and map_bottomright != None:
        navigationsymbol_x = round((arrow_topleft[0] + arrow_bottomright[0]) / 2 - map_topleft[0])
        navigationsymbol_y = round((arrow_topleft[1] + arrow_bottomright[1]) / 2 - map_topleft[1])
        ScreenCapture.CreateCam(CamSetupDisplay = settings.Get("NavigationDetection", ["ScreenCapture", "display"], 0))
        ScreenCapture.monitor_x1 = map_topleft[0]
        ScreenCapture.monitor_y1 = map_topleft[1]
        ScreenCapture.monitor_x2 = map_bottomright[0]
        ScreenCapture.monitor_y2 = map_bottomright[1]
    else:
        navigationsymbol_x = 0
        navigationsymbol_y = 0

    enabled = True
    offset = settings.Get("NavigationDetection", "LaneOffset", 0)
    lefthand_traffic = settings.Get("NavigationDetection", "LeftHandTraffic", False)

    fuel_update_timer = 0
    fuel_total = 0
    fuel_current = 0
    fuel_percentage = 100

    check_map_timer = 0
    do_zoom = False
    do_blocked = False
    mod_enabled = False
    allow_playsound = False
    allow_playsound_timer = time.time()

    controls_last_left = False
    controls_last_right = False

    left_x_lane = 0
    right_x_lane = 0
    left_x_turn = 0
    right_x_turn = 0
    left_x_turndrive = 0
    right_x_turndrive = 0
    approve_upper_y_left = 0
    approve_lower_y_left = 0
    approve_upper_y_right = 0
    approve_lower_y_right = 0

    detection_offset_lane_y = 0

    turnincoming_detected = False
    turnincoming_direction = None
    turnincoming_last_detected = 0

    indicator_last_left = False
    indicator_last_right = False
    indicator_left_wait_for_response = False
    indicator_right_wait_for_response = False
    indicator_left_response_timer = 0
    indicator_right_response_timer = 0
    indicator_enable_left = False
    indicator_enable_right = False
    indicator_changed_by_code = True

    lanechanging_do_lane_changing = settings.Get("NavigationDetection", "LaneChanging", True)
    lanechanging_speed = settings.Get("NavigationDetection", "LaneChangeSpeed", 1)
    lanechanging_width = settings.Get("NavigationDetection", "LaneChangeWidth", 10)
    lanechanging_current_lane = 0
    lanechanging_final_offset = 0


def manual_setup():
    subprocess.Popen(["python", os.path.join(variables.PATH, "ETS2LA", "plugins", "NavigationDetection", "manual_setup.py")])


def automatic_setup():
    subprocess.Popen(["python", os.path.join(variables.PATH, "ETS2LA", "plugins", "NavigationDetection", "automatic_setup.py")])


def get_text_size(text="NONE", text_width=100, max_text_height=100):
    fontscale = 1
    textsize, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fontscale, 1)
    width_current_text, height_current_text = textsize
    max_count_current_text = 3
    while width_current_text != text_width or height_current_text > max_text_height:
        fontscale *= min(text_width / textsize[0], max_text_height / textsize[1])
        textsize, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fontscale, 1)
        max_count_current_text -= 1
        if max_count_current_text <= 0:
            break
    thickness = round(fontscale * 2)
    if thickness <= 0:
        thickness = 1
    return text, fontscale, thickness, textsize[0], textsize[1]


def preprocess_image(image):
    image = np.array(image)
    image = cv2.resize(image, (IMG_WIDTH, IMG_HEIGHT))
    image = np.array(image, dtype=np.float32) / 255.0
    transform = transforms.Compose([
        transforms.ToTensor(),
    ])
    return transform(image).unsqueeze(0).to(AIDevice)


def HandleCorruptedAIModel():
    DeleteAllAIModels()
    CheckForAIModelUpdates()
    while AIModelUpdateThread.is_alive(): time.sleep(0.1)
    time.sleep(0.5)
    if TorchAvailable == True:
        LoadAIModel()
    else:
        print("NavigationDetectionAI not available due to missing dependencies.")
        console.RestoreConsole()


def LoadAIModel():
    try:
        def LoadAIModelThread():
            try:
                global LoadAILabel
                global LoadAIProgress
                global AIModel
                global AIModelLoaded
                global IMG_WIDTH
                global IMG_HEIGHT

                CheckForAIModelUpdates()
                while AIModelUpdateThread.is_alive(): time.sleep(0.1)

                if GetAIModelName() == []:
                    return

                LoadAIProgress = 0
                LoadAILabel = "Loading the AI model..."

                print("\033[92m" + f"Loading the AI model..." + "\033[0m")

                IMG_WIDTH = GetAIModelProperties()[2]
                IMG_HEIGHT = GetAIModelProperties()[3]

                ModelFileCorrupted = False

                try:
                    AIModel = torch.jit.load(os.path.join(f"{variables.PATH}ETS2LA/plugins/NavigationDetection/AIModel", GetAIModelName()), map_location=AIDevice)
                    AIModel.eval()
                except:
                    ModelFileCorrupted = True

                if ModelFileCorrupted == False:
                    print("\033[92m" + f"Successfully loaded the AI model!" + "\033[0m")
                    AIModelLoaded = True
                    LoadAIProgress = 100
                    LoadAILabel = "Successfully loaded the AI model!"
                else:
                    print("\033[91m" + f"Failed to load the AI model because the model file is corrupted." + "\033[0m")
                    AIModelLoaded = False
                    LoadAIProgress = 0
                    LoadAILabel = "ERROR! Your AI model file is corrupted!"
                    time.sleep(3)
                    HandleCorruptedAIModel()
            except Exception as e:
                exc = traceback.format_exc()
                SendCrashReport("NavigationDetection - Loading AI Error.", str(exc))
                console.RestoreConsole()
                print("\033[91m" + f"Failed to load the AI model." + "\033[0m")
                AIModelLoaded = False
                LoadAIProgress = 0
                LoadAILabel = "Failed to load the AI model!"

        global AIModelLoadThread
        AIModelLoadThread = threading.Thread(target=LoadAIModelThread, daemon=True)
        AIModelLoadThread.start()

    except Exception as ex:
        exc = traceback.format_exc()
        SendCrashReport("NavigationDetection - Error in function LoadAIModel.", str(exc))
        print(f"NavigationDetection - Error in function LoadAIModel: {ex}")
        console.RestoreConsole()
        print("\033[91m" + f"Failed to load the AI model." + "\033[0m")


def CheckForAIModelUpdates():
    try:
        def CheckForAIModelUpdatesThread():
            try:
                global LoadAILabel
                global LoadAIProgress

                try:
                    response = requests.get("https://huggingface.co/", timeout=3)
                    response = response.status_code
                except requests.exceptions.RequestException as ex:
                    response = None

                if response == 200:
                    LoadAIProgress = 0
                    LoadAILabel = "Checking for AI model updates..."

                    print("\033[92m" + f"Checking for AI model updates..." + "\033[0m")

                    if settings.Get("NavigationDetection", "LastUpdateCheck", 0) + 600 > time.time():
                        LoadAIProgress = 100
                        LoadAILabel = "Skipping AI model update check, last check was less than 10 minutes ago."
                        print("\033[92m" + f"Skipping AI model update check, last check was less than 10 minutes ago." + "\033[0m")
                        return
                    settings.Set("NavigationDetection", "LastUpdateCheck", round(time.time()))

                    url = "https://huggingface.co/Glas42/NavigationDetectionAI/tree/main/model"
                    response = requests.get(url)
                    soup = BeautifulSoup(response.content, 'html.parser')

                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if href.startswith('/Glas42/NavigationDetectionAI/blob/main/model'):
                            LatestAIModel = href.split("/")[-1]
                            break

                    CurrentAIModel = GetAIModelName()
                    if CurrentAIModel == "UNKNOWN":
                        CurrentAIModel = None

                    if str(LatestAIModel) != str(CurrentAIModel):
                        LoadAILabel = "Updating AI model..."
                        print("\033[92m" + f"Updating AI model..." + "\033[0m")
                        DeleteAllAIModels()
                        response = requests.get(f"https://huggingface.co/Glas42/NavigationDetectionAI/resolve/main/model/{LatestAIModel}?download=true", stream=True)
                        last_progress = 0
                        with open(os.path.join(f"{variables.PATH}ETS2LA/plugins/NavigationDetection/AIModel", f"{LatestAIModel}"), "wb") as modelfile:
                            total_size = int(response.headers.get('content-length', 0))
                            downloaded_size = 0
                            chunk_size = 1024
                            for data in response.iter_content(chunk_size=chunk_size):
                                downloaded_size += len(data)
                                modelfile.write(data)
                                progress = (downloaded_size / total_size) * 100
                                if round(last_progress) < round(progress):
                                    progress_mb = downloaded_size / (1024 * 1024)
                                    total_size_mb = total_size / (1024 * 1024)
                                    LoadAIProgress = progress
                                    LoadAILabel = f"Downloading AI model: {round(progress)}%"
                                    last_progress = progress
                        LoadAIProgress = 100
                        LoadAILabel = "Successfully updated AI model!"
                        print("\033[92m" + f"Successfully updated AI model!" + "\033[0m")
                    else:
                        LoadAIProgress = 100
                        LoadAILabel = "No AI model updates available!"
                        print("\033[92m" + f"No AI model updates available!" + "\033[0m")

                else:

                    console.RestoreConsole()
                    print("\033[91m" + f"Connection to https://huggingface.co/ is most likely not available in your country. Unable to check for AI model updates." + "\033[0m")
                    LoadAIProgress = 0
                    LoadAILabel = "Connection to https://huggingface.co/ is\nmost likely not available in your country.\nUnable to check for AI model updates."

            except Exception as ex:
                exc = traceback.format_exc()
                SendCrashReport("NavigationDetection - Error in function CheckForAIModelUpdatesThread.", str(exc))
                print(f"NavigationDetection - Error in function CheckForAIModelUpdatesThread: {ex}")
                console.RestoreConsole()
                print("\033[91m" + f"Failed to check for AI model updates or update the AI model." + "\033[0m")
                LoadAIProgress = 0
                LoadAILabel = "Failed to check for AI model updates or update the AI model."

        global AIModelUpdateThread
        AIModelUpdateThread = threading.Thread(target=CheckForAIModelUpdatesThread, daemon=True)
        AIModelUpdateThread.start()

    except Exception as ex:
        exc = traceback.format_exc()
        SendCrashReport("NavigationDetection - Error in function CheckForAIModelUpdates.", str(exc))
        print(f"NavigationDetection - Error in function CheckForAIModelUpdates: {ex}")
        console.RestoreConsole()
        print("\033[91m" + f"Failed to check for AI model updates or update the AI model." + "\033[0m")


def ModelFolderExists():
    try:
        if os.path.exists(f"{variables.PATH}ETS2LA/plugins/NavigationDetection/AIModel") == False:
            os.makedirs(f"{variables.PATH}ETS2LA/plugins/NavigationDetection/AIModel")
    except Exception as ex:
        exc = traceback.format_exc()
        SendCrashReport("NavigationDetection - Error in function ModelFolderExists.", str(exc))
        print(f"NavigationDetection - Error in function ModelFolderExists: {ex}")
        console.RestoreConsole()


def GetAIModelName():
    try:
        ModelFolderExists()
        for file in os.listdir(f"{variables.PATH}ETS2LA/plugins/NavigationDetection/AIModel"):
            if file.endswith(".pt"):
                return file
        return "UNKNOWN"
    except Exception as ex:
        exc = traceback.format_exc()
        SendCrashReport("NavigationDetection - Error in function GetAIModelName.", str(exc))
        print(f"NavigationDetection - Error in function GetAIModelName: {ex}")
        console.RestoreConsole()
        return "UNKNOWN"


def DeleteAllAIModels():
    try:
        ModelFolderExists()
        for file in os.listdir(f"{variables.PATH}ETS2LA/plugins/NavigationDetection/AIModel"):
            if file.endswith(".pt"):
                os.remove(os.path.join(f"{variables.PATH}ETS2LA/plugins/NavigationDetection/AIModel", file))
    except Exception as ex:
        exc = traceback.format_exc()
        SendCrashReport("NavigationDetection - Error in function DeleteAllAIModels.", str(exc))
        print(f"NavigationDetection - Error in function DeleteAllAIModels: {ex}")
        console.RestoreConsole()


def GetAIModelProperties():
    try:
        ModelFolderExists()
        if GetAIModelName() == "UNKNOWN":
            return ("UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN")
        else:
            string = str(GetAIModelName())
            if string != "UNKNOWN":
                epochs = int(string.split("EPOCHS-")[1].split("_")[0])
                batch = int(string.split("BATCH-")[1].split("_")[0])
                img_width = int(string.split("IMG_WIDTH-")[1].split("_")[0])
                img_height = int(string.split("IMG_HEIGHT-")[1].split("_")[0])
                img_count = int(string.split("IMG_COUNT-")[1].split("_")[0])
                training_time = string.split("TIME-")[1].split("_")[0]
                training_date = string.split("DATE-")[1].split(".")[0]
                return (epochs, batch, img_width, img_height, img_count, training_time, training_date)
            else:
                return ("UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN")
    except Exception as ex:
        exc = traceback.format_exc()
        SendCrashReport("NavigationDetection - Error in function GetAIModelProperties.", str(exc))
        print(f"NavigationDetection - Error in function GetAIModelProperties: {ex}")
        console.RestoreConsole()
        return ("UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN")


############################################################################################################################
# Code
############################################################################################################################
def plugin():

    data = {}
    data["api"] = TruckSimAPI.run()
    data["frame"] = ScreenCapture.run(imgtype="cropped")

    global enabled
    global indicator_last_left
    global indicator_last_right
    global indicator_left_wait_for_response
    global indicator_right_wait_for_response
    global indicator_left_response_timer
    global indicator_right_response_timer

    current_time = time.time()

    if UseAI == False or TorchAvailable == False:
        global map_topleft
        global map_bottomright
        global arrow_topleft
        global arrow_bottomright

        global arrow_percentage

        global navigationsymbol_x
        global navigationsymbol_y

        global offset
        global lefthand_traffic

        global fuel_update_timer
        global fuel_total
        global fuel_current
        global fuel_percentage

        global check_map_timer
        global do_zoom
        global do_blocked
        global mod_enabled
        global allow_playsound
        global allow_playsound_timer

        global controls_last_left
        global controls_last_right

        global left_x_lane
        global right_x_lane
        global left_x_turn
        global right_x_turn
        global left_x_turndrive
        global right_x_turndrive
        global approve_upper_y_left
        global approve_lower_y_left
        global approve_upper_y_right
        global approve_lower_y_right
        
        global detection_offset_lane_y

        global turnincoming_detected
        global turnincoming_direction
        global turnincoming_last_detected

        global indicator_enable_left
        global indicator_enable_right
        global indicator_changed_by_code

        global lanechanging_do_lane_changing
        global lanechanging_speed
        global lanechanging_width
        global lanechanging_current_lane
        global lanechanging_final_offset

        try:
            frame = data["frame"]
            width = frame.shape[1]
            height = frame.shape[0]
        except:
            return

        if frame is None: return
        if width <= 0 or width == None: return
        if height <= 0 or height == None: return
        
        if isinstance(frame, np.ndarray) and frame.ndim == 3 and frame.size > 0:
            valid_frame = True
        else:
            valid_frame = False
            return
        
        if map_topleft != None and map_bottomright != None and arrow_topleft != None and arrow_bottomright != None:
            if (0 <= map_topleft[0] < arrow_topleft[0] < arrow_bottomright[0] < map_bottomright[0] < screen_width) and (0 <= map_topleft[1] < arrow_topleft[1] < arrow_bottomright[1] < map_bottomright[1] < screen_height):
                valid_setup = True
            else:
                valid_setup = False
        else:
            valid_setup = False
        
        if valid_setup == False:
            print("NavigationDetection: Invalid frame or setup.")
            console.RestoreConsole()

        try:
            gamepaused = data["api"]["pause"]
            if gamepaused == True:
                speed = 0
            else:
                speed = round(data["api"]["truckFloat"]["speed"]*3.6, 2)
        except:
            gamepaused = False
            speed = 0

        if current_time > fuel_update_timer + 5:
            fuel_update_timer = current_time
            try:
                fuel_total = data["api"]["configFloat"]["fuelCapacity"]
                fuel_current = data["api"]["truckFloat"]["fuel"]
                if fuel_total != 0:
                    fuel_percentage = (fuel_current/fuel_total)*100
                else:
                    fuel_percentage = 100
            except:
                fuel_total = 0
                fuel_current = 0
                fuel_percentage = 100

        try:
            indicator_left = data["api"]["truckBool"]["blinkerLeftActive"]
            indicator_right = data["api"]["truckBool"]["blinkerRightActive"]
        except:
            indicator_left = False
            indicator_right = False

        intended_left_indicator_state = False
        intended_right_indicator_state = False

        f5_key_state = ctypes.windll.user32.GetAsyncKeyState(0x74)
        f5_pressed = f5_key_state & 0x8000 != 0

        if f5_pressed == True or do_blocked == True or do_zoom == True:
            check_map_timer = current_time
        
        if current_time - 1 < check_map_timer or check_map_timer == 0:
            check_map = True
        else:
            check_map = False

        if check_map == True:
            if map_topleft != None and map_bottomright != None and arrow_topleft != None and arrow_bottomright != None and map_topleft[0] < map_bottomright[0] and map_topleft[1] < map_bottomright[1] and arrow_topleft[0] < arrow_bottomright[0] and arrow_topleft[1] < arrow_bottomright[1]:
                lower_blue = np.array([0, 65, 120])
                upper_blue = np.array([110, 200, 255])
                mask_blue = cv2.inRange(frame[arrow_topleft[1] - map_topleft[1]:arrow_bottomright[1] - map_bottomright[1], arrow_topleft[0] - map_topleft[0]:arrow_bottomright[0] - map_bottomright[0]], lower_blue, upper_blue)
                arrow_height, arrow_width = mask_blue.shape[:2]
                pixel_ratio = round(cv2.countNonZero(mask_blue) / (arrow_width * arrow_height), 3)
            else:
                pixel_ratio = 0

            if arrow_percentage != None:
                if pixel_ratio > arrow_percentage * 0.85 and pixel_ratio < arrow_percentage * 1.15:
                    do_zoom = False
                else:
                    do_zoom = True
                if pixel_ratio < 0.01:
                    do_blocked = True
                else:
                    do_blocked = False
            else:
                do_zoom = False
                do_blocked = False
            if check_map_timer == 0:
                check_map_timer = current_time
            
            lower_green = np.array([0, 200, 0])
            upper_green = np.array([150, 255, 230])
            mask_green = cv2.inRange(frame, lower_green, upper_green)
            if cv2.countNonZero(mask_green) > 0:
                mod_enabled = False
            else:
                mod_enabled = True

        if mod_enabled == False:
            lower_red = np.array([160, 0, 0])
            upper_red = np.array([255, 110, 110])
            lower_green = np.array([0, 200, 0])
            upper_green = np.array([150, 255, 230])
            white_limit = 1

            mask_red = cv2.inRange(frame, lower_red, upper_red)
            mask_green = cv2.inRange(frame, lower_green, upper_green)

            frame_with_mask = cv2.bitwise_or(cv2.bitwise_and(frame, frame, mask=mask_red), cv2.bitwise_and(frame, frame, mask=mask_green))
        else:
            lower_red = np.array([160, 0, 0])
            upper_red = np.array([255, 110, 110])
            white_limit = 1

            mask_red = cv2.inRange(frame, lower_red, upper_red)

            frame_with_mask = cv2.bitwise_and(frame, frame, mask=mask_red)

        cv2.rectangle(frame_with_mask, (0,0), (round(width/6),round(height/3)),(0,0,0),-1)
        cv2.rectangle(frame_with_mask, (width,0), (round(width-width/6),round(height/3)),(0,0,0),-1)

        frame_gray = cv2.cvtColor(frame_with_mask, cv2.COLOR_BGR2GRAY)
        frame_gray_unblurred = frame_gray.copy()

        frame_gray = cv2.GaussianBlur(frame_gray,(3,3),0)

        frame = cv2.cvtColor(frame_gray_unblurred, cv2.COLOR_BGR2RGB)
        
        y_coordinate_of_lane = round(navigationsymbol_y / 1.3)
        y_coordinate_of_turn = round(navigationsymbol_y / 4) 
        automatic_x_offset = round(width/2-navigationsymbol_y)

        def GetArrayOfLaneEdges(y_coordinate_of_detection, tilt, x_offset, y_offset):
            detectingLane = False
            laneEdges = []

            for x in range(0, int(width)):
                
                y = round(y_coordinate_of_detection + y_offset + (navigationsymbol_x - x + x_offset) * tilt)
                if y < 0:
                    y = 0
                if y > height - 1:
                    y = height - 1

                pixel = frame_gray[y, x]
                if (white_limit <= pixel):
                    
                    if not detectingLane:
                        detectingLane = True
                        laneEdges.append(x - x_offset)
                else:
                    if detectingLane:
                        detectingLane = False
                        laneEdges.append(x - x_offset)

            if len(laneEdges) < 2:
                laneEdges.append(width)

            return laneEdges
        
        
        if turnincoming_direction != None:
            if turnincoming_direction == "Left":
                tilt = 0.25
            else:
                tilt = -0.25
        else:
            tilt = 0
        x_offset = lanechanging_final_offset - offset
        y_offset = detection_offset_lane_y
        lanes = GetArrayOfLaneEdges(y_coordinate_of_lane, tilt, x_offset, y_offset)
        try:
            closest_x_pair = min([(left_x, right_x) for left_x, right_x in zip(lanes[::2], lanes[1::2])], key=lambda pair: abs((pair[0] + pair[1]) / 2 - navigationsymbol_x))
            left_x_lane, right_x_lane = closest_x_pair
        except:
            if lefthand_traffic == False:
                left_x_lane = lanes[len(lanes)-2]
                right_x_lane = lanes[len(lanes)-1]
            else:
                try:
                    left_x_lane = lanes[len(lanes)-4]
                    right_x_lane = lanes[len(lanes)-3]
                except:
                    left_x_lane = lanes[len(lanes)-2]
                    right_x_lane = lanes[len(lanes)-1]
        
        left_y_lane = round(y_coordinate_of_lane + detection_offset_lane_y + (navigationsymbol_x - left_x_lane - x_offset) * tilt)
        right_y_lane = round(y_coordinate_of_lane + detection_offset_lane_y + (navigationsymbol_x - right_x_lane - x_offset) * tilt)

        tilt = 0
        x_offset = lanechanging_final_offset - offset
        y_offset = 0
        lanes = GetArrayOfLaneEdges(y_coordinate_of_turn, tilt, x_offset, y_offset)
        try:
            closest_x_pair = min([(left_x, right_x) for left_x, right_x in zip(lanes[::2], lanes[1::2])], key=lambda pair: abs((pair[0] + pair[1]) / 2 - navigationsymbol_x))
            left_x_turn, right_x_turn = closest_x_pair
        except:
            if lefthand_traffic == False:
                left_x_turn = lanes[len(lanes)-2]
                right_x_turn = lanes[len(lanes)-1]
            else:
                try:
                    left_x_turn = lanes[len(lanes)-4]
                    right_x_turn = lanes[len(lanes)-3]
                except:
                    left_x_turn = lanes[len(lanes)-2]
                    right_x_turn = lanes[len(lanes)-1]

        if left_x_lane + lanechanging_final_offset == width:
            left_x_lane = 0
            left_y_lane = 0
            right_x_lane = 0
            right_y_lane = 0
        if left_x_turn + lanechanging_final_offset == width:
            left_x_turn = 0
            right_x_turn = 0

        width_lane = right_x_lane - left_x_lane
        width_turn = right_x_turn - left_x_turn

        center_x_lane = (left_x_lane + right_x_lane) / 2
        center_x_turn = (left_x_turn + right_x_turn) / 2

        approve_x_left = round(navigationsymbol_x - width/4)
        if approve_x_left >= width:
            approve_x_left = width - 1
        if approve_x_left < 0:
            approve_x_left = 0
        approve_upper_y_left = 0
        approve_lower_y_left = 0
        for y in range(height-1, -1, -1):
            pixel = frame_gray[y, approve_x_left]
            if (white_limit <= pixel):
                if approve_upper_y_left == 0:
                    approve_upper_y_left = y
                    approve_lower_y_left = y
                else:
                    approve_lower_y_left = y
            else:
                if approve_upper_y_left != 0:
                    break

        approve_x_right = round(navigationsymbol_x + width/4)
        if approve_x_right >= width:
            approve_x_right = width - 1
        if approve_x_right < 0:
            approve_x_right = 0
        approve_upper_y_right = 0
        approve_lower_y_right = 0
        for y in range(height-1, -1, -1):
            pixel = frame_gray[y, approve_x_right]
            if (white_limit <= pixel):
                if approve_upper_y_right == 0:
                    approve_upper_y_right = y
                    approve_lower_y_right = y
                else:
                    approve_lower_y_right = y
            else:
                if approve_upper_y_right != 0:
                    break
        
        if approve_lower_y_left != 0 and approve_lower_y_right != 0:
            current_color = (255, 0, 0)
        else:
            current_color = (0, 255, 0)
        if approve_lower_y_left != 0:
            cv2.line(frame, (approve_x_left, approve_upper_y_left), (approve_x_left, approve_lower_y_left), current_color, 2)
        if approve_lower_y_right != 0:
            cv2.line(frame, (approve_x_right, approve_upper_y_right), (approve_x_right, approve_lower_y_right), current_color, 2)

        if approve_upper_y_left != 0 and approve_upper_y_right != 0:
            if approve_lower_y_left + round((approve_lower_y_left - approve_upper_y_left) / 2) <= y_coordinate_of_lane <= approve_upper_y_left - round((approve_lower_y_left - approve_upper_y_left) / 2) or approve_lower_y_right + round((approve_lower_y_right - approve_upper_y_right) / 2) <= y_coordinate_of_lane <= approve_upper_y_right - round((approve_lower_y_right - approve_upper_y_right) / 2):
                if approve_lower_y_left < approve_lower_y_right:
                    distance = round((approve_lower_y_left + approve_lower_y_right) / 2 + (approve_lower_y_left - approve_upper_y_left) / 2) - y_coordinate_of_lane
                else:
                    distance = round((approve_lower_y_left + approve_lower_y_right) / 2 + (approve_lower_y_right - approve_upper_y_right) / 2) - y_coordinate_of_lane
                if distance < 0:
                    detection_offset_lane_y = distance
                else:
                    detection_offset_lane_y = 0
            else:
                detection_offset_lane_y = 0
        else:
            detection_offset_lane_y = 0

        if width_turn == 0:
            if approve_upper_y_left != 0:
                turnincoming_detected = True
                turnincoming_direction = "Left"
            if approve_upper_y_right != 0:
                turnincoming_detected = True
                turnincoming_direction = "Right"
        else:
            turnincoming_detected = False
            turnincoming_direction = None

        if approve_upper_y_left != 0 and approve_upper_y_right != 0:
            turnincoming_detected = False
            turnincoming_direction = None

        if approve_upper_y_left == 0 and approve_upper_y_right == 0:
            turnincoming_detected = False
            turnincoming_direction = None

        if turnincoming_detected == True:
            turnincoming_last_detected = current_time
            lanechanging_current_lane = 0

        try:
            data["sdk"]
        except:
            data["sdk"] = {}
        indicator_changed_by_code = False
        if indicator_left != indicator_last_left:
            indicator_left_wait_for_response = False
        if indicator_right != indicator_last_right:
            indicator_right_wait_for_response = False
        if current_time - 1 > indicator_left_response_timer:
            indicator_left_wait_for_response = False
        if current_time - 1 > indicator_right_response_timer:
            indicator_right_wait_for_response = False
        if turnincoming_direction == "Left" and indicator_left == False and indicator_left_wait_for_response == False and enabled == True:
            intended_left_indicator_state = True
            indicator_left_wait_for_response = True
            indicator_left_response_timer = current_time
        if turnincoming_direction == "Right" and indicator_right == False and indicator_right_wait_for_response == False and enabled == True:
            intended_right_indicator_state = True
            indicator_right_wait_for_response = True
            indicator_right_response_timer = current_time
        if turnincoming_direction == None and indicator_left == True and indicator_left_wait_for_response == False and current_time - 2 > turnincoming_last_detected and indicator_changed_by_code == True and enabled == True:
            intended_left_indicator_state = True
            indicator_left_wait_for_response = True
            indicator_left_response_timer = current_time
        if turnincoming_direction == None and indicator_right == True and indicator_right_wait_for_response == False and current_time - 2 > turnincoming_last_detected and indicator_changed_by_code == True and enabled == True:
            intended_right_indicator_state = True
            indicator_right_wait_for_response = True
            indicator_right_response_timer = current_time
        if turnincoming_detected == True:
            indicator_changed_by_code = True
        else:
            indicator_changed_by_code = False
        
        try:
            if controls.GetKeybindFromName("Lane change to the left")['buttonIndex'] != -1:
                controls_left_set = True
                controls_left = controls.GetKeybindValue("Lane change to the left")
            else:
                controls_left_set = False
                controls_left = False
        except:
            controls_left_set = False
            controls_left = False
        try:
            if controls.GetKeybindFromName("Lane change to the right")['buttonIndex'] != -1:
                controls_right_set = True
                controls_right = controls.GetKeybindValue("Lane change to the right")
            else:
                controls_right_set = False
                controls_right = False
        except:
            controls_right_set = False
            controls_right = False

        if enabled == True:
            if controls_left_set == False:
                if indicator_left != indicator_last_left and indicator_left == True and indicator_changed_by_code == False and lanechanging_do_lane_changing == True and current_time - 1 > turnincoming_last_detected:
                    lanechanging_current_lane += 1
            else:
                if controls_left == True and controls_last_left == False and indicator_changed_by_code == False and lanechanging_do_lane_changing == True and current_time - 1 > turnincoming_last_detected:
                    if indicator_left == True:
                        lanechanging_current_lane += 1
                    elif indicator_left == False and indicator_right_wait_for_response == False:
                        lanechanging_current_lane += 1
                        indicator_enable_left = True
            if controls_right_set == False:
                if indicator_right != indicator_last_right and indicator_right == True and indicator_changed_by_code == False and lanechanging_do_lane_changing == True and current_time - 1 > turnincoming_last_detected:
                    lanechanging_current_lane -= 1
            else:
                if controls_right == True and controls_last_right == False and indicator_changed_by_code == False and lanechanging_do_lane_changing == True and current_time - 1 > turnincoming_last_detected:
                    if indicator_right == True:
                        lanechanging_current_lane -= 1
                    elif indicator_right == False and indicator_left_wait_for_response == False:
                        lanechanging_current_lane -= 1
                        indicator_enable_right = True

        if indicator_enable_left == True and indicator_left == False and indicator_left_wait_for_response == False and enabled == True:
            intended_left_indicator_state = True
            indicator_changed_by_code = True
            indicator_left_wait_for_response = True
            indicator_left_response_timer = current_time
        elif indicator_left == True and indicator_left_wait_for_response == False:
            indicator_enable_left = False
        if indicator_enable_right == True and indicator_right == False and indicator_right_wait_for_response == False and enabled == True:
            intended_right_indicator_state = True
            indicator_changed_by_code = True
            indicator_right_wait_for_response = True
            indicator_right_response_timer = current_time
        elif indicator_right == True and indicator_right_wait_for_response == False:
            indicator_enable_right = False

        lanechanging_target_offset = lanechanging_width * lanechanging_current_lane
        lanechanging_current_correction = lanechanging_target_offset - lanechanging_final_offset
        if abs(lanechanging_current_correction) > lanechanging_speed/10:
            if lanechanging_current_correction > 0:
                lanechanging_current_correction = lanechanging_speed/10
            else:
                lanechanging_current_correction = -lanechanging_speed/10
        lanechanging_final_offset += lanechanging_current_correction
        lanechanging_progress = lanechanging_final_offset/lanechanging_width
        
        if lanechanging_progress == lanechanging_current_lane and indicator_left == True and indicator_left_wait_for_response == False and indicator_changed_by_code == False and lanechanging_do_lane_changing == True and enabled == True and controls_left_set == False:
            intended_left_indicator_state = True
            indicator_left_wait_for_response = True
            indicator_left_response_timer = current_time
        elif lanechanging_progress == lanechanging_current_lane and indicator_left == True and indicator_left_wait_for_response == False and indicator_changed_by_code == False and lanechanging_do_lane_changing == True and enabled == True and controls_left_set == True:
            intended_left_indicator_state = True
            indicator_left_wait_for_response = True
            indicator_left_response_timer = current_time

        if lanechanging_progress == lanechanging_current_lane and indicator_right == True and indicator_right_wait_for_response == False and indicator_changed_by_code == False and lanechanging_do_lane_changing == True and enabled == True and controls_right_set == False:
            intended_right_indicator_state = True
            indicator_right_wait_for_response = True
            indicator_right_response_timer = current_time
        elif lanechanging_progress == lanechanging_current_lane and indicator_right == True and indicator_right_wait_for_response == False and indicator_changed_by_code == False and lanechanging_do_lane_changing == True and enabled == True and controls_right_set == True:
            intended_right_indicator_state = True
            indicator_right_wait_for_response = True
            indicator_right_response_timer = current_time

        if width_lane != 0:
            if turnincoming_detected == False:
                correction = navigationsymbol_x - center_x_lane
            else:
                if turnincoming_direction == "Left":
                    correction = navigationsymbol_x - center_x_lane - width_lane/40
                else:
                    correction = navigationsymbol_x - center_x_lane + width_lane/40
        else:
            correction = 0
            if turnincoming_direction == "Left" and enabled == True:
                intended_left_indicator_state = False
            if turnincoming_direction == "Right" and enabled == True:
                intended_right_indicator_state = False
            turnincoming_detected = False
            turnincoming_direction = None

        map_detected = True

        if valid_setup == False:
            if allow_playsound == True:
                sounds.Play("info")
                allow_playsound = False
                allow_playsound_timer = current_time
            frame = cv2.GaussianBlur(frame, (9, 9), 0)
            frame = cv2.addWeighted(frame, 0.5, frame, 0, 0)

            cv2.circle(frame, (width//2, int(height/3.5)), height//4, (255, 128, 0), height//50, cv2.LINE_AA)
            cv2.line(frame, (width//2, int(height/3.5)), (width//2, int(height//3.5 + height/8)), (255, 128, 0), height//35, cv2.LINE_AA)
            cv2.circle(frame, (width//2, int(height/3.5 - height/8)), height//50, (255, 128, 0), -1, cv2.LINE_AA)

            text, fontscale, thickness, text_width, text_height = get_text_size(text="Do the Setup", text_width=width/1.1, max_text_height=height/10)
            cv2.putText(frame, text, (int(width/2-text_width/2), int(height/1.45+text_height/2)), cv2.FONT_HERSHEY_SIMPLEX, fontscale, (255, 128, 0), thickness, cv2.LINE_AA)

            correction = 0
            map_detected = False

        elif do_blocked == True:
            if allow_playsound == True:
                sounds.Play("info")
                allow_playsound = False
                allow_playsound_timer = current_time
            frame = cv2.GaussianBlur(frame, (9, 9), 0)
            frame = cv2.addWeighted(frame, 0.5, frame, 0, 0)

            cv2.circle(frame, (width//2, int(height/3.5)), height//4, (255, 128, 0), height//50, cv2.LINE_AA)
            cv2.line(frame, (width//2, int(height/3.5)), (width//2, int(height//3.5 + height/8)), (255, 128, 0), height//35, cv2.LINE_AA)
            cv2.circle(frame, (width//2, int(height/3.5 - height/8)), height//50, (255, 128, 0), -1, cv2.LINE_AA)

            text, fontscale, thickness, text_width, text_height = get_text_size(text="Minimap covered", text_width=width/1.1, max_text_height=height/10)
            cv2.putText(frame, text, (int(width/2-text_width/2), int(height/1.45+text_height/2)), cv2.FONT_HERSHEY_SIMPLEX, fontscale, (255, 128, 0), thickness, cv2.LINE_AA)

            correction = 0
            map_detected = False

        elif do_zoom == True:
            if allow_playsound == True:
                sounds.Play("info")
                allow_playsound = False
                allow_playsound_timer = current_time
            frame = cv2.GaussianBlur(frame, (9, 9), 0)
            frame = cv2.addWeighted(frame, 0.5, frame, 0, 0)

            cv2.circle(frame, (width//2, int(height/3.5)), height//4, (255, 128, 0), height//50, cv2.LINE_AA)
            cv2.line(frame, (width//2, int(height/3.5)), (width//2, int(height//3.5 + height/8)), (255, 128, 0), height//35, cv2.LINE_AA)
            cv2.circle(frame, (width//2, int(height/3.5 - height/8)), height//50, (255, 128, 0), -1, cv2.LINE_AA)

            text, fontscale, thickness, text_width, text_height = get_text_size(text="Zoom Minimap in", text_width=width/1.1, max_text_height=height/10)
            cv2.putText(frame, text, (int(width/2-text_width/2), int(height/1.45+text_height/2)), cv2.FONT_HERSHEY_SIMPLEX, fontscale, (255, 128, 0), thickness, cv2.LINE_AA)

            correction = 0
            map_detected = False

        elif width_lane == 0:
            if allow_playsound == True:
                sounds.Play("info")
                allow_playsound = False
                allow_playsound_timer = current_time
            frame = cv2.GaussianBlur(frame, (9, 9), 0)
            frame = cv2.addWeighted(frame, 0.5, frame, 0, 0)

            cv2.circle(frame, (width//2, int(height/3.5)), height//4, (255, 128, 0), height//50, cv2.LINE_AA)
            cv2.line(frame, (width//2, int(height/3.5)), (width//2, int(height//3.5 + height/8)), (255, 128, 0), height//35, cv2.LINE_AA)
            cv2.circle(frame, (width//2, int(height/3.5 - height/8)), height//50, (255, 128, 0), -1, cv2.LINE_AA)

            text, fontscale, thickness, text_width, text_height = get_text_size(text="No Lane Detected", text_width=width/1.1, max_text_height=height/10)
            cv2.putText(frame, text, (int(width/2-text_width/2), int(height/1.45+text_height/2)), cv2.FONT_HERSHEY_SIMPLEX, fontscale, (255, 128, 0), thickness, cv2.LINE_AA)

            correction = 0
            map_detected = False

        else:

            if current_time - 1 > allow_playsound_timer:
                allow_playsound = True

            if width_lane != 0:
                cv2.line(frame, (round(left_x_lane + lanechanging_final_offset - offset), left_y_lane), (round(right_x_lane + lanechanging_final_offset - offset), right_y_lane),  (255, 255, 255), 2)
            if width_turn != 0:
                cv2.line(frame, (round(left_x_turn + lanechanging_final_offset - offset), y_coordinate_of_turn), (round(right_x_turn + lanechanging_final_offset - offset), y_coordinate_of_turn), (255, 255, 255), 2)

        text, fontscale, thickness, text_width_enabled, text_height_enabled = get_text_size(text="Enabled" if enabled else "Disabled", text_width=width/1.1, max_text_height=height/11)
        cv2.putText(frame, text, (5, 5 + text_height_enabled), cv2.FONT_HERSHEY_SIMPLEX, fontscale, (0, 255, 0) if enabled else (255, 0, 0), thickness, cv2.LINE_AA)

        if lanechanging_do_lane_changing == True:
            text, fontscale, thickness, text_width_lane, text_height_lane = get_text_size(text=f"Lane: {lanechanging_current_lane}", text_width=text_width_enabled, max_text_height=height)
            cv2.putText(frame, text, (5, 15 + text_height_enabled + text_height_lane), cv2.FONT_HERSHEY_SIMPLEX, fontscale, (150, 150, 150) if turnincoming_detected else (200, 200, 200), thickness, cv2.LINE_AA)

        if fuel_percentage < 15:
            text, fontscale, thickness, text_width_refuel, text_height_refuel = get_text_size(text="Refuel!", text_width=text_width_enabled, max_text_height=height)
            cv2.putText(frame, text, (5, (25 if lanechanging_do_lane_changing == True else 15) + text_height_enabled + text_height_refuel + (text_height_lane if lanechanging_do_lane_changing == True else 0)), cv2.FONT_HERSHEY_SIMPLEX, fontscale, (255, 0, 0), thickness, cv2.LINE_AA)

        indicator_last_left = indicator_left
        indicator_last_right = indicator_right
        controls_last_left = controls_left
        controls_last_right = controls_right

        correction /= -30

        if speed > 63:
            correction *= 63/speed
        elif speed < -0.25:
            correction *= -1

        if turnincoming_detected == False and width_turn != 0 and width_turn < width_lane:
            curve = (center_x_lane - center_x_turn)/30
        else:
            curve = correction/10
        if gamepaused == True:
            curve = 0

        if width_lane == 0:
            lane_detected = False
            check_map_timer = current_time
        else:
            lane_detected = True

        data["NavigationDetection"] = {}
        data["NavigationDetection"]["lanedetected"] = lane_detected
        data["NavigationDetection"]["mapdetected"] = map_detected
        data["NavigationDetection"]["turnincoming"] = turnincoming_detected
        data["NavigationDetection"]["curve"] = curve
        data["NavigationDetection"]["lane"] = lanechanging_current_lane
        data["NavigationDetection"]["laneoffsetpercent"] = lanechanging_progress

        Steering.run(value=correction, sendToGame=enabled)
        ShowImage.run(frame)
        SDKController.lblinker = bool(intended_left_indicator_state)
        SDKController.rblinker = bool(intended_right_indicator_state)

        return data["NavigationDetection"]

    else:

        try:
            global IMG_WIDTH
            global IMG_HEIGHT

            try:
                while AIModelUpdateThread.is_alive(): return
                while AIModelLoadThread.is_alive(): return
            except:
                return

            try:
                frame = data["frame"]
                width = frame.shape[1]
                height = frame.shape[0]
            except:
                return

            if frame is None: return
            if width == 0 or width == None: return
            if height == 0 or height == None: return

            if isinstance(frame, np.ndarray) and frame.ndim == 3 and frame.size > 0:
                valid_frame = True
            else:
                valid_frame = False
                return

            try:
                gamepaused = data["api"]["pause"]
            except:
                gamepaused = False

            cv2.rectangle(frame, (0, 0), (round(frame.shape[1]/6), round(frame.shape[0]/3)), (0, 0, 0), -1)
            cv2.rectangle(frame, (frame.shape[1] ,0), (round(frame.shape[1]-frame.shape[1]/6), round(frame.shape[0]/3)), (0, 0, 0), -1)
            lower_red = np.array([160, 0, 0])
            upper_red = np.array([255, 110, 110])
            mask = cv2.inRange(frame, lower_red, upper_red)
            frame_with_mask = cv2.bitwise_and(frame, frame, mask=mask)
            frame = cv2.cvtColor(frame_with_mask, cv2.COLOR_BGR2GRAY)

            if cv2.countNonZero(frame) / (frame.shape[0] * frame.shape[1]) > 0.03:
                lane_detected = True
            else:
                lane_detected = False

            try:
                AIFrame = preprocess_image(mask)
            except:
                IMG_WIDTH = GetAIModelProperties()[2]
                IMG_HEIGHT = GetAIModelProperties()[3]
                if IMG_WIDTH == "UNKNOWN" or IMG_HEIGHT == "UNKNOWN":
                    print(f"NavigationDetection - Unable to read the AI model image size. Make sure you didn't change the model file name. The code wont run the NavigationDetectionAI.")
                    console.RestoreConsole()
                    return
                AIFrame = preprocess_image(mask)

            output = [[0, 0, 0, 0, 0, 0, 0, 0]]

            if enabled == True and gamepaused == False:
                if AIModelLoaded == True:
                    with torch.no_grad():
                        output = AIModel(AIFrame)
                        output = output.tolist()

            steering = float(output[0][0]) / -30
            left_indicator = bool(float(output[0][1]) > 0.15)
            right_indicator = bool(float(output[0][2]) > 0.15)

            if lane_detected == False:
                steering = 0
                left_indicator = False
                right_indicator = False

            try:
                indicator_left = data["api"]["truckBool"]["blinkerLeftActive"]
                indicator_right = data["api"]["truckBool"]["blinkerRightActive"]
            except:
                indicator_left = False
                indicator_right = False

            try:
                data["sdk"]
            except:
                data["sdk"] = {}

            if enabled == True and gamepaused == False:
                if left_indicator != indicator_left:
                    intended_left_indicator_state = True
                    indicator_left_wait_for_response = True
                    indicator_left_response_timer = current_time
                if right_indicator != indicator_right:
                    intended_right_indicator_state = True
                    indicator_right_wait_for_response = True
                    indicator_right_response_timer = current_time

                if indicator_left != indicator_last_left:
                    indicator_left_wait_for_response = False
                if indicator_right != indicator_last_right:
                    indicator_right_wait_for_response = False
                if current_time - 1 > indicator_left_response_timer:
                    indicator_left_wait_for_response = False
                if current_time - 1 > indicator_right_response_timer:
                    indicator_right_wait_for_response = False
            indicator_last_left = left_indicator
            indicator_last_right = right_indicator

            data["NavigationDetection"] = {}
            if left_indicator == True or right_indicator == True:
                data["NavigationDetection"]["turnincoming"] = True
            else:
                data["NavigationDetection"]["turnincoming"] = False

            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

            text, fontscale, thickness, text_width_enabled, text_height_enabled = get_text_size(text="Enabled" if enabled else "Disabled", text_width=width/1.1, max_text_height=height/11)
            cv2.putText(frame, text, (5, 5 + text_height_enabled), cv2.FONT_HERSHEY_SIMPLEX, fontscale, (0, 255, 0) if enabled else (255, 0, 0), thickness, cv2.LINE_AA)

            Steering.run(value=steering, sendToGame=enabled)
            ShowImage.run(frame)
            SDKController.lblinker = bool(indicator_last_left)
            SDKController.rblinker = bool(indicator_last_right)

        except Exception as e:
            exc = traceback.format_exc()
            SendCrashReport("NavigationDetection - Running AI Error.", str(exc))
            console.RestoreConsole()
            print("\033[91m" + f"NavigationDetection - Running AI Error: " + "\033[0m" + str(e))