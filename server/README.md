# Picamera Manager - Server Application

This application provides a local web interface from which one or more Raspberry Pi camera devices (running the appropriate [camera software](https://github.com/mfreeborn/picamera-manager/tree/master/camera)) can be managed.

## Installation

### Prerequisites

* Raspberry Pi 3b or more powerful
* `python3.7` and `python3.7-venv`
* Git

### Steps

* Download and run the install script:

```bash
$ sudo wget https://raw.githubusercontent.com/mfreeborn/picamera-manager/master/server/scripts/install.sh > bash
```

### Upgrading

To upgrade to the latest version, run the following command in your terminal:

```bash
$ sudo ~/.picamera-manger/server/scripts/upgrade.sh
```

### Uninstalling

To uninstall, run the following command in your terminal:

```bash
$ sudo ~/.picamera-manger/server/scripts/uninstall.sh
```