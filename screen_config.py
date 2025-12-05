
menufont = "Helvetica 24"
cascademenufont = "Helvetica 28"
buttonfont = "Helvetica 18"
smallfont = "Helvetica 16"
labelfont = "Helvetica 18"
titlefont = "Helvetica 22"
tablefont = "Helvetica 12"

def screen_config(parent):
    parent.title('Main')
    parent.geometry('800x480')
    parent.config(bg='#ffffff')
    parent.attributes('-fullscreen', True)

def widget_config(parent):
    parent.title('Widget')
    parent.geometry('800x480')
    parent.config(bg='#ffffff')
    parent.attributes('-fullscreen', True)
   
def kill_previous(prevscreen):
    for screen in prevscreen:
        screen.destroy()
    