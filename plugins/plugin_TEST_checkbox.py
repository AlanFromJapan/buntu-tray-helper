import socket
import threading
import time
import plugins.shared as shared
import pystray


__indicator = None
__thread = None
__thread_kill = False
__menu_item = None
__running = False

#The register function is required for the plugin system to recognize this file as a plugin.
def register(menu, indicator):
    global __indicator
    global __menu_item
    __indicator = indicator
    shared.logger.info("Plugin 'plugin_TEST_checkbox' registered")

    __menu_item = pystray.MenuItem("TEST - Checkbox", click_me, checked=is_checked)
    menu.append(__menu_item)

#return the visual checked state of the menu item
def is_checked(item):
    global __running
    return __running

# This function is called by the main application to get the current status of the plugin (RAG).
def get_status():
    #always return green as this is not a health check, and no way you can't send UDP packets (no reception check)
    return shared.default_ok_status()


__lock = threading.Lock()
def click_me(_, autostart=False):
    global __menu_item
    global __thread
    global __thread_kill
    global __lock
    global __running

    __running = not __running


