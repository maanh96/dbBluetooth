# Sync Bluetooth Key
Script to copy Bluetooth Key and MAC address of a device from Windows to Linux so that the device can work in both systems without re-paring.

I create this for personal use since [bt-dualboot](https://github.com/x2es/bt-dualboot) has not yet worked with my Bluetooth LE (Low Energy) devices. I try to keep it as simple as possible so for specific case you might want to check this [ArchWiki](https://wiki.archlinux.org/title/Bluetooth#Preparing_Bluetooth_5.1_Keys) page first.

## Using
1. Pair and connect the device in Linux FIRST
2. Pair and connect the device in Windows
3. Boot to Linux
4. Mount Windows partition
5. Install chntpw on Linux to read registry file
    ``` 
    sudo apt install chntpw 
    ```
6. Download `dbBluetooth.py` and `requirement.txt` and save it to a new folder
7. In this folder, create a virtual environment to install required packages
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
8. Still in the folder, run script with sudo privileges (to gain access to `/var/lib/bluetooth/`)
   ```
   sudo ./dbBluetooth.py
   ```
9.  Rebooting 
    
    (You can try restart bluetooth service first using `systemctl restart bluetooth` but in my case the device only works after rebooting)
    
## Credit
* [Bluetooth LE Dual Boot Connecting guide](https://gist.github.com/tVienonen/fad5cb68e6449f6c4804e276094516e3)
* [Dual boot pairing - ArchWiki](https://wiki.archlinux.org/title/Bluetooth#Preparing_Bluetooth_5.1_Keys)