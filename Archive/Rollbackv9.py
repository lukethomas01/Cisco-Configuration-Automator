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
Hostfile = "hosts.txt"
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
# For loop, copy rollback configuration file
#
for i in devicelist:
    print('Creating a backup file on ' + i)
    cisco_automation['host'] = i
    #
    # Error handling
    #
    try:
        net_connect = Netmiko(**cisco_automation)
        enable_commands = "copy running-config flash:Automation_Rollback.conf"
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
#
# Set delay before next for loop
#
time.sleep(10)
#
# Set EEM Rollback Script
#
for i in devicelist:
    print('Deploying timed EEM rollback script on  ' + i)
    cisco_automation['host'] = i
    try:
        #
        # Error handling
        #
        net_connect = ConnectHandler(**cisco_automation)
        #
        # Commands to push on box EEM watchdog script timer is in seconds
        #
        config_commands = ['event manager applet Automation_Rollback',
                           'event timer watchdog time 600',
                           'action 0.1 cli command "enable"',
                           'action 0.2 cli command "configure replace flash:Automation_Rollback.conf force"']
        output = net_connect.send_config_set(config_commands)
        print(output)
    except Exception as e:
        print(Error_MSG.format(i, e))
        Error_Logs.write(Error_MSG.format(i, e))
    continue
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
#
# Delete EEM Rollback Script
#
for i in devicelist:
    print('Removing timed EEM script on  ' + i)
    cisco_automation['host'] = i
    try:
        #
        # Error handling
        #
        net_connect = ConnectHandler(**cisco_automation)
        #
        # Commands to delete on box EEM watchdog script timer is in seconds
        #
        config_commands = 'no event manager applet Automation_Rollback'
        output = net_connect.send_config_set(config_commands)
        print(output)
    except Exception as e:
        print(Error_MSG.format(i, e))
        Error_Logs.write(Error_MSG.format(i, e))
    continue
#
# Write Memory
#
for i in devicelist:
    print('Saving configuration to ' + i)
    cisco_automation['host'] = i
    #
    # Error handling
    #
    try:
        net_connect = Netmiko(**cisco_automation)
        enable_commands = "copy run start"
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
print('Total time taken to complete automation: ', datetime.now() - startTime)
