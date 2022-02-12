#!/bin/bash

# check if we are running as sudo
if [[ $EUID -ne 0 ]]; then
    echo "Error: uninstallation script must be run with superuser privileges to remove the server as a service"
    exit 1
fi

echo "Uninstalling the server will remove all files and associated data. Are you sure you wish to continue?"
select yn in "Yes" "No"; do
    case $yn in
        Yes ) break;;
        No ) exit;;
    esac
done

echo "Stopping server"
systemctl stop picamera_manager_server.service
systemctl disable picamera_manager_server.service
rm /etc/systemd/system/picamera_manager_server.service

echo "Removing all files..."
rm -rf /home/pi/.picamera-manager

echo "Uninstallation complete"