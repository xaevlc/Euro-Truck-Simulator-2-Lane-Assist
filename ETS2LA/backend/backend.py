from ETS2LA.Plugin import *
import multiprocessing
import importlib
import threading
import inspect
import time
import os

plugin_path = "plugins"
plugin_target_class = "Plugin"

AVAILABLE_PLUGINS: list[tuple[str, PluginDescription, Author]] = []

class PluginHandler:
    
    plugin_name: str
    plugin_description: PluginDescription
    data = None
    
    return_queue: multiprocessing.JoinableQueue
    
    plugins_queue: multiprocessing.JoinableQueue
    plugins_return_queue: multiprocessing.JoinableQueue
    
    def __init__(self, plugin_name: str, plugin_description: PluginDescription):
        self.plugin_name = plugin_name
        self.plugin_description = plugin_description
        self.return_queue = multiprocessing.JoinableQueue()
        self.plugins_queue = multiprocessing.JoinableQueue()
        self.plugins_return_queue = multiprocessing.JoinableQueue()
        self.process = multiprocessing.Process(target=PluginRunner, args=(self.plugin_name, self.plugin_description, self.return_queue, self.plugins_queue, self.plugins_return_queue), daemon=True)
        self.process.start()
        RUNNING_PLUGINS.append(self)
        threading.Thread(target=self.data_handler, daemon=True).start()
        threading.Thread(target=self.plugins_handler, daemon=True).start()

    def plugins_handler(self):
        while True:
            if not self.plugins_queue.empty():
                plugin_name = self.plugins_queue.get()
                if plugin_name in [plugin.plugin_name for plugin in RUNNING_PLUGINS]:
                    index = [plugin.plugin_name for plugin in RUNNING_PLUGINS].index(plugin_name)
                    self.plugins_return_queue.put(RUNNING_PLUGINS[index].data)
                else:
                    self.plugins_return_queue.put(None)
            else:
                time.sleep(0.01)

    def data_handler(self):
        while True:
            if not self.return_queue.empty():
                data = self.return_queue.get()
                self.data = data
            else:
                time.sleep(0.01) # 100fps

RUNNING_PLUGINS: list[PluginHandler] = []

def get_plugin_class(module_name):
    module = __import__(module_name, fromlist=['*'])
    for name, cls in inspect.getmembers(module):
        if inspect.isclass(cls) and issubclass(cls, ETS2LAPlugin) and cls != ETS2LAPlugin:
            return cls
    return None

def find_plugins() -> list[tuple[str, PluginDescription, Author]]:
    folders = os.listdir(plugin_path)
    plugins = []
    for folder in folders:
        if "main.py" in os.listdir(f"{plugin_path}/{folder}"):
            plugin_class = get_plugin_class(f"{plugin_path}.{folder}.main")
            if plugin_class is not None:
                information = getattr(plugin_class, "description", None)
                author = getattr(plugin_class, "author", None)
                plugins.append((folder, information, author))
            del plugin_class
            
    return plugins

def enable_plugin(plugin_name: str):
    runner = threading.Thread(target=PluginHandler, args=(plugin_name, PluginDescription()), daemon=True)
    runner.start()
    
def get_plugin_data(plugin_name: str):
    for plugin in RUNNING_PLUGINS:
        if plugin.plugin_name == plugin_name:
            return plugin.data
    return None

def run():
    global AVAILABLE_PLUGINS
    AVAILABLE_PLUGINS = find_plugins()
    print(AVAILABLE_PLUGINS)