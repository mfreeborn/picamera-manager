#!/bin/bash

# check if we are running as sudo
if [[ $EUID -ne 0 ]]; then
    echo "Error: uninstallation script must be run with superuser privileges to remove the client as a service"
    exit 1
fi

echo "Uninstalling the client will remove all files and associated data. Are you sure you wish to continue?"
select yn in "Yes" "No"; do
    case $yn in
        Yes ) break;;
        No ) exit;;
    esac
done

echo "Stopping client"
systemctl stop picamera_manager_client.service
systemctl disable picamera_manager_client.service
rm /etc/systemd/system/picamera_manager_client.service

echo "Removing all files..."
rm -rf /home/pi/.picamera-manager

echo "Uninstallation complete"