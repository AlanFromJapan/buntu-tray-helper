
import json
import os


#What an OK status looks like
def default_ok_status():
    return {"status": "G", "failed": []}


def get_plugin_config(config_file_name: str):
    """
    Get the plugin configuration from a JSON file.
    """
    if config_file_name is None:
        return {}
    if not config_file_name.endswith('.json'):
        return {}
    
    # Re-Load config each time in case it changes
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(script_dir, "..", "config")
    # Ensure config directory exists
    if not os.path.exists(config_dir):
        return {}
    # Ensure config file exists
    if not os.path.exists(os.path.join(config_dir, config_file_name)):
        return {}
    with open(os.path.join(config_dir, config_file_name), 'r') as f:
        return json.load(f)