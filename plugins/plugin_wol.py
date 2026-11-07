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
    shared.logger.info("Plugin 'plugin_wol' registered")

    __menu_item = pystray.MenuItem("Wake-On-LAN (WOL)", send_wol, checked=is_checked)
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
def send_wol(_, autostart=False):
    global __menu_item
    global __thread
    global __thread_kill
    global __lock
    global __running
    
    with __lock:
        if (not __running and not __thread_kill) or (not __running and autostart):
            #NOT running, NOT marked for kill: Start it
            
            shared.logger.info("Starting WOL sending thread...")
            __thread = threading.Thread(target=background_task, daemon=True)
            __thread.start()
        else:
            shared.logger.info("Stopping WOL sending thread...")
            __thread_kill = True
            __running = False #needed to remember that the function is disabled while the thread my be waiting to terminate


def background_task():
    global __thread_kill
    global __running

    if __thread_kill or __running:
        return

    #set
    __thread_kill = False
    __running = True

    #start background task loop
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

    #reset    
    __thread_kill = False
    __running = False
    shared.logger.info("🪦 WOL sending thread exiting...")
