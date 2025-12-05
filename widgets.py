from tkinter import *
from tkinter import messagebox
import tkinter as tk
from tkinter import ttk
import results



def drawKeyboard(parent):
    keyboardFrame = tk.Frame(parent, bg = '#ffffff')
    keyboardFrame.pack(side=BOTTOM)
    caps = 1
    keys = [
        [ ("Alpha Keys"),
          [('0', '1', '2', '3', '4', '5', '6', '7', '8', '9','Caps'),
           ('q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p','Space'),
        ('a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l','@',':','Bksp'),
        ('z', 'x', 'c', 'v', 'b', 'n', 'm','/','_', '-','.')
          ]
        ]]
    
    def makeframe(caps):
        for widget in keyboardFrame.winfo_children():
            widget.destroy()
        for key_section in keys:
            sect_vals = key_section[1]
            sect_frame = tk.Frame(keyboardFrame)
            sect_frame.pack(side = 'left', expand = 'yes', fill = 'both', padx = 10, pady = 10, ipadx = 10, ipady = 10)
            for key_group in sect_vals:
                group_frame = tk.Frame(sect_frame)
                group_frame.pack(side = 'top', expand = 'yes', fill = 'both')
                for key in key_group:
                    if (caps%2)==1: 
                        key = key.capitalize() 
                    if len(key) <= 1: key_button = ttk.Button(group_frame, text = key, width = 6, takefocus=False)
                    else:key_button = ttk.Button(group_frame, text = key.center(5, ' '), takefocus=False)
                    key_button['command'] = lambda q=key: key_command(q, caps)
                    key_button.pack(side = 'left', fill = 'both', expand = 'yes')
    makeframe(caps)                
    def key_command(event, caps):
        entry = parent.focus_get()
        try: position = entry.index(INSERT)
        except: print('no focus defined')
        if event == 'Bksp': entry.delete(position-1)
        elif event == 'Space': entry.insert(position, " ")
        elif event == 'Caps': 
            caps = caps+1
            makeframe(caps)
        else: entry.insert(position, event)
        
def error(string):
    try:
        messagebox.showinfo(title=None, message=string)
        results.usesummary(string)
    except Exception as e:
        print(e)
        messagebox.showinfo(title=None, message=str(e))
        results.usesummary(str(e))
    


def askquestion(string, func, para):
     response = messagebox.askquestion(title=None, message=string)
     if response == "no": print('')
     else:
         if para =='':func()
         else:func(para)
         
def showinfo(title, message):
    messagebox.showinfo(title=title, message=str(message))
    results.usesummary(f"Info:{message}")