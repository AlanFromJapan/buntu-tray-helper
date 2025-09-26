import os
import gi
gi.require_version('AppIndicator3', '0.1')
from gi.repository import AppIndicator3, Gtk

import importlib
import pkgutil

from dotenv import load_dotenv

#load environment variables from a .env file
load_dotenv()

def quit_app(_):
    Gtk.main_quit()


def load_plugins():
    plugins = []

    script_dir = os.path.dirname(os.path.abspath(__file__))

    for finder, name, ispkg in pkgutil.iter_modules([os.path.join(script_dir, "plugins")]):
        print(f"Found plugin: {name}")
        module = importlib.import_module(os.path.join("plugins", name).replace(os.sep, "."))
        if hasattr(module, "register"):
            plugins.append(module)
            module.register(menu, indicator)  # call convention
    return plugins


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
load_plugins()

menu.show_all()
indicator.set_menu(menu)

Gtk.main()
