from gi.repository import Gtk
import socket
import threading
import time
import plugins.shared as shared


__indicator = None
__thread = None
__thread_kill = False
__menu_item = None

#The register function is required for the plugin system to recognize this file as a plugin.
def register(menu, indicator):
    global __indicator
    global __menu_item
    __indicator = indicator
    shared.logger.info("Plugin 'plugin_wol' registered")

    __menu_item = Gtk.CheckMenuItem(label="Wake-On-LAN (WOL)")
    __menu_item.connect("activate", send_wol)
    menu.append(__menu_item)


# This function is called by the main application to get the current status of the plugin (RAG).
def get_status():
    #always return green as this is not a health check, and no way you can't send UDP packets (no reception check)
    return shared.default_ok_status()


__lock = threading.Lock()
def send_wol(_, autostart=False):
    global __menu_item
    global __thread
    global __thread_kill
    global __lock
    
    with __lock:
        if autostart or __menu_item.get_active():
            __menu_item.set_active(True) # Keep it checked to show it's active

            shared.logger.info("Starting WOL sending thread...")
            __thread_kill = False
            __thread = threading.Thread(target=background_task, daemon=True)
            __thread.start()
        else:
            shared.logger.info("Stopping WOL sending thread...")
            __menu_item.set_active(False) # Keep it unchecked to show it's inactive
            __thread_kill = True
            # this will stop after the next sleep cycle in background_task, hoping user don't restart it before then


def background_task():
    global __thread_kill
    while not __thread_kill:
        config = shared.get_plugin_config('wol.json')
        for device in config.get('devices', []):
            mac_address = device.get('mac', '')
            if mac_address != '':
                try:
                    shared.logger.debug(f"Preparing to send WOL packet to '{device.get('name', '<unknown>')}' [{mac_address}] ...")
                    # Build the magic packet
                    mac_bytes = bytes.fromhex(mac_address.replace(":", ""))
                    magic_packet = b'\xff' * 6 + mac_bytes * 16

                    # Send the packet to the broadcast address on UDP port 9
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                        sock.sendto(magic_packet, ('<broadcast>', 9))

                    shared.logger.info(f"WOL packet sent to '{device.get('name', '<unknown>')}' [{mac_address}].")
                except Exception as e:
                    shared.logger.error(f"Error sending WOL packet to {mac_address}: {e}")

        frequency_sec = int(config.get('settings', {}).get('frequency_sec', 180))
        time.sleep(frequency_sec)
    shared.logger.info("🪦 WOL sending thread exiting...")
