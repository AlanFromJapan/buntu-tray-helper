from gi.repository import Gtk
import os
from dotenv import load_dotenv
import threading
import time
import asyncio
import json
from pysnmp.hlapi.v1arch.asyncio import *

#load environment variables from a .env file
load_dotenv()

__indicator = None
__thread = None
__thread_kill = False
__health = {"status": "G", "failed": []}
__menu_item = None



#The register function is required for the plugin system to recognize this file as a plugin.
def register(menu, indicator):
    global __indicator
    global __menu_item
    __indicator = indicator


    print("Plugin 'plugin_snmp_health' registered")

    __menu_item = Gtk.CheckMenuItem(label="SNMP Health Check")
    __menu_item.connect("activate", do_snmp_health_check)
    menu.append(__menu_item)


# This function is called by the main application to get the current status of the plugin (RAG).
def get_status():
    global __health
    return __health["status"]


def do_snmp_health_check(_):
    global __menu_item
    global __thread
    global __thread_kill

    if __menu_item.get_active():
        __menu_item.set_active(True) # Keep it checked to show it's active

        print("Starting SNMP health check thread...")
        __thread_kill = False
        __thread = threading.Thread(target=background_task, daemon=True)
        __thread.start()
    else:
        print("Stopping SNMP health check thread...")
        __menu_item.set_active(False) # Keep it unchecked to show it's inactive
        # No direct way to stop thread, but setting daemon=True means it will exit when main program exits
        __thread_kill = True
        # this will stop after the next sleep cycle in background_task, hoping user don't restart it before then


async def snmp_get(host: str, oid: str, port: int = 161, community: str = "public", dyn_check:str= None):
    health_result = {"status": "?", "failed": []}

    with SnmpDispatcher() as snmpDispatcher:
        iterator = await get_cmd(
            snmpDispatcher,
            CommunityData(community, mpModel=0),
            await UdpTransportTarget.create((host, port)),
            (oid, None),
        )

        errorIndication, errorStatus, errorIndex, varBinds = iterator

        if errorIndication:
            print(errorIndication)

        elif errorStatus:
            print(
                "{} at {}".format(
                    errorStatus.prettyPrint(),
                    errorIndex and varBinds[int(errorIndex) - 1][0] or "?",
                )
            )
        else:
            for varBind in varBinds:
                print(" = ".join([x.prettyPrint() for x in varBind]))

                # Dynamic exec of code to check value True/False
                if dyn_check:
                    try:
                        check = "response = True if " + dyn_check + " else False"
                        local_vars = {'response': None, 'value': varBind[1].prettyPrint()}
                        exec(check, {}, local_vars)
                        response = local_vars['response']
                        print(f"Dynamic check '{dyn_check}' evaluated to {response}")
                        if not response:
                            health_result["status"] = "R"
                            health_result["failed"].append(f"Check failed: {dyn_check} with value {varBind[1].prettyPrint()}")
                        else:
                            if health_result["status"] != "R":
                                health_result["status"] = "G"  # Only set to Green if not already Red

                    except ValueError:
                        print(f"Invalid dynamic check value: {dyn_check}")
                        health_result["status"] = "R"
                        health_result["failed"].append(f"Invalid check: {dyn_check}")
    return health_result



def background_task(run_once=False):
    global __health
    global __thread_kill

    while not __thread_kill:
        # Re-Load config each time in case it changes
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(script_dir, "..", "config")
        with open(os.path.join(config_dir, 'snmp_health.json'), 'r') as f:
            config = json.load(f)

        for server in config.get('servers', []):
            # SNMP Check Logic
            ip = server.get('server')  # Example IP from config
            port = server.get('port', 161)  # Default SNMP port is 161
            __health = {"status": "G", "failed": []} # Reset health status before checks
            for entry in server.get('oids', []):
                oid = entry["oid"]
                dyn_check = entry.get("dyn_check", None)

                print(f"Checking SNMP OID {oid} on {ip}:{port}")
                result = asyncio.run(snmp_get(ip, oid=oid, port=port, community='public', dyn_check=dyn_check))

                if result["status"] == "R":
                    __health["status"] = "R"
                    __health["failed"].extend(result["failed"])

        if run_once:
            break
        time.sleep(int(config.get("config", {}).get("frequency_in_sec", 180)))  # Wait for the configured frequency before checking again
    print("SNMP health check thread exiting...")
