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
import logging
from logging.handlers import RotatingFileHandler

import subprocess

# --------------------- Constants ---------------------

APP_ID = "buntu_tray_helper"

script_dir = os.path.dirname(os.path.abspath(__file__))
icon_dir = os.path.join(script_dir, "icon")

icon_prefix = None  # will be set later

# --------------------- Logging Setup ---------------------

def setup_logging():
    """Setup logging with both stdout and rotating file handlers."""
    global script_dir
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(script_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(APP_ID)
    logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Rotating file handler
    log_file = os.path.join(logs_dir, f"{APP_ID}.log")
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=1*1024*1024,  # 1MB
        backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

# --------------------- Misc functions ---------------------

def quit_app(_):
    logger.info("Quitting application...")
    logger.info("="*50)
    Gtk.main_quit()


def get_icon_path_from_status(status):
    global icon_prefix
    global icon_dir

    if icon_prefix is None:
        #load just once
        icon_prefix = get_config_json().get("icons_prefix", "demo")

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


def open_log_file(_):
    """Open the current log file with system default editor."""
    logs_dir = os.path.join(script_dir, "logs")
    log_file = os.path.join(logs_dir, f"{APP_ID}.log")
    
    if os.path.exists(log_file):
        try:
            # Use xdg-open on Linux to open with default application
            subprocess.run(['xdg-open', log_file], check=True)
            logger.info(f"Opened log file: {log_file}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to open log file: {e}")
            show_notification("Error", f"Failed to open log file: {e}", "R")
        except FileNotFoundError:
            logger.error("xdg-open not found. Cannot open log file.")
            show_notification("Error", "xdg-open not found. Cannot open log file.", "R")
    else:
        logger.warning(f"Log file does not exist: {log_file}")
        show_notification("Warning", "Log file does not exist yet.", "A")


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
            logger.info(f"Overall status changed from {current_status} to {new_status}")
            current_status = new_status
            show_notification(APP_ID +" ~ Status Changed", f"Overall status changed to [{get_status_text_from_status(new_status)}]", new_status)


#Start all the autostart plugins
def thread_autostart_plugins():
    global registered_plugins
    time.sleep(5)  # wait 5 seconds before starting autostart plugins to allow the main app to settle
    logger.info("🏁 Starting autostart plugins...")
    
    j = get_config_json()

    for plugin in registered_plugins:
        #if it can be autostarted, then just autostart it
        if hasattr(plugin, "autostart"):
            try:
                logger.info(f"🏁 Autostarting plugin {plugin.__name__}...")
                #run it on different thread to avoid blocking the main thread
                threading.Thread(target=plugin.autostart, daemon=True).start()
                time.sleep(0.1)  # wait a bit before starting the next one
            except Exception as e:
                logger.error(f"Error autostarting plugin {plugin.__name__}: {e}")
    logger.info("🏁 Starting autostart plugins... done.")


#--------------------- Main Application ---------------------
indicator = None
menu = None
def main():
    global indicator
    global menu
    global registered_plugins

    logger.info(f"Starting {APP_ID} application")

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

    #Open log file menu item
    item_open_log = Gtk.MenuItem(label="Open Log File")
    item_open_log.connect("activate", open_log_file)
    menu.append(item_open_log)

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