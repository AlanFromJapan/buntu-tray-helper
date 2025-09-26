# buntu-tray-helper
A simple Ubuntu app to control different functions (wake my NAS with WOL, monitor status of servers) from the system tray

## Setup
```bash
sudo apt install python3-gi gir1.2-appindicator3-0.1

#need to set access to OS level packages (installed above)
python3 -m venv . --system-site-packages
#or edit pyvenv.cfg and set "include-system-site-packages = true"

source bin/activate

python -m pip install -r requirements.txt
```

## Run

```bash
python buntu-tray-helper.py
```
