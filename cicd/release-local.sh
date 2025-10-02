#!/bin/bash

# Create a folder in ~/AppImage if it doesn't exist
mkdir -p ~/AppImage/buntu-tray-helper

# Copy current code to that folder
rsync -av --exclude='.git' --exclude='cicd' ~/Git/buntu-tray-helper/ ~/AppImage/buntu-tray-helper/

#make it autostart
mkdir -p ~/.config/autostart
cp ~/Git/buntu-tray-helper/cicd/buntu-tray-helper.desktop ~/.config/autostart/

#that's it!
echo "Local release prepared in ~/AppImage/buntu-tray-helper"