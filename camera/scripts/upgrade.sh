#!/bin/bash

set -e

# check if we are running as sudo
if [[ $EUID -ne 0 ]]; then
    echo "Error: upgrade script must be run with superuser privileges"
    exit 1
fi

# stop the picamera service
echo "Stopping Picamera client"
systemctl stop picamera_manager_client.service

cd /home/pi/.picamera-manager/client
# update repo
echo "Updating repository"
sudo -u pi git pull

echo "Updating client"
sudo -u pi .venv/bin/pip install -r requirements.txt

echo "Restarting the Picamera client"
cp picamera_manager_client.service /etc/systemd/system/picamera_manager_client.service
systemctl daemon-reload
systemctl start picamera_manager_client.service

echo "Upgrade complete"