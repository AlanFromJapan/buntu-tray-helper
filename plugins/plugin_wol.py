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

#The register function is required for the plugin system to recognize this file as a plugin.
def register(menu, indicator):
    global __indicator
    __indicator = indicator
    print("Plugin 'plugin_wol' registered")

    menu_item = Gtk.MenuItem(label="WOL NAS")
    menu_item.connect("activate", send_wol)
    menu.append(menu_item)


def send_wol(_):
    print("Starting WOL sending thread...")
    __thread = threading.Thread(target=background_task, daemon=True)
    __thread.start()


def background_task():
    while True:
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

