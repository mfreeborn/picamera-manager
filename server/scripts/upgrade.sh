#!/bin/bash

set -e

# check if we are running as sudo
if [[ $EUID -ne 0 ]]; then
    echo "Error: upgrade script must be run with superuser privileges"
    exit 1
fi

# stop the picamera service
echo "Stopping Picamera server"
systemctl stop picamera_manager_server.service

cd /home/pi/.picamera-manager/server
# update repo
echo "Updating repository"
sudo -u pi git pull

echo "Updating server"
# update requirements
sudo -u pi .venv/bin/pip install -r requirements.txt
# and then update the database
sudo -u pi .venv/bin/alembic upgrade head

echo "Restarting the Picamera server"
cp picamera_manager_server.service /etc/systemd/system/picamera_manager_server.service
systemctl daemon-reload
systemctl start picamera_manager_server.service

echo "Upgrade complete"