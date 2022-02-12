#!/bin/bash

set -e

# check if we are running as sudo
if [[ $EUID -ne 0 ]]; then
    echo "Error: installation script must be run with superuser privileges to install the server as a service"
    exit 1
fi

# check that the preferred server port is free
if lsof -i:8000 && lsof -i:8000 | grep -q -E 'IPv4.*LISTEN'; then
    echo "Error: port 8000 is required to be free, but it is being used by another process. Aborting installation."
    exit 1
fi

# ensure we've got the necessary packages installed, and install them if required
echo "Checking for required dependencies"

packages=("git" "python3.7" "python3.7-venv")

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
[ -d .picamera-manager/server ] && {
echo "An existing installation has been detected. Would you like to overwrite it with a fresh installation? (All old data will be deleted)"
select yn in "Yes" "No"; do
    case $yn in
        Yes ) echo "Deleting previous installation..."; rm -rf .picamera-manager/server; [ -z "$(ls -A .picamera-manager)" ] && rmdir .picamera-manager; echo "...previous installation deleted!"; break;;
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

# take what we need and make a top level server directory
shopt -s dotglob
sudo -u pi mv picamera-manager/* .
shopt -u dotglob
sudo -u pi rm -rf picamera-manager
sudo -u pi rm -rf camera
cd server

# set up a fresh python virtual environment
echo "Setting up python virtual environment"
sudo -u pi python3.7 -m venv .venv

# install the required packages
echo "Installing required Python packages"
sudo -u pi .venv/bin/pip install --upgrade pip setuptools wheel
sudo -u pi .venv/bin/pip install --no-cache-dir -r requirements.txt

# set up the database
echo "Initialising data stores"
sudo -u pi mkdir -p data/cameras
sudo -u pi touch data/cam_manager.db
sudo -u pi .venv/bin/alembic upgrade head

# install the app as a service
echo "Installing the app as a service"
cp picamera_manager_server.service /etc/systemd/system/picamera_manager_server.service
systemctl daemon-reload
systemctl start picamera_manager_server.service
systemctl enable picamera_manager_server.service

# done!
echo "The Picamera Manager server has now been set up and is running on http://0.0.0.0:8000/"