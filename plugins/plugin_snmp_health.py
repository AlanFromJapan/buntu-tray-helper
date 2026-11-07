import os
import threading
import time
import asyncio
import json
from pysnmp.hlapi.v1arch.asyncio import *
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
    shared.logger.info("Plugin 'plugin_snmp_health' registered")

    __menu_item = pystray.MenuItem("SNMP Health Check", do_snmp_health_check, checked=is_checked)
    menu.append(__menu_item)


#return the visual checked state of the menu item
def is_checked(item):
    global __running
    return __running

#Will be called if the module is set to autostart in the config
def autostart():
    do_snmp_health_check(None, autostart=True)
    

# This function is called by the main application to get the current status of the plugin (RAG).
def get_status():
    global __health
    global __thread_kill
    global __running
    
    return __health if not __thread_kill or not __running else shared.default_ok_status()  # If thread is killed, return Green status


__lock = threading.Lock()
def do_snmp_health_check(_, autostart=False):
    global __menu_item
    global __thread
    global __thread_kill
    global __lock
    global __running

    with __lock:
        shared.logger.debug(f"▶ do_snmp_health_check called, autostart={autostart}, thread={__thread}, thread_kill={__thread_kill}")

        if (not __running and not __thread_kill) or (not __running and autostart):
            #NOT running, NOT marked for kill: Start it
            shared.logger.info("▶ Starting SNMP health check thread...")
            __thread = threading.Thread(target=background_task, daemon=True)
            __thread.start()
        else:
            shared.logger.info("▶ Stopping SNMP health check thread...")
            # No direct way to stop thread, but setting daemon=True means it will exit when main program exits
            __thread_kill = True
            __running = False #needed to remember that the function is disabled while the thread my be waiting to terminate

            # this will stop after the next sleep cycle in background_task, hoping user don't restart it before then




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
    global __running

    if __thread_kill or __running:
        return

    #set
    __thread_kill = False
    __running = True

    #start background task loop    
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

    #reset    
    __thread_kill = False
    __running = False
    shared.logger.info("🪦 SNMP health check thread exiting.")


