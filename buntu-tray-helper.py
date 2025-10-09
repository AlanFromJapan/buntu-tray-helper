import os
import threading
import time
import datetime
import gi
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Notify', '0.7')
from gi.repository import AppIndicator3, Gtk, Notify
#from gi.repository import GLib, Gdk

import importlib
import pkgutil
import json



# --------------------- Constants ---------------------

APP_ID = "buntu_tray_helper"

script_dir = os.path.dirname(os.path.abspath(__file__))
icon_dir = os.path.join(script_dir, "icon")

icon_prefix = None  # will be set later
# --------------------- Misc functions ---------------------

def quit_app(_):
    Gtk.main_quit()


def get_icon_path_from_status(status):
    global icon_prefix
    global icon_dir

    if icon_prefix is None:
        #load just once
        icon_prefix = get_config_json().get("icon-prefix", "demo")

    if status == "R":
        if datetime.datetime.now().second % 2 == 0:
            return os.path.join(icon_dir, f"{icon_prefix}-bad.png")
        else:
            return os.path.join(icon_dir, f"{icon_prefix}-bad-alt.png") if os.path.exists(os.path.join(icon_dir, f"{icon_prefix}-bad-alt.png")) else os.path.join(icon_dir, f"{icon_prefix}-bad.png")
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

# Show a notification popup
def show_notification(title, message, status=None):
    # Initialize Notify only once
    if not Notify.is_initted():
        Notify.init(APP_ID)
        
    n = Notify.Notification.new(title, message, get_icon_path_from_status(status) if status else None)
    n.show()


# Show the status of all plugins in a dialog
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

# Get the config json as a dictionary, create it if it doesn't exist
def get_config_json():
    global script_dir
    config_dir = os.path.join(script_dir, "config")
    config_file = os.path.join(config_dir, 'buntu-tray-helper.json')
    if not os.path.exists(config_file):
        with open(config_file, 'w') as f:
            f.write('{}')  # create empty json file
    with open(config_file, 'r') as f:
        return json.load(f)

# --------------------- Plugin Management ---------------------
registered_plugins = []
def load_plugins():
    global script_dir
    plugins = []

    for _, name, _ in pkgutil.iter_modules([os.path.join(script_dir, "plugins")]):
        if not  name.startswith("plugin_"):
            continue
        
        module = importlib.import_module(os.path.join("plugins", name).replace(os.sep, "."))
        if hasattr(module, "register"):
            try:
                module.register(menu, indicator)  # call convention
                plugins.append(module)
            except Exception as e:
                print(f"Error registering plugin {name}: {e}")
    return plugins

# --------------------- Background Tasks ---------------------

#Check the status of all plugins every second and update the icon accordingly
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


#Start all the autostart plugins
def thread_autostart_plugins():
    global registered_plugins
    time.sleep(5)  # wait 5 seconds before starting autostart plugins to allow the main app to settle
    print("🏁 Starting autostart plugins...")
    
    j = get_config_json()

    for plugin in registered_plugins:
        #if it can be autostarted, then just autostart it
        if hasattr(plugin, "autostart"):
            try:
                print(f"🏁 Autostarting plugin {plugin.__name__}...")
                #run it on different thread to avoid blocking the main thread
                threading.Thread(target=plugin.autostart(), daemon=True).start()
                time.sleep(0.1)  # wait a bit before starting the next one
            except Exception as e:
                print(f"Error autostarting plugin {plugin.__name__}: {e}")
    print("🏁 Starting autostart plugins... done.")


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

    # Start the autostart plugins thread as a daemon so it exits when the main program does
    threading.Thread(target=thread_autostart_plugins, daemon=True).start()

    Gtk.main()


if __name__ == "__main__":
    #Marked as deprecated in newer versions of PyGObject, but still needed for compatibility?
    #GLib.threads_init()
    #Gdk.threads_init()
    main()