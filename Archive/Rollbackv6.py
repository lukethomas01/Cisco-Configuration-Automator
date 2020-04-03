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
#from netmiko.ssh_exception import NetMikoTimeoutException
#from netmiko.ssh_exception import AuthenticationException
import time
#
# List of variables
#
iPfile = "ips.txt"
#ConnectionTimeout = "TimeoutsErrors.txt"
#Authfail = "Authfailures.txt"
#SSHFail = "SSHFailures.txt"
#Enderrors = "EOFerrors.txt"
#RandomError = "UnknownErrors.txt"
Error_Log = "Error_Log.txt"
Error_MSG = "ERROR -  {0}: {1}: \n"
#
# List of variables to open files
#
devicelist = open(iPfile, 'r').read().split()
#Timeouts = open(ConnectionTimeout, "a+")
Error_Logs = open(Error_Log, "a+")
#Authfailure = open(Authfail, "a+")
#SSHException = open(SSHFail, "a+")
#EOFError = open(Enderrors, "a+")
#UnknownError = open(RandomError, "a+")
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
# Read list of ip devices
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
                           'action 0.2 cli command "configure replace flash:Automation_Rollback.conf force"',
                           'interface gig 0/0/0',
                           'shutdown']
        output = net_connect.send_config_set(config_commands)
        print(output)
    except Exception as e:
        print(Error_MSG.format(i, e))
        Error_Logs.write(Error_MSG.format(i, e))