from gi.repository import Gtk
import os

__state = True
__indicator = None

#The register function is required for the plugin system to recognize this file as a plugin.
def register(menu, indicator):
    global __indicator
    __indicator = indicator
    print("Plugin 'plugin_toggle' registered")

    menu_item = Gtk.MenuItem(label="Toggle Icon")
    menu_item.connect("activate", toggle_icon)
    menu.append(menu_item)


# This function is called by the main application to get the current status of the plugin (RAG).
def get_status():
    return "G"


def toggle_icon(_):
    global __state

    #folder where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_dir = os.path.join(script_dir, "..", "icon")
    print(script_dir)

    if __state:
        __indicator.set_icon_full(os.path.join(icon_dir, "demo-ok.png"), "OK")
    else:
        __indicator.set_icon_full(os.path.join(icon_dir, "demo-bad.png"), "Bad")
    __state = not __state
    return True  # keep timer running
