from tkinter import *
import tkinter as tk
from tkinter import ttk
import sys
import os

def poweroff():
    shutdown = tk.messagebox.askquestion("Confirm","Do you want to shutdown?")
    if shutdown == 'no':print('no')
    else:os.system("sudo shutdown -h now")

def restart():
    restart = tk.messagebox.askquestion("Confirm","Do you want to restart?")
    if restart == 'no':print('no')
    else:os.system("sudo shutdown -r now")

