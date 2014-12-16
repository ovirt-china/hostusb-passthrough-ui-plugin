# Introduction
A UI plugin of oVirt webadmin to passthrough host USB devices into guests

# Installation and Setup
## Engine side
1. Copy the following files from the repository and place them in /usr/share/ovirt-engine/ui-plugins on the host running oVirt Engine:
  * hostusb-passthrough.json
  * hostusb-passthrough-resources/plugin.html
  * hostusb-passthrough-resources/hostusb-passthrough.html
2. Change hostnames and ports in the configuration files according to your environment
3. The UI part depends on [patternfly](https://github.com/patternfly), so download patternfly.min.js and patternfly.min.css and put them in the following places:
  * patternfly.min.js -> /usr/share/ovirt-engine/ui-plugins/hostusb-passthrough-resources/js/patternfly.min.js
  * patternfly.min.css -> /usr/share/ovirt-engine/ui-plugins/hostusb-passthrough-resources/css/patternfly.min.css

## Host side
1. Copy the agent script from the repository to every host:
  * agent/usb-passthrough.py
2. Run the script on every host (better in screen/tmux):
  * python usb-passthrough.py

# Known Issues
* Due to libvirt/vdsm's security policy, user should manully run "chmod o+w /dev/bus/usb/BUS/DEVICE" for the corresponding device on the hosts which would be passed through to allow the user qemu to access to the device
* Bypass vdsm, caution split-brain

# TODO
* Startup/stop service script for the agent?
