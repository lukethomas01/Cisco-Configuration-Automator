# --------------------------------------
# Python program Cisco_IOS rollback
# Author: Luke Thomas
# Date: 09 February 2020
# --------------------------------------
#
# List of import modules
#
from netmiko import ConnectHandler
from netmiko import Netmiko
from easygui import passwordbox
import time
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
    print('Deploying timed EEM script on  ' + i)
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
                           'event timer watchdog time 50',
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
        config_commands = ['interface gig 0',
                           'shutdown']
#                          'interface gig 0/0/0',
#                           'shutdown']
        output = net_connect.send_config_set(config_commands)
        print(output)
    except Exception as e:
        print(Error_MSG.format(i, e))
        Error_Logs.write(Error_MSG.format(i, e))
    continue