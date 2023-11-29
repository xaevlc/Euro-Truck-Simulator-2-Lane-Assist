from src.logger import print

'''
This file contains the main UI for the program. It is responsible for creating the window and setting up the main UI elements.
'''

import time
import tkinter as tk
from tkinter import ttk, messagebox
import src.helpers as helpers
from tkinter import font
import src.variables as variables
from src.loading import LoadingWindow
from src.logger import print
import src.settings as settings
from src.translator import Translate
import plugins.ThemeSelector.main as themeSelector

def CropWallpaper(image, x, y, w, h):
    from PIL import Image
    image = Image.open("assets/images/wallpaper.png")
    image = image.resize((width, height), Image.Resampling.BILINEAR)
    image = image.crop((x, y, x+w, y+h))
    return image

def DeleteRoot():
    global root
    
    # Save the current position
    x = root.winfo_x()
    y = root.winfo_y()
    settings.CreateSettings("User Interface", "Position", [x, y])
    
    try:
        root.destroy()
        del root
    except:
        pass

lastClosedTabName = "About"
def closeTab(event):
    global lastClosedTabName
    try:
        index = pluginNotebook.tk.call(pluginNotebook._w, "identify", "tab", event.x, event.y)
        # Get plugin name from the pluginNotebook
        pluginName = pluginNotebook.tab(index, "text")
        pluginNotebook.forget(index)
        pluginFrames.pop(index)
        UIs.pop(index)
        lastClosedTabName = pluginName
        settings.RemoveFromList("User Interface", "OpenTabs", pluginName)
        
    except:
        pass

def selectedOtherTab():
    currentFrame = pluginFrames[pluginNotebook.index(pluginNotebook.select())]
    currentUI = UIs[pluginNotebook.index(pluginNotebook.select())]
    # Run the UI tab focus function
    if currentUI != None:
        try:
            currentUI.tabFocused()
        except:
            resizeWindow(width, height)
    else:
        resizeWindow(width, height)

def switchSelectedPlugin(pluginName):
    global plugin
    global pluginFrame
    global pluginFrames
    global ui
    global root

    # Check if the plugin is already loaded
    notebookNames = []
    for tab in pluginNotebook.tabs():
        notebookNames.append(pluginNotebook.tab(tab, "text"))
    
    if pluginName.replace("plugins.", "").replace(".main", "") in notebookNames:
        pluginNotebook.select(notebookNames.index(pluginName.replace("plugins.", "").replace(".main", "")))
        ui = UIs[pluginNotebook.index(pluginNotebook.select())]
        return
    
    plugin = __import__(pluginName, fromlist=["UI", "PluginInfo"])
    
    if plugin.PluginInfo.disablePlugins == True and settings.GetSettings("Plugins", "Enabled") != []:
        if messagebox.askokcancel("Plugins", Translate("The panel has asked to disable all plugins. Do you want to continue?")):
            settings.CreateSettings("Plugins", "Enabled", [])
            variables.UpdatePlugins()
            
        else: return
        
    if plugin.PluginInfo.disableLoop == True and variables.ENABLELOOP == True:
        if messagebox.askokcancel("Plugins", Translate("The panel has asked to disable the mainloop. Do you want to continue?")):
            variables.ToggleEnable()
            enableButton.config(text=(Translate("Disable") if variables.ENABLELOOP else Translate("Enable")))
        
        else: return
        
        
        
    # Create a new frame for the plugin in the notebook
    pluginFrame = ttk.Frame(pluginNotebook, width=width, height=height-20)
    pluginFrame.pack_propagate(0)
    pluginFrame.grid_propagate(0)
    
    ui = plugin.UI(pluginFrame)
    UIs.append(ui)
    
    pluginFrames.append(pluginFrame)
    pluginNotebook.add(pluginFrame, text=plugin.PluginInfo.name)
    
    pluginNotebook.select(pluginFrames.index(pluginFrame))
    
    print("Loaded " + pluginName)
    
    settings.AddToList("User Interface", "OpenTabs", plugin.PluginInfo.name, exclusive=True)

def quit():
    global root
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        # Destroy the root window
        root.destroy()
        del root

def drawButtons(refresh=False):
    global enableButton
    global themeButton
    
    if refresh or pluginFrames == []:
        CreateRoot()
    
    try:
        for child in pluginFrames[0].winfo_children():
            child.destroy()
    except:
        pass
        
    for child in buttonFrame.winfo_children():
        child.destroy()
    
    try:
        helpers.MakeButton(pluginFrames[0], "Panel Manager", lambda: switchSelectedPlugin("plugins.PanelManager.main"), 0, 0, width=20)
        helpers.MakeButton(pluginFrames[0], "Plugin Manager", lambda: switchSelectedPlugin("plugins.PluginManager.main"), 1, 0, width=20)
        helpers.MakeButton(pluginFrames[0], "First Time Setup", lambda: switchSelectedPlugin("plugins.FirstTimeSetup.main"), 2, 0, width=20, style="Accent.TButton")
        helpers.MakeButton(pluginFrames[0], "LANGUAGE - 语言设置", lambda: switchSelectedPlugin("plugins.DeepTranslator.main"), 3, 0, width=20, style="Accent.TButton", translate=False)
        helpers.MakeLabel(pluginFrames[0], "You can use F5 to refresh the UI and come back to this page.\n(as long as the app is disabled)", 0, 1)
        helpers.MakeLabel(pluginFrames[0], "The top of the app has all your currently open tabs.              \nThey can be closed with the middle mouse button.", 1, 1)
    except:
        pass
    enableButton = helpers.MakeButton(buttonFrame, "Enable", lambda: (variables.ToggleEnable(), enableButton.config(text=("Disable" if variables.ENABLELOOP else "Enable"))), 0, 0, width=10, padx=9, style="Accent.TButton")
    helpers.MakeButton(buttonFrame, "Panels", lambda: switchSelectedPlugin("plugins.PanelManager.main"), 1, 0, width=10, padx=9)
    helpers.MakeButton(buttonFrame, "Plugins", lambda: switchSelectedPlugin("plugins.PluginManager.main"), 2, 0, width=10, padx=9)
    helpers.MakeButton(buttonFrame, "Performance", lambda: switchSelectedPlugin("plugins.Performance.main"), 3, 0, width=10, padx=9)
    helpers.MakeButton(buttonFrame, "Settings", lambda: switchSelectedPlugin("plugins.Settings.main"), 4, 0, width=10, padx=9)
    helpers.MakeButton(buttonFrame, "Help/About", lambda: switchSelectedPlugin("plugins.About.main"), 5, 0, width=10, padx=9)
    themeButton = helpers.MakeButton(buttonFrame, Translate(settings.GetSettings("User Interface", "Theme")).capitalize() + " Mode", lambda: changeTheme(), 6, 0, width=10, padx=9)
    import webbrowser
    helpers.MakeButton(buttonFrame, "Discord", lambda: webbrowser.open("https://discord.gg/DpJpkNpqwD"), 7, 0, width=10, padx=9, style="Accent.TButton", translate=False)

prevFrame = 100
def update(data):
    global fps
    global prevFrame
    
    # Calculate the UI caused overhead
    frame = time.time()
    try:
        fps.set(f"UI FPS: {round((frame-prevFrame)*1000)}ms ({round(1/(frame-prevFrame))}fps)")
    except: pass
    prevFrame = frame
        
    try:
        # Update the selected plugin
        ui = UIs[pluginNotebook.index(pluginNotebook.select())]
        if ui != None:
            ui.update(data)
    except Exception as ex:
        if "'UI' object has no attribute 'update'" in str(ex):
            print("Currently open panel does not have an update method. Please add one.")
        elif "name 'ui' is not defined" not in str(ex):
            print(str(ex))
        pass

    try:
        root.update()
    except:
        raise Exception("The main window has been closed.", "If you closed the app this is normal.")
    
def resizeWindow(newWidth, newHeight):
    global root
    global root
    # Offsets for the new tabs
    newHeight += 20
    newWidth += 40
    
    root.geometry(f"{newWidth}x{newHeight}")
    pluginNotebook.config(width=newWidth, height=newHeight-20)
    buttonFrame.config(height=newHeight-20)
    root.update()
        
def changeTheme():
    print("Changing theme")
    global themeButton
    themeSelector.SwitchThemeType()
    themeButton.config(text=Translate(settings.GetSettings("User Interface", "Theme")).capitalize() + " Mode")
    
# Save the position of the window if it's moved
saveTimer = time.time()
saveEveryXSeconds = 1
def savePosition(event):
    global saveTimer
    if time.time() - saveTimer > saveEveryXSeconds:
        saveTimer = time.time()
        global root
        x = root.winfo_x()
        y = root.winfo_y()
        settings.CreateSettings("User Interface", "Position", [x, y])
        

pluginFrames = []
UIs = []
additionals = []
ui = None
def CreateRoot():
    global root
    global buttonFrame
    global pluginFrames
    global UIs
    global pluginNotebook
    global width
    global height
    global fps
    global fpsLabel
    
    # Stack overflow comes to the rescue once again here
    # https://stackoverflow.com/a/44422362
    import ctypes
    wantedAwareness = settings.GetSettings("User Interface", "DPIAwareness", 0)

    # Query DPI Awareness (Windows 10 and 8)
    awareness = ctypes.c_int()
    errorCode = ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
    print("Original DPI awareness value : " + str(awareness.value))

    # Set DPI Awareness  (Windows 10 and 8)
    try:
        errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(wantedAwareness)
        print("Set DPI awareness value to " + str(wantedAwareness) + " (code " + str(errorCode) + ")")
    except:
        print("Failed to set DPI awareness value")
        #errorCode = ctypes.windll.user32.SetProcessDPIAware()

    # the argument is the awareness level, which can be 0, 1 or 2:
    # for 1-to-1 pixel control I seem to need it to be non-zero (I'm using level 2)
    
    try:
        root.destroy()
    except:
        pass  
    
    width = 800
    height = 600

    root = tk.Tk()
    showCopyrightInTitlebar = settings.GetSettings("User Interface", "TitleCopyright")
    if showCopyrightInTitlebar == None:
        settings.CreateSettings("User Interface", "TitleCopyright", True)
        showCopyrightInTitlebar = True
    
    root.title("Lane Assist - ©Tumppi066 2023" if showCopyrightInTitlebar else "Lane Assist")
    
    # Hack to make windows think we are our own app, and then show our icon
    import ctypes
    myappid = u'mycompany.myproduct.subproduct.version' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    root.iconbitmap(default="assets/favicon.ico")

    root.resizable(False, False)
    # Load the size and position
    position = settings.GetSettings("User Interface", "Position")
    if position == None:
        root.geometry(f"{width}x{height}")
    else:
        root.geometry(f"{width}x{height}+{position[0]}+{position[1]}")
    root.protocol("WM_DELETE_WINDOW", lambda: quit())
    
    theme = settings.GetSettings("User Interface", "ColorTheme")
    if theme == None:
        theme = "Forest"
        settings.CreateSettings("User Interface", "ColorTheme", theme)
    
    themeSelector.ChangeTheme(theme, root)

    # Check if an image exists in assets/images/wallpaper.png
    # If it does then set it as a background image called and then make a canvas
    try:
        from PIL import Image, ImageTk
        image = Image.open("assets/images/wallpaper.png")
        image = image.resize((width, height), Image.Resampling.BILINEAR)
        image = ImageTk.PhotoImage(image)
        imageLabel = tk.Label(root, image=image)
        imageLabel.image = image
        imageLabel.place(x=0, y=0, relwidth=1, relheight=1)
    except:
        pass

    # Bottom text
    showCopyright = settings.GetSettings("User Interface", "ShowCopyright")
    if showCopyright == None:
        settings.CreateSettings("User Interface", "ShowCopyright", False)
        showCopyright = False
    if showCopyright:
        ttk.Label(root, text=f"ETS2 Lane Assist ({variables.VERSION})   ©Tumppi066 - 2023", font=("Roboto", 8)).pack(side="bottom", anchor="s", padx=10, pady=0)
    fps = tk.StringVar()
    
    showFps = settings.GetSettings("User Interface", "ShowFPS")
    if showFps == None:
        settings.CreateSettings("User Interface", "ShowFPS", False)
        showFps = False
    if showFps:
        fpsLabel = ttk.Label(root, textvariable=fps, font=("Roboto", 8)).pack(side="bottom", anchor="s", padx=10, pady=0)

    # Left button bar
    try:
        buttonFrame = tk.Canvas(root, width=width-675, height=height-20, border=0, highlightthickness=0)
        
        # Cut out the image to only where the canvas is 
        x = 10
        y = 10
        w = width-675
        h = height-20
        image = CropWallpaper("assets/images/wallpaper.png", x, y, w, h)
        newImage = ImageTk.PhotoImage(image)
        
        imageLabel = tk.Label(buttonFrame, image=newImage)
        imageLabel.image = newImage
        imageLabel.place(x=0, y=0, relwidth=1, relheight=1)    
    except:
        buttonFrame = ttk.LabelFrame(root, text="Lane Assist", width=width-675, height=height-20)
    
    buttonFrame.pack_propagate(0)
    buttonFrame.grid_propagate(0)
    buttonFrame.pack(side="left", anchor="n", padx=10, pady=10)

    # Create the plugin notebook
    pluginNotebook = ttk.Notebook(root, width=width, height=height-20)
    pluginNotebook.pack_propagate(0)
    pluginNotebook.grid_propagate(0)

    # Create the page for the main menu
    pluginFrame = ttk.Frame(pluginNotebook, width=width, height=height-20)
    pluginFrame.pack_propagate(0)
    pluginFrame.grid_propagate(0)
    pluginFrames = []
    UIs = []
    pluginFrames.append(pluginFrame)
    UIs.append(None)
    pluginNotebook.add(pluginFrame, text="Main Menu")
    
    pluginNotebook.pack(side="left", anchor="n", padx=10, pady=10)
    
    # Make a callback for selecting another tab
    pluginNotebook.bind("<<NotebookTabChanged>>", lambda e: selectedOtherTab())
    
    # Bind middleclick on a tab to close it
    closeMMB = settings.GetSettings("User Interface", "CloseTabMMB")
    if closeMMB == None:
        settings.CreateSettings("User Interface", "CloseTabMMB", True)
        closeMMB = True
    closeRMB = settings.GetSettings("User Interface", "CloseTabRMB")
    if closeRMB == None:
        settings.CreateSettings("User Interface", "CloseTabRMB", False)
        closeRMB = False
        
    if closeMMB:
        pluginNotebook.bind("<Button-2>", lambda e: closeTab(e))
    if closeRMB:
        pluginNotebook.bind("<Button-3>", lambda e: closeTab(e))
    
    # Bind the custom key to close the tab
    try:
        customKey = settings.GetSettings("User Interface", "CustomKey")
        if customKey != None and customKey != "":
            root.bind(f"<{customKey}>", lambda e: closeTab(e))
            print(f"Bound <{customKey}> to close tab")
    except:
        print("Failed to bind custom key to close tab")
    
    # Bind rightclick on a tab to move it to another position
    # TODO: Make this work
    # pluginNotebook.bind("<Button-3>", lambda e: moveTab(e))

    # Bind CTRL Z to undo closing last tab
    root.bind("<Control-z>", lambda e: switchSelectedPlugin(f"plugins.{lastClosedTabName}.main"))

    def Reload():
        variables.RELOAD = True

    # Bind F5 to drawButtons
    root.bind("<F5>", lambda e: Reload())
    print("Initialized UI")
    
    # Bind movement of the window to save the position
    root.bind("<Configure>", lambda e: savePosition(e))

    root.update()
    
    if theme != "SunValley" and theme != "Forest" and theme != "Azure":
        themeSelector.ColorTitleBar(root, override="0x313131")
    else:
        themeSelector.ColorTitleBar(root)
        
    # Open previously open tabs
    ReopenTabs = settings.GetSettings("User Interface", "ReopenTabs")
    if ReopenTabs == None:
        settings.CreateSettings("User Interface", "ReopenTabs", True)
        ReopenTabs = True
        
    if settings.GetSettings("User Interface", "OpenTabs") is not None and ReopenTabs:
        for tab in settings.GetSettings("User Interface", "OpenTabs"):
            print("Loading " + tab)
            try:
                switchSelectedPlugin(f"plugins.{tab}.main")
            except Exception as ex:
                print(ex.args)
                pass

    print("Loaded previously open tabs")
    root.update()


CreateRoot()