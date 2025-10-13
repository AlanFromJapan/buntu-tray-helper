from gi.repository import Gtk
import os
import threading
import time
import asyncio
import json
from pysnmp.hlapi.v1arch.asyncio import *
import plugins.shared as shared
from gi.repository import GLib



__indicator = None
__thread = None
__thread_kill = False
__health = shared.default_ok_status()
__menu_item = None



#The register function is required for the plugin system to recognize this file as a plugin.
def register(menu, indicator):
    global __indicator
    global __menu_item
    __indicator = indicator


    shared.logger.info("Plugin 'plugin_snmp_health' registered")

    __menu_item = Gtk.CheckMenuItem(label="SNMP Health Check")
    __menu_item.set_active(True) #check by default
    __menu_item.connect("activate", do_snmp_health_check)
    menu.append(__menu_item)


#Will be called if the module is set to autostart in the config
def autostart():
    do_snmp_health_check(None, autostart=True)
    

# This function is called by the main application to get the current status of the plugin (RAG).
def get_status():
    global __health
    return __health if not __thread_kill else shared.default_ok_status()  # If thread is killed, return Green status


__lock = threading.Lock()
def do_snmp_health_check(_, autostart=False):
    global __menu_item
    global __thread
    global __thread_kill
    global __lock

    with __lock:
        shared.logger.debug(f"▶ do_snmp_health_check called, autostart={autostart}, thread={__thread}, thread_kill={__thread_kill}")
        #I don't know why the get_active() is True when clicked to deactivate, so invert the logic here
        if autostart or __thread is None :
            shared.logger.info("▶ Starting SNMP health check thread...")
            __thread_kill = False

            __thread = threading.Thread(target=background_task, daemon=True)
            __thread.start()

            GLib.idle_add(toggle_menu_item_state, True, priority=GLib.PRIORITY_DEFAULT_IDLE)
            shared.logger.info("▶ Starting SNMP health check thread... done.")
        else:
            shared.logger.info("▶ Stopping SNMP health check thread...")
            # No direct way to stop thread, but setting daemon=True means it will exit when main program exits
            __thread_kill = True

            GLib.idle_add(toggle_menu_item_state, False, priority=GLib.PRIORITY_DEFAULT_IDLE)
            # this will stop after the next sleep cycle in background_task, hoping user don't restart it before then

        #Toggle the check state to reflect the new state
        shared.logger.debug("👉 Toggling SNMP health check menu item state done." + str(__menu_item.get_active()))


def toggle_menu_item_state(state: bool):
    global __menu_item
    if __menu_item:
        __menu_item.set_active(state)
    #run once for Gtk idle loop
    return False


async def snmp_get(host: str, oid: str, port: int = 161, community: str = "public", dyn_check:str= None):
    health_result = shared.default_ok_status()

    with SnmpDispatcher() as snmpDispatcher:
        iterator = await get_cmd(
            snmpDispatcher,
            CommunityData(community, mpModel=0),
            await UdpTransportTarget.create((host, port)),
            (oid, None),
        )

        errorIndication, errorStatus, errorIndex, varBinds = iterator

        if errorIndication:
            shared.logger.error(f"SNMP error indication: {errorIndication}")

        elif errorStatus:
            shared.logger.error(
                "{} at {}".format(
                    errorStatus.prettyPrint(),
                    errorIndex and varBinds[int(errorIndex) - 1][0] or "?",
                )
            )
        else:
            for varBind in varBinds:
                shared.logger.debug(" = ".join([x.prettyPrint() for x in varBind]))

                # Dynamic exec of code to check value True/False
                if dyn_check:
                    try:
                        check = "response = True if " + dyn_check + " else False"
                        local_vars = {'response': None, 'value': varBind[1].prettyPrint()}
                        exec(check, {}, local_vars)
                        response = local_vars['response']
                        shared.logger.debug(f"Dynamic check '{dyn_check}' evaluated to {response}")
                        if not response:
                            health_result["status"] = "R"
                            health_result["failed"].append(f"Check failed: {dyn_check} with value {varBind[1].prettyPrint()}")
                        else:
                            if health_result["status"] != "R":
                                health_result["status"] = "G"  # Only set to Green if not already Red

                    except ValueError:
                        shared.logger.error(f"Invalid dynamic check value: {dyn_check}")
                        health_result["status"] = "R"
                        health_result["failed"].append(f"Invalid check: {dyn_check}")
    return health_result



def background_task(run_once=False):
    global __health
    global __thread_kill
    global __thread

    while not __thread_kill:
        config = shared.get_plugin_config('snmp_health.json')

        new_health = shared.default_ok_status()  # Reset health status before checks
        for server in config.get('servers', []):
            # SNMP Check Logic
            ip = server.get('server')  # Example IP from config
            port = server.get('port', 161)  # Default SNMP port is 161
            for entry in server.get('oids', []):
                oid = entry["oid"]
                dyn_check = entry.get("dyn_check", None)
                descr = entry.get("description", oid)

                result = None
                try:
                    shared.logger.debug(f"Checking SNMP OID [{descr}] on {ip}:{port}")

                    result = asyncio.run(snmp_get(ip, oid=oid, port=port, community='public', dyn_check=dyn_check))
                except Exception as e:
                    shared.logger.error(f"Error checking SNMP OID [{descr}] on {ip}:{port} - {e}")

                if result is None or result["status"] in ["R", "?"]:
                    new_health["status"] = "R"
                    new_health["failed"].append(f"SNMP check failed for {ip} OID [{descr}]")

        __health = new_health

        if run_once:
            break
        shared.logger.debug("-"*40)

        time.sleep(int(config.get("config", {}).get("frequency_in_sec", 180)))  # Wait for the configured frequency before checking again
    shared.logger.info("🪦 SNMP health check thread exiting.")
    __thread = None


