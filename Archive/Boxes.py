#https://datatofish.com/message-box-python/
import tkinter as tk
from tkinter import messagebox

root = tk.Tk()  # create window

canvas1 = tk.Canvas(root, width=150, height=150)
canvas1.pack()


def ExitApplication():
    MsgBox = tk.messagebox.askquestion('Apply Configuration?', 'Are you sure you want to apply the configuration?',
                                       icon='warning')
    if MsgBox == 'yes':
        root.destroy()
    else:
        tk.messagebox.showinfo('Return', 'You will now return to the application screen')


button1 = tk.Button(root, text='Exit Application', command=ExitApplication)
canvas1.create_window(75, 75, window=button1)

root.mainloop()