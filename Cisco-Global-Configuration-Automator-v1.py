# ----------------------------------------------------- #
# Python program - Cisco Global Configuration Automator #
# Author: Luke Thomas                                   #
# Date: 15 February 2020                                #
# Copyright (C) 2020                                    #
# Licensed under the GNU General Public License v3.0    #
# ----------------------------------------------------- #
#
# List of import modules
#
import sys
import tkinter.filedialog
from netmiko import ConnectHandler
from netmiko import Netmiko
from easygui import passwordbox, codebox
from datetime import datetime
#
# Start script timer
#
startTime = datetime.now()
#
# List of variables
#
Hostfile = tkinter.filedialog.askopenfilename(title="Please Select Host File", filetypes=(("text files", "*.txt"), ("csv files", "*.csv"), ("all files", "*.*")))
configfile = tkinter.filedialog.askopenfilename(title="Please Select Configuration File", filetypes=(("text files", "*.txt"), ("config files", "*.conf"), ("all files", "*.*")))
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
# Popup box referring to the list of hosts
#
if codebox("Please review the following list of hosts before continuing.\nClick OK to continue or Cancel to Quit", "Contents of host file", "\n".join(devicelist)):
    pass
else:
    sys.exit(0)
#
# Popup box referring to the config file with a list of commands
#
if codebox("Please review the following configuration commands before continuing.\nClick OK to continue or Cancel to Quit", "Contents of configuration file", configlist):
    pass
else:
    sys.exit(0)
#
# For loop, show running configuration
#
for i in devicelist:
    print('Checking for configuration compliance on ' + i)
    cisco_automation['host'] = i
    #
    # Error handling
    #
    try:
        net_connect = Netmiko(**cisco_automation)
        enable_commands = "show run"
        output = net_connect.send_command(enable_commands)
        for cl in configlist:
            if cl not in output:
                Device_Lists.write(Device_MSG.format(i))
                d_list.append(i)
                break
        net_connect.disconnect()
    except Exception as e:
        Error_Logs.write(Error_MSG.format(i, e))
        continue
if codebox("Please review the following list of non compliant hosts before continuing.\n\nClick OK to continue change work on these hosts or click Cancel to Quit", "Non Compliant Host List", "\n".join(d_list)):
    pass
else:
    sys.exit(0)
#
# For loop, copy rollback configuration file
#
#########################################################################
# To Do - Create a single loop for all tasks.
#########################################################################
for dl in d_list:
    print('Creating a backup file on ' + dl)
    cisco_automation['host'] = dl
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
            print("Overwriting existing rollback file...")
            output += net_connect.send_command_timing("\n")
#        print()
        net_connect.disconnect()
#        print()
    except Exception as e:
        Error_Logs.write(Error_MSG.format(dl, e))
    continue

#
# Set EEM Rollback Script
#
for dl in d_list:
    print('Deploying a timed EEM rollback script on  ' + dl)
    cisco_automation['host'] = dl
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
        Error_Logs.write(Error_MSG.format(dl, e))
    continue
#
# Device configuration task
#
for dl in d_list:
    print('Deploying configuration changes on ' + dl)
    cisco_automation['host'] = dl
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
        Error_Logs.write(Error_MSG.format(dl, e))
    continue
#
# Delete EEM Rollback Script
#
for dl in d_list:
    print('Removing EEM script on  ' + dl)
    cisco_automation['host'] = dl
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
    except Exception as e:
        Error_Logs.write(Error_MSG.format(dl, e))
    continue
#
# Write Memory
#
########################
# delete rollback.conf #
########################
for dl in d_list:
    print('Saving configuration to ' + dl)
    cisco_automation['host'] = dl
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
        net_connect.disconnect()
    except Exception as e:
        Error_Logs.write(Error_MSG.format(dl, e))
        continue
print('Total time taken to complete automation: ', datetime.now() - startTime)
print('\nScript complete...')
