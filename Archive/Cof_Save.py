#
# List of import modules
#
from netmiko import ConnectHandler
from netmiko import Netmiko
from easygui import passwordbox
from netmiko.ssh_exception import NetMikoTimeoutException
from netmiko.ssh_exception import AuthenticationException
import time
import tkinter as tk

#
# List of variables
#
iPfile = "ips.txt"

ConnectionTimeout = "Connection time outs.txt"
Authfail = "Authfailures.txt"
SSHFail = "Authfailures.txt"
Enderrors = "EOFerrors.txt"
RandomError = "UnknownError.txt"

devicelist = open(iPfile, 'r').read().split()
Timeouts = open(ConnectionTimeout, "a+")
Authfailure = open(Authfail, "a+")
SSHException = open(SSHFail, "a+")
EOFError = open(Enderrors, "a+")
UnknownError = open(RandomError, "a+")
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
# For loop,
#
for i in devicelist:
    print('Running Configuration Changes on ' + i)
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
    except AuthenticationException:
        print('\n' + 'Authentication Failure: ')
        Authfailure.write('\n')
        continue
    except NetMikoTimeoutException:
        print('\n' + 'Timeout to device: ')
        Timeouts.write('\n')
        continue
    except SSHException:
        print('\n' + 'SSH might not be enabled: ')
        SSHException.write('\n')
        continue
    except EOFError:
        print('\n' + 'End of attempting device: ')
        EOFError.write('\n')
        continue
    except UnknownError:
        print('\n' + 'Some other error: ')
        UnknownError.write('\n')
        continue
