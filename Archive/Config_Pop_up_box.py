# --------------------------------------
# Python program Cisco IOS rollback
# Author: Luke Thomas
# Date: 15 February 2020
# --------------------------------------
#
# List of import modules
#
import os
import sys
import easygui
import time
import tkinter.filedialog
from netmiko import ConnectHandler
from netmiko import Netmiko
from easygui import passwordbox, easygui, ccbox, codebox
from datetime import datetime

#
# Start script timer
#
startTime = datetime.now()
#
# List of variables
#
Hostfile = tkinter.filedialog.askopenfilename()
configfile = os.path.normcase("../configuration.txt")
Error_Log = "Error_Log.txt"
Error_MSG = "ERROR -  {0}: {1}: \n"
#
# List of variables to open files
#
devicelist = open(Hostfile, 'r').readlines()
configlist = open(configfile, 'r').readlines()
Error_Logs = open(Error_Log, "a+")
#
# Dictionary of items
#
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
#
#
if ccbox("Please select hostfile"):
    pass # continue
    Hostfile = tkinter.filedialog.askopenfilename()
else:
    sys.exit(0)  # exit the program


#
# Read list of configuration commands
#
#print(configlist)
#
if codebox("Please review the following configuration commands before continuing", "Show File Contents", configlist):
    pass  # user chose Continue
else:  # user chose Cancel
    sys.exit(0)
#
# Popup box referring to the list of hosts
#
if codebox("Please review the following list of hosts before continuing", "Show File Contents", devicelist):
    pass
else:
    sys.exit(0)
#
#
# ------------------------------------------------------------------------------------------------------
#
# Add a popup box here and refer to a config file with a list of commands (are you happy to run these commands yes/no?)
#
# ------------------------------------------------------------------------------------------------------
#
# Device configuration task
#
for i in devicelist:
    print('Deploying configuration script on ' + i)
    cisco_automation['host'] = i
    try:
        #
        # Error handling
        #
        net_connect = ConnectHandler(**cisco_automation)
        #
        # Configuration commands to push to the list of Host
        #
        config_commands = configlist
        output = net_connect.send_config_set(config_commands)
        print(output)
    except Exception as e:
        print(Error_MSG.format(i, e))
        Error_Logs.write(Error_MSG.format(i, e))
    continue
print('Total time taken to complete automation: ', datetime.now() - startTime)
quit()
