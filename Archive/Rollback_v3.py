import tkinter as tk
from tkinter import messagebox
from netmiko import ConnectHandler
from easygui import passwordbox
from netmiko.ssh_exception import NetMikoTimeoutException
from netmiko.ssh_exception import AuthenticationException

import time
#
iPfile = "ips.txt"
devicelist = open(iPfile, 'r').read().split()
Timeouts = open("Connection time outs.txt", "a")
Authfailure = open("Auth failures.txt", "a")
SSHException = ("SSH Failure.txt", 'a')
EOFError = ("EOFerrors.txt", 'a')
UnknownError = ("UnknownError.txt", 'a')

#Dictionary of items
cisco_automation = {
    'device_type': 'cisco_ios',
    'host': '',
    'username': passwordbox("Enter Username:"),
    'password': passwordbox("Enter Password:"),
    'port': 22,
    'secret': passwordbox("Enter Enable Password:"),
}

#Read list of devices

print(devicelist)

# Begin Loop of items in device list
#import tkinter as tk
from tkinter import messagebox

#root = tk.Tk()  # create window

#canvas1 = tk.Canvas(root, width=150, height=150)
#canvas1.pack()


#def ExitApplication():
#    MsgBox = tk.messagebox.askquestion('Apply Configuration?', 'Are you sure you want to apply the configuration?',
#                                      icon='warning')
#   if MsgBox == 'yes':
#       root.destroy()
 #   else:
#      tk.messagebox.showinfo('Return', 'You will now return to the application screen')
#
#
#button1 = tk.Button(root, text='Exit Application', command=ExitApplication)
#canvas1.create_window(75, 75, window=button1)
#
#root.mainloop()

for i in devicelist:
# Help with error finding
    print('Running Configuration Changes on ' + i)
    cisco_automation['host'] = i
    try:
        net_connect = ConnectHandler(**cisco_automation)
    #    net_connect.enable()
    #    command_ConfSave = "copy running-config flash:Automation_Rollback.conf \n\n\n"
    #    result = net_connect.send_command_expect(command_ConfSave)

        config_commands = ['event manager applet Automation_Rollback',
                        'event timer watchdog time 20',
                        'action 0.1 cli command "enable"',
                        'action 0.2 cli command "configure replace flash:Automation_Rollback.conf force"',
                        'interface gig 0/0/0',
                        'shutdown']

        output = net_connect.send_config_set(config_commands)
        print(output)
    except (AuthenticationException):
        print ('Authentication Failure: ')
        Authfailure.write('\n')
        continue
    except (NetMikoTimeoutException):
        print ('\n' + 'Timeout to device: ')
        Timeouts.write('\n')
        continue
    except (SSHException):
        print ('SSH might not be enabled: ')
        SSHException.write('\n')
        continue
    except (EOFError):
        print ('\n' + 'End of attempting device: ')
        EOFError.write('\n')
        continue
    except unknown_error:
        print ('Some other error: ' + str(unknown_error))
        continue

#time.sleep(30)

#for i in devicelist:
# Help with error finding
#    print('Running Configuration Changes on ' + i)
#    cisco_automation['host'] = i
#   net_connect = ConnectHandler(**cisco_automation)
#    net_connect.enable()
#    command_ConfSave = "copy running-config flash:Automation_Rollback.conf \n\n\n"
#    result = net_connect.send_command_expect(command_ConfSave)
#   config_commands = ['no event manager applet Automation_Rollback']
#   output = net_connect.send_config_set(config_commands)
#   print(output)
# Command confirmation?
# Error Handling