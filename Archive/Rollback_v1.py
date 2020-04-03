import tkinter as tk
from tkinter import messagebox
from netmiko import ConnectHandler
# from netmiko import Netmiko (not working)
from easygui import passwordbox
# from datetime import datetime (not working)
#
iPfile = "ips.txt"
devicelist = open(iPfile, 'r').read().split()

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
    net_connect = ConnectHandler(**cisco_automation)
    config_commands = ['do copy running-config flash:Automation_Rollback.conf']
                    #'event manager applet Automation_Rollback',
                    #'event timer watchdog time 60',
                    #'action 0.1 cli command "enable"',
                    #'action 0.2 cli command "configure replace flash:Automation_Rollback.conf"',]
    output = net_connect.send_config_set(config_commands)
    print(output)

# Command confirmation?
# Error Handling

