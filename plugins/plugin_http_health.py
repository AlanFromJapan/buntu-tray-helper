import os
import threading
import time
import json
import urllib.request
import urllib.error
import ssl
import plugins.shared as shared
import pystray


__indicator = None
__thread = None
__thread_kill = False
__health = shared.default_ok_status()
__menu_item = None
__running = False


#The register function is required for the plugin system to recognize this file as a plugin.
def register(menu, indicator):
    global __indicator
    global __menu_item
    __indicator = indicator

    shared.logger.info("Plugin 'plugin_http_health' registered")

    __menu_item = pystray.MenuItem("HTTP Health Check", do_http_health_check, checked=is_checked)
    menu.append(__menu_item)


#return the visual checked state of the menu item
def is_checked(item):
    global __thread
    return __thread is not None and __thread.is_alive()


#Will be called if the module is set to autostart in the config
def autostart():
    do_http_health_check(None, autostart=True)


# This function is called by the main application to get the current status of the plugin (RAG).
def get_status():
    global __health
    return __health if not __thread_kill else shared.default_ok_status()  # If thread is killed, return Green status


__lock = threading.Lock()
def do_http_health_check(_, autostart=False):
    global __menu_item
    global __thread
    global __thread_kill
    global __lock
    global __running

    with __lock:
        if (not __running and not __thread_kill) or (not __running and autostart):
            #NOT running, NOT marked for kill: Start it

            shared.logger.info("Starting HTTP health check thread...")
            __thread = threading.Thread(target=background_task, daemon=True)
            __thread.start()
        else:
            shared.logger.info("Stopping HTTP health check thread...")
            __thread_kill = True
            __running = False #needed to remember that the function is disabled while the thread my be waiting to terminate
            # this will stop after the next sleep cycle in background_task, hoping user don't restart it before then


def http_get(url: str, timeout: int = 30, expected_text: str = None, expected_status: int = 200):
    """
    Perform HTTP GET request and check response
    Returns: {"status": "G|R|?", "failed": []}
    """
    health_result = shared.default_ok_status()
    
    try:
        # Create request with timeout
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'buntu-tray-helper/1.0')
        
        # Create SSL context that ignores certificate validation
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
            status_code = response.getcode()
            response_data = response.read().decode('utf-8', errors='ignore')
            
            # Check status code
            if status_code != expected_status:
                health_result["status"] = "R"
                health_result["failed"].append(f"HTTP {url} returned status {status_code}, expected {expected_status}")
                return health_result
            
            # Check for expected text if specified
            if expected_text and expected_text not in response_data:
                health_result["status"] = "R"
                health_result["failed"].append(f"HTTP {url} response does not contain expected text: '{expected_text}'")
                return health_result
                
            shared.logger.info(f"HTTP check successful for {url} - Status: {status_code}")
            
    except urllib.error.HTTPError as e:
        health_result["status"] = "R"
        health_result["failed"].append(f"HTTP {url} returned error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        health_result["status"] = "R"
        health_result["failed"].append(f"HTTP {url} connection failed: {e.reason}")
    except Exception as e:
        health_result["status"] = "R"
        health_result["failed"].append(f"HTTP {url} check failed: {str(e)}")
    
    return health_result


def background_task(run_once=False):
    global __health
    global __thread_kill
    global __running

    if __thread_kill or __running:
        return

    #set
    __thread_kill = False
    __running = True
    
    while not __thread_kill:
        config = shared.get_plugin_config('http_health.json')

        __health = shared.default_ok_status()  # Reset health status before checks
        
        for url_config in config.get('urls', []):
            url = url_config.get('url')
            if not url:
                continue
                
            timeout = url_config.get('timeout', 30)
            expected_text = url_config.get('expected_text')
            expected_status = url_config.get('expected_status', 200)

            shared.logger.debug(f"Checking HTTP URL: {url}")
            result = http_get(url, timeout=timeout, expected_text=expected_text, expected_status=expected_status)

            if result["status"] in ["R", "?"]:
                __health["status"] = "R"
                __health["failed"].append(result["failed"])

        if run_once:
            break
            
        frequency = config.get("config", {}).get("frequency_in_sec", 300)  # Default 5 minutes
        time.sleep(frequency)

    #reset
    __running = False
    __thread_kill = False
    shared.logger.info("🪦 HTTP health check thread exiting...")