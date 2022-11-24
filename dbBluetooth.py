#!.venv/bin/python3
# for Bluetooth LE (Low Energy) device
# Source:
# https://gist.github.com/tVienonen/fad5cb68e6449f6c4804e276094516e3
# https://wiki.archlinux.org/title/Bluetooth#Preparing_Bluetooth_5.1_Keys


from glob import glob
from configparser import ConfigParser
import shutil
import subprocess
import re
from thefuzz import process

"""
Convert functions
"""


def convert_reg(info):
    type, value = info.split(':')
    if type == 'hex':
        return value.replace(',', '').upper()
    if type == 'hex(b)':
        result = value.split(',')
        result.reverse()
        return str(int(''.join(result), base=16))
    if type == 'dword':
        result = re.findall('..', value)
        return str(int(''.join(result), base=16))


def reg_to_mac(reg):
    result = re.findall('..', reg)
    return ':'.join(result).upper()


def mac_to_reg(mac):
    return mac.replace(':', '').lower()


"""
Find Windows mount directory
"""

# path to bluetooth registry file in mount Windows
system_path = 'Windows/System32/config/SYSTEM'
mounts = []
with open('/proc/mounts') as f:
    for line in f:
        if line.startswith('/dev/'):
            mounts += [line.split(' ')[1]]

for i in mounts:
    result = glob(i + '/' + system_path)
    if len(result) == 1:
        registry_file = i + '/' + system_path

if not registry_file:
    win_path = (
        'Cannot find Windows mount directory. Please enter manually: (eg: /mnt/Windows)')
    if win_path.endswith('/'):
        registry_file = win_path + system_path
    else:
        registry_file = win_path + '/' + system_path

if not glob(registry_file):
    print('Cannot find Windows mount directory.')
    raise SystemExit(0)

"""
Find BT devices connected with Windows
"""

# bluetooth registry devices
reg_device = r'ControlSet001\Services\BTHPORT\Parameters\Devices'

# exports given registry device as text
device_cmd = ['reged', '-x', registry_file,
              'PREFIX', reg_device, 'device.reg']
device_result = subprocess.run(device_cmd, capture_output=True, text=True)

with open('device.reg', 'r') as f:
    # remove first line of window reg to work with configparser
    device_text = ''.join(f.readlines()[1:])

win_config = ConfigParser()
win_config.optionxform = lambda option: option
win_config.read_string(device_text)

# get all connected device name and mac
win_devices = {}
for i in win_config.sections():
    try:
        device_name = bytes.fromhex(convert_reg(win_config[i]
                                                ['"Name"'])).decode('utf-8')
        device_mac = i.rsplit('\\', 1)[1]
        win_devices[device_name] = device_mac
    except:
        pass

"""
Find BT devices connected with Linux
"""

bt_dir = glob('/var/lib/bluetooth/**/info', recursive=True)
linux_config = ConfigParser()
linux_config.optionxform = lambda option: option
linux_devices = {}
for i in bt_dir:
    linux_config.read(i)
    device_name = linux_config['General']['Name']
    device_mac = i.rsplit('/', 2)[1]
    device_dir = i
    linux_devices[device_name] = [device_mac, device_dir]

if not linux_devices:
    print('Cannot find device connected with Linux. Please connect device first and run this script with sudo privileges.')
    raise SystemExit(0)

"""
Ask device to sync
"""

print('This is list of Bluetooth devices that connected to Linux:')
device_index = 0
list_device = {}
for i in list(linux_devices.keys()):
    device_index += 1
    list_device[device_index] = i
    print('{}. {}'.format(device_index, i))

device_name = list_device[int(
    input('Please choose a device to sync info (1-{}): '.format(device_index)))]
device_linux_mac, device_linux_dir = linux_devices[device_name]

if mac_to_reg(device_linux_mac) in list(win_devices.values()):
    device_win_mac = mac_to_reg(device_linux_mac)
    device_win_name = [
        k for k, v in win_devices.items() if v == device_win_mac][0]
else:
    # match device name in linux and win using thefuzz
    win_match = process.extractOne(device_name, list(win_devices.values()))

    if win_match[1] < 90:
        print('Cannot find match device in Windows. Please connect {} device with Windows.'.format(
            device_name))
        raise SystemExit(0)
    else:
        device_win_name = win_match[0]
        device_win_mac = win_devices[device_win_name]

print('\nDevice name: {} ({})\nWindow MAC address: {}\nLinux MAC address: {}\n'.format(
    device_name, device_win_name, device_win_mac, device_linux_mac))

"""
Get info from Windows reg
"""

# bluetooth registry keys
reg_key = r'ControlSet001\Services\BTHPORT\Parameters\Keys'

# exports given registry key as text
key_cmd = ['reged', '-x', registry_file, 'PREFIX', reg_key, 'key.reg']
key_result = subprocess.run(key_cmd, capture_output=True, text=True)

# open and get info from Windows BT Key reg
with open('key.reg', 'r') as f:
    key_text = ''.join(f.readlines()[1:])

key_config = ConfigParser()
key_config.optionxform = lambda option: option
key_config.read_string(key_text)

# open and get info file from Linux
info_file = device_linux_dir
info_config = ConfigParser()
info_config.optionxform = lambda option: option
info_config.read(info_file)

if not key_config.has_section(key_config.sections()[1] + '\\' + device_win_mac):
    win_device_info = key_config[key_config.sections()[1]]
else:
    win_device_info = key_config[key_config.sections()[
        1] + '\\' + device_win_mac]

reg_dicts = {
    '"' + device_win_mac + '"': ['LinkKey', 'Key'],
    '"LTK"': ['LongTermKey', 'Key'],
    '"ERand"': ['LongTermKey', 'Rand'],
    '"EDIV"': ['LongTermKey', 'EDiv'],
    '"IRK"': ['IdentityResolvingKey', 'Key'],
    '"CSRK"': ['LocalSignatureKey', 'Key']
}

info_need_sync = 0

for i in reg_dicts.keys():
    if i in win_device_info.keys():
        win_info = convert_reg(win_device_info[i])
        linux_info = info_config[reg_dicts[i][0]][reg_dicts[i][1]]
        if win_info == linux_info:
            print('Already synced:\n[{0}]\n{1}={2}\n'.format(
                reg_dicts[i][0], reg_dicts[i][1], linux_info))
        else:
            info_need_sync += 1
            info_config[reg_dicts[i][0]][reg_dicts[i][1]] = win_info
            print('Need to sync:\n[{0}]\nFrom {1}={2}\nTo {1}={3}\n'.format(reg_dicts[i][0], reg_dicts[i][1], linux_info,
                  win_info))

if info_need_sync != 0:
    action = input(
        'Choose an action (a/b):\n(a) Copy new info file to current directory to recheck\n(b) Create a backup of current info file & REPLACE it with new info.\n')
    if action == 'b':
        # create backup before write out file
        backup_file = device_name + ' info_backup'
        k = 0
        while k < 5 and glob(backup_file):
            k += 1
            backup_file = device_name + 'info_backup' + str(k)
        shutil.copy2(info_file, backup_file)
        with open(info_file, 'w') as f:
            info_config.write(f, False)
        if reg_to_mac(device_win_mac) != device_linux_mac:
            old_dir = device_linux_dir.rsplit('/', 1)[0]
            new_dir = old_dir.rsplit(
                '/', 1)[0] + '/' + reg_to_mac(device_win_mac)
            shutil.move(old_dir, new_dir)
        print(
            '\nSync info successfully. Backup file is created in the current directory.')
    else:
        with open(device_name + ' info', 'w') as f:
            info_config.write(f, False)
            print('\nInfo file is created in the current directory.')
else:
    print('All synced. No information need to change.')
