from gi.repository import Gtk
import socket
import os
from dotenv import load_dotenv
import threading
import time

#load environment variables from a .env file
load_dotenv()

__indicator = None
__thread = None
__thread_kill = False
__menu_item = None

#The register function is required for the plugin system to recognize this file as a plugin.
def register(menu, indicator):
    global __indicator
    global __menu_item
    __indicator = indicator
    print("Plugin 'plugin_wol' registered")

    __menu_item = Gtk.CheckMenuItem(label="WOL NAS")
    __menu_item.connect("activate", send_wol)
    menu.append(__menu_item)


# This function is called by the main application to get the current status of the plugin (RAG).
def get_status():
    #always return green as this is not a health check, and no way you can't send UDP packets (no reception check)
    return {"status": "G", "failed": []}


def send_wol(_):
    global __menu_item
    global __thread
    global __thread_kill
    if __menu_item.get_active():
        __menu_item.set_active(True) # Keep it checked to show it's active

        print("Starting WOL sending thread...")
        __thread_kill = False
        __thread = threading.Thread(target=background_task, daemon=True)
        __thread.start()
    else:
        print("Stopping WOL sending thread...")
        __menu_item.set_active(False) # Keep it unchecked to show it's inactive
        __thread_kill = True
        # this will stop after the next sleep cycle in background_task, hoping user don't restart it before then


def background_task():
    global __thread_kill
    while not __thread_kill:
        print("Sending WOL packet...")

        # Replace with your NAS MAC address
        mac_address = os.getenv("WOL") or "00:11:22:33:44:55"

        # Build the magic packet
        mac_bytes = bytes.fromhex(mac_address.replace(":", ""))
        magic_packet = b'\xff' * 6 + mac_bytes * 16

        # Send the packet to the broadcast address on UDP port 9
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, ('<broadcast>', 9))

        print("WOL packet sent to", mac_address)

        time.sleep(3 * 60)  # Wait for 3 minutes before sending again
    print("WOL sending thread exiting...")
