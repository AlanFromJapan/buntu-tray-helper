# buntu-tray-helper
A simple Ubuntu app to control different functions (wake my NAS with WOL, monitor status of servers via SNMP, services status via HTTP(s)) from the system tray.

![sample screenshot](assets/screenshot1.png)


![App Icon](icon/appicon.png)

## What it looks like

- <img src="icon/logo1-ok.png" width="32" /> All  good
- <img src="icon/logo1-warn.png" width="32" /> Warning
- <img src="icon/logo1-bad.png" width="32" /> Error (blinks every second between red dot and yellow dot)



## What it does

- [x] SNMP check : get an answer and can evaluate a simple expression that resolves to True (ok) or False (bad)
- [x] HTTP(s) check: checks that a given URL answers a 200 and that some specific text can be found in the answer. Certificate checks are ignored.
- [x] WOL (Wake-on-LAN): can send the magic packet to multiple devices to turn them and keep them on
- [x] Works on Ubuntu 22.04 and 24.04

# Setup

## Get the code
```bash
sudo apt install python3-gi gir1.2-appindicator3-0.1

#need to set access to OS level packages (installed above)
python3 -m venv . --system-site-packages
#or edit pyvenv.cfg and set "include-system-site-packages = true"

source bin/activate

python -m pip install -r requirements.txt
```

## Configure

Copy the `*.sample.json` files in config in the same folder but remove the `.sample`. Edit to your liking, it should be quite straightforward.

## Run

```bash
python buntu-tray-helper.py
```
