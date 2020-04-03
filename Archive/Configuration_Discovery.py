# ----------------------------------------------------------------------------------------------------------------
# Python program Cisco IOS configuration changes
# Author: Luke Thomas
# Date: 15 February 2020
# ----------------------------------------------------------------------------------------------------------------
#
# List of import modules
#
import os
import sys
import tkinter
import tkinter.filedialog
from netmiko import ConnectHandler
from netmiko import Netmiko
from easygui import passwordbox, codebox
from datetime import datetime
import time
#
# Start script timer
#
startTime = datetime.now()
#
# List of variables
#
# Hostfile = "hosts.txt"
Hostfile = tkinter.filedialog.askopenfilename()
configfile = tkinter.filedialog.askopenfilename()
Error_Log = "Error_Log.txt"
Error_MSG = "ERROR -  {0}: {1}: \n"
Device_List = "Show_Configuration.txt"
Device_MSG = "{0}\n"
d_list = []
#
# List of variables to open files
#
devicelist = open(Hostfile, 'r').read().split()
configlist = open(configfile, 'r').readlines()
Error_Logs = open(Error_Log, "a+")
Device_Lists = open(Device_List, "w+")
#
# Dictionary of items
#
cisco_automation = {
    'device_type': 'cisco_ios',
    'host': '',
    'username': passwordbox("Enter Username:"),
    'password': passwordbox("Enter Password:"),
    'port': 22,
    'secret': passwordbox("Enter Enable Password:"),
}
#
# Read list of devices
#
print(devicelist)
#
# Popup box referring to the config file with a list of commands
#
if codebox("Please review the following configuration commands before continuing", "Show File Contents", configlist):
    pass
else:
    sys.exit(0)
#
# Popup box referring to the list of hosts
#
if codebox("Please review the following list of hosts before continuing", "Show File Contents", devicelist):
    pass
else:
    sys.exit(0)
#
# For loop, show running configuration
#
for i in devicelist:
    print('Running Configuration checks on ' + i)
    cisco_automation['host'] = i
    #
    # Error handling
    #
    try:
        net_connect = Netmiko(**cisco_automation)
        enable_commands = "show run"
        output = net_connect.send_command_timing(enable_commands)
        print(output)
        for cl in configlist:
            if cl not in output:
                print(Device_MSG.format(i))
                Device_Lists.write(Device_MSG.format(i))
                d_list.append(i)
                break
        net_connect.disconnect()
        print()
    except Exception as e:
        print(Error_MSG.format(i, e))
        Error_Logs.write(Error_MSG.format(i, e))
        continue
print('Total time taken to complete automation: ', datetime.now() - startTime)
if codebox("Please review the following list of hosts before continuing", "Show File Contents", d_list):
    pass
else:
    sys.exit(0)
print(d_list)
print('\nAutomation complete...')
