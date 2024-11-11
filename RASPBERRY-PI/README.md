sudo apt-get update
sudo apt-get install gpsd gpsd-clients

sudo apt update
sudo apt install -y python3-smbus i2c-tools
i2cdetect -y 1


Open a terminal session on the Raspberry Pi.

The first thing we will do is backup the file cmdline.txt before we edit it.

sudo cp /boot/cmdline.txt /boot/cmdline_backup.txt and press Enter.

The we need to edit cmdlint.txt and remove the serial interface.

Type in sudo nano /boot/cmdline.txt and press Enter.

Delete console=ttyAMA0,115200 and save the file by pressing Ctrl X, Y, and Enter.

Now type in sudo nano /etc/inittab and press enter.

Find ttyAMA0 by pressing Ctrl W and typing ttyAMA0 on the search line.

When it finds that line, press home, insert a # symbol to comment out that line, and Ctrl X, Y, Enter to save.

Type sudo reboot and press Enter to restart the Pi.



sudo nano /boot/config.txt
At the end of the file add the follwing lines:

dtparam=spi=on
dtoverlay=pi3-disable-bt
core_freq=250
enable_uart=1
force_turbo=1

sudo cp /boot/cmdline.txt /boot/cmdline_backup.txt
sudo nano /boot/cmdline.txt

Replace the content with the follwing line (delete everything in it and write down the following content):

dwc_otg.lpm_enable=0 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait quiet splash plymouth.ignore-serial-consoles
sudo reboot

sudo cat /dev/ttyAMA0

DISABLE - https://sparklers-the-makers.github.io/blog/robotics/use-neo-6m-module-with-raspberry-pi/


