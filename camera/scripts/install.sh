#!/bin/bash

set -e

# check if we are running as sudo
if [[ $EUID -ne 0 ]]; then
    echo "Error: installation script must be run with superuser privileges to install the program as a service"
    exit 1
fi

# check that the preferred server port is free
if lsof -i:9000 && lsof -i:9000 | grep -q -E 'IPv4.*LISTEN'; then
    echo "Error: port 9000 is required to be free, but it is being used by another process. Aborting installation."
    exit 1
fi

# ensure we've got the necessary packages installed, and install them if required
echo "Checking for required dependencies"

packages=("git" "python3.7" "python3.7-venv" "libatlas-base-dev")

for pkg in ${packages[@]}; do
    if [ $(dpkg-query -W -f='${Status}' ${pkg} 2>/dev/null | grep -c "ok installed") -eq 1 ]; then
        echo "    ${pkg} is installed"
    else
	echo "    ${pkg} is not installed. Installing now..."
	apt install -y ${pkg}
    fi
done

cd /home/pi

# if an installation is already detected, offer to overwrite or abort
[ -d .picamera-manager/camera ] && {
echo "An existing installation has been detected. Would you like to overwrite it with a fresh installation? (All old data will be deleted)"
select yn in "Yes" "No"; do
    case $yn in
        Yes ) echo "Deleting previous installation..."; rm -rf .picamera-manager/camera; [ -z "$(ls -A .picamera-manager)" ] && rmdir .picamera-manager; echo "...previous installation deleted!"; break;;
        No ) echo "Exiting installation script"; exit;;
    esac
done
}

echo "Creating installation directory located in /home/pi/.picamera-manager"
sudo -u pi mkdir -p .picamera-manager
cd .picamera-manager

# grab the files from GitHub
echo "Running app installation"
sudo -u pi git clone --depth=1 git@github.com:mfreeborn/picamera-manager.git

# take what we need and make a top level camera directory
shopt -s dotglob
sudo -u pi mv picamera-manager/* .
shopt -u dotglob
sudo -u pi rm -rf picamera-manager
sudo -u pi rm -rf server
cd client

# set up a fresh python virtual environment
echo "Setting up Python virtual environment"
sudo -u pi python3.7 -m venv .venv

# install the required packages
echo "Installing required Python packages"
sudo -u pi .venv/bin/pip install --upgrade pip setuptools wheel
sudo -u pi .venv/bin/pip install --no-cache-dir -r requirements.txt

# create a blank config file
echo "Setting up default configuration"
sudo -u pi cp camera_config_template.toml camera_config.toml

# install the app as a service
echo "Installing the app as a service"
cp picamera_manager_camera.service /etc/systemd/system/picamera_manager_camera.service
systemctl daemon-reload
systemctl start picamera_manager_camera.service
systemctl enable picamera_manager_camera.service

# done!
echo "The Picamera Manager camera application has now been set up and is running on http://0.0.0.0:9000/"
