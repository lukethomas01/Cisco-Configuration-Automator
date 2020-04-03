# --------------------------------------
# Python program Cisco IOS rollback
# Author: Luke Thomas
# Date: 15 February 2020
# --------------------------------------
#
# List of import modules
#
from netmiko import ConnectHandler
from netmiko import Netmiko
from easygui import passwordbox
from datetime import datetime
import time

#
# Start script timer
#
startTime = datetime.now()
#
# List of variables
#
Hostfile = "hosts.txt"
Error_Log = "Error_Log.txt"
Error_MSG = "ERROR -  {0}: {1}: \n"
#
# List of variables to open files
#
devicelist = open(Hostfile, 'r').read().split()
Error_Logs = open(Error_Log, "a+")
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
# For loop, copy rollback configuration file
#
for i in devicelist:
    print('Running show commands on ' + i)
    cisco_automation['host'] = i
    #
    # Error handling
    #
    try:
        net_connect = Netmiko(**cisco_automation)
        enable_commands = "show run | include ntp"
        output = net_connect.send_command_timing(enable_commands)
        if 'Destination filename' in output:
            output += net_connect.send_command_timing("\n")
        if 'over write' in output:
            output += net_connect.send_command_timing("\n")
        print(output)
        print(net_connect.find_prompt())
        net_connect.disconnect()
        print()
    except Exception as e:
        print(Error_MSG.format(i, e))
        Error_Logs.write(Error_MSG.format(i, e))
        continue
