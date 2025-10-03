import os
import threading
import time
import gi
gi.require_version('AppIndicator3', '0.1')
from gi.repository import AppIndicator3, Gtk, Notify

import importlib
import pkgutil

from dotenv import load_dotenv


APP_ID = "buntu_tray_helper"

#load environment variables from a .env file
load_dotenv()

script_dir = os.path.dirname(os.path.abspath(__file__))
icon_dir = os.path.join(script_dir, "icon")

def quit_app(_):
    Gtk.main_quit()


def get_icon_path_from_status(status):
    icon_prefix = os.getenv("ICON_PREFIX", "demo")
    if status == "R":
        return os.path.join(icon_dir, f"{icon_prefix}-bad.png")
    elif status == "A":
        return os.path.join(icon_dir, f"{icon_prefix}-warn.png")
    else:
        return os.path.join(icon_dir, f"{icon_prefix}-ok.png")


def get_status_text_from_status(status):
    if status == "R":
        return "Bad"
    elif status == "A":
        return "Warn"
    else:
        return "OK"


def show_notification(title, message, status=None):
    # Initialize Notify only once
    if not Notify.is_initted():
        Notify.init(APP_ID)
        
    n = Notify.Notification.new(title, message, get_icon_path_from_status(status) if status else None)
    n.show()


def show_status(_):
    print("Status clicked")

    msg = []
    for plugin in registered_plugins:
        if hasattr(plugin, "get_status"):
            status = plugin.get_status()
            if status["status"] == "R":
                # Here you could add code to show a dialog or notification
                m = f"Plugin {plugin.__name__} failed:\n"
                for failure in status["failed"]:
                    m += f"- {failure}\n"
                msg.append(m)

    if len(msg) > 0:
        dialog = Gtk.MessageDialog(parent=None, flags=0, message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK, text="This is a WARNING MessageDialog")
        dialog.format_secondary_text("\n".join(msg))
        dialog.run()

        dialog.destroy()
    else:
        dialog = Gtk.MessageDialog(parent=None, flags=0, message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK, text="This is an INFO MessageDialog")
        dialog.format_secondary_text("All good.")
        dialog.run()

        dialog.destroy()


registered_plugins = []
def load_plugins():
    global script_dir
    plugins = []

    for _, name, _ in pkgutil.iter_modules([os.path.join(script_dir, "plugins")]):
        if not  name.startswith("plugin_"):
            continue
        
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
    global APP_ID
    current_status = "G"
    while True:
        time.sleep(1)  # wait 1 second before updating again
        new_status = "G"
        statuses = [plugin.get_status()["status"] for plugin in registered_plugins if hasattr(plugin, "get_status")]
        if "R" in statuses:
            indicator.set_icon_full(get_icon_path_from_status("R"), get_status_text_from_status("R"))
            new_status = "R"
        elif "A" in statuses:
            indicator.set_icon_full(get_icon_path_from_status("A"), get_status_text_from_status("A"))
            new_status = "A"
        else:
            indicator.set_icon_full(get_icon_path_from_status("G"), get_status_text_from_status("G"))
            new_status = "G"
        
        if new_status != current_status:
            current_status = new_status
            show_notification(APP_ID +" ~ Status Changed", f"Overall status changed to [{get_status_text_from_status(new_status)}]", new_status)


#--------------------- Main Application ---------------------
indicator = None
menu = None
def main():
    global indicator
    global menu
    global registered_plugins

    indicator = AppIndicator3.Indicator.new(
        APP_ID,
        "system-run",  # an icon name from system theme, or absolute path to .png/.svg
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS
    )

    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    # Build a simple menu
    menu = Gtk.Menu()

    #Quit menu on top
    item_quit = Gtk.MenuItem(label="Quit")
    item_quit.connect("activate", quit_app)
    menu.append(item_quit)

    #separator BEFORE the plugins
    menu.append(Gtk.SeparatorMenuItem())    

    #get the plugins folder
    registered_plugins = load_plugins()

    #separator AFTER the plugins
    menu.append(Gtk.SeparatorMenuItem())    

    #Show the status menu item
    item_show_status = Gtk.MenuItem(label="Show Status")
    item_show_status.connect("activate", show_status)
    menu.append(item_show_status)

    #show the menu
    menu.show_all()
    indicator.set_menu(menu)

    # Start the icon update thread as a daemon so it exits when the main program does
    threading.Thread(target=thread_icon, daemon=True).start()

    Gtk.main()


if __name__ == "__main__":
    main()