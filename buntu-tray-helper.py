import os
import threading
import time
import gi
gi.require_version('AppIndicator3', '0.1')
from gi.repository import AppIndicator3, Gtk

import importlib
import pkgutil

from dotenv import load_dotenv

#load environment variables from a .env file
load_dotenv()

script_dir = os.path.dirname(os.path.abspath(__file__))
icon_dir = os.path.join(script_dir, "icon")

def quit_app(_):
    Gtk.main_quit()

registered_plugins = []
def load_plugins():
    global script_dir
    plugins = []

    for finder, name, ispkg in pkgutil.iter_modules([os.path.join(script_dir, "plugins")]):
        print(f"Found plugin: {name}")
        module = importlib.import_module(os.path.join("plugins", name).replace(os.sep, "."))
        if hasattr(module, "register"):
            try:
                module.register(menu, indicator)  # call convention
                plugins.append(module)
            except Exception as e:
                print(f"Error registering plugin {name}: {e}")
    return plugins

# --------------------- Background Tasks ---------------------

def thread_icon():
    global icon_dir
    while True:
        time.sleep(1)  # wait 1 second before updating again
        statuses = [plugin.get_status() for plugin in registered_plugins if hasattr(plugin, "get_status")]
        if "R" in statuses:
            indicator.set_icon_full(os.path.join(icon_dir, "demo-bad.png"), "Bad")
        elif "A" in statuses:
            indicator.set_icon_full(os.path.join(icon_dir, "demo-warn.png"), "Warn")
        else:
            indicator.set_icon_full(os.path.join(icon_dir, "demo-ok.png"), "OK")


#--------------------- Main Application ---------------------

indicator = AppIndicator3.Indicator.new(
    "buntu_tray_helper-indicator",
    "system-run",  # an icon name from system theme, or absolute path to .png/.svg
    AppIndicator3.IndicatorCategory.APPLICATION_STATUS
)

indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

# Build a simple menu
menu = Gtk.Menu()

item_quit = Gtk.MenuItem(label="Quit")
item_quit.connect("activate", quit_app)
menu.append(item_quit)

#get the plugins folder
registered_plugins = load_plugins()

menu.show_all()
indicator.set_menu(menu)

# Start the icon update thread as a daemon so it exits when the main program does
threading.Thread(target=thread_icon, daemon=True).start()

Gtk.main()
