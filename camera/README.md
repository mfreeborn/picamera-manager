# Picamera Manager - Camera Application

This application works in unison with the [server application](https://github.com/mfreeborn/picamera-manager/tree/master/server) and should be installed on a Raspberry Pi with an attached Raspberry Pi camera.

## Installation

### Prerequisites

* Raspberry Pi 0 or greater
* Raspberry Pi camera v1.2 or HQ
* `python3.7` and `python3.7-venv`
* Git

### Steps

* Download and run the install script:

```bash
$ sudo wget https://raw.githubusercontent.com/mfreeborn/picamera-manager/master/camera/scripts/install.sh > bash
```

### Upgrading

To upgrade to the latest version, run the following command in your terminal:

```bash
$ sudo ~/.picamera-manger/camera/scripts/upgrade.sh
```

### Uninstalling

To uninstall, run the following command in your terminal:

```bash
$ sudo ~/.picamera-manger/camera/scripts/uninstall.sh
```