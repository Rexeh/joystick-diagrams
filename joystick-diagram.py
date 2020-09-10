import adaptors.gremlin as gremlin
import config
import functions.helper as helper
import tkinter as tk
import webbrowser
from PIL import ImageTk,Image 
from tkinter.font import Font
from tkinter import Frame
from tkinter.filedialog import askopenfilename
import subprocess
from tkinter import ttk

root = tk.Tk()
text = tk.Text(root)
root.wm_minsize(800,600)
root.title("Joystick Visualiser - github.com/Rexeh/joystick-diagrams")
root.iconbitmap('./logo.ico')
root.config(bg="white")
app_background = "white"
# Font Setting
tabFont = Font(family="Helvetica", size=12, weight="bold")
largeFont = Font(family="Helvetica", size=12, weight="bold")
buttonFont = Font(family="Helvetica", size=8, weight="bold")

s = ttk.Style()
s.configure('TNotebook.Tab', font=largeFont,background="white")
s.configure('TNotebook', font=largeFont,background="white")
s.configure('TFrame', font=largeFont,background="white")

# Image Inits
githubIcon = Image.open('./images/github.png')
githubIcon = githubIcon.resize((20,20), Image.ANTIALIAS)

bugIcon = Image.open('./images/bug.png')
bugIcon = bugIcon.resize((20,20), Image.ANTIALIAS)

photo = ImageTk.PhotoImage(githubIcon)
bug = ImageTk.PhotoImage(bugIcon)

# Functions

def exportGremlin():
    parsedConfig = gremlin.Gremlin(selectedFile.cget('text'))
    
    devices = parsedConfig.createDictionary()

    for joystick in devices:
        for mode in devices[joystick]:
            helper.exportDevice(devices, joystick, mode)

def clicked():
    selected_item_label.configure(text=nlist.get("active"))

def openLink():
    webbrowser.open('https://github.com/Rexeh/joystick-diagrams')

def openBugs():
    webbrowser.open('https://github.com/Rexeh/joystick-diagrams/issues')

def chooseFile():
    file = askopenfilename(
                title="Select Joystick Gremlin .XML config",
                filetypes=[("Gremlin Config Files" , '*.xml')]
                )
    global selectedFile
    selectedFile = tk.Label(jg_tab, text=file,font=buttonFont)
    selectedFile.grid(row=1, column=2)


def openDiagramsDirectory():
    subprocess.Popen('explorer "./diagrams"') ## DOESNT WORK YET


tabControl = ttk.Notebook(root, padding=15)

# Add Tabs
jg_tab = ttk.Frame(tabControl)
dcs_tab = ttk.Frame(tabControl)
settings_tab = ttk.Frame(tabControl)

tabControl.add(jg_tab, text='Joystick Gremlin', padding=5)
tabControl.add(dcs_tab, text='DCS World', padding=5)
tabControl.add(settings_tab, text='Settings', padding=5)

topFrame = Frame(root,bg="white", bd=1)
bottomFrame = Frame(root, bg="white", bd=1)
separator = Frame(height=2, bd=1, relief='sunken')

topFrame.pack()
separator.pack()
tabControl.pack(expand=1, fill="both")
separator.pack()
bottomFrame.pack()

#Remove DCS panel for now
tabControl.hide(1)

version = tk.Label(bottomFrame, text="Version: ALPHA",font=largeFont, anchor="e", compound = "left", state="disabled", bg=app_background)
info = tk.Label(bottomFrame, text="This is an early version, please report bugs and I will fix them!", anchor="w" ,font=largeFont,compound = "left", state="disabled", bg="white")
gremlinLogo = tk.Button(topFrame, text="Support us on GitHub", image=photo, bg="white",anchor="e",padx=(15), font=buttonFont,command=openLink,compound = "left", width=160)
bugLogo = tk.Button(topFrame, text="Got a Bug? Feature?", image=bug,bg="white",anchor="e", padx=(15), font=buttonFont, command=openBugs,compound = "left", width=160)

step_1_info = tk.Label(jg_tab, text="Step 1: Select your Gremlin .XML File",font=largeFont, compound = "left", state="disabled",bg="white", pady=20)
chooseFile = tk.Button(jg_tab, text="Choose Gremlin File",font=buttonFont, command=chooseFile,bg="white")

## LISTBOX TEST
nlist = tk.Listbox(dcs_tab, selectmode='MULTIPLE', selectbackground="white", font=buttonFont)

items = [1,2,3,4,5]
for i in items:
    nlist.insert(i, ("File_name_{}.xml").format(i))

selected_item_button = tk.Button(dcs_tab, text="What is it?",bg="white",anchor="w", padx=(15), font=buttonFont, command=clicked,compound = "left")
selected_item_label = tk.Label(dcs_tab, text="Selected file",font=largeFont, state="disabled",bg="white")

### END
step_2_info = tk.Label(jg_tab, text="Step 2: Run Export",font=largeFont, state="disabled",bg="white",compound = "left",pady=20)
step_2_button = tk.Button(jg_tab, text="Export profiles",bg="white",anchor="w", padx=(15), font=buttonFont, command=exportGremlin,compound = "left")
step_2_secondary = tk.Label(jg_tab, text="This will export all found Joystick Gremlin profiles for all devices.",compound = "left",font=buttonFont,bg="white")

step_3_info = tk.Label(jg_tab, text="Step 3: View Diagrams",font=largeFont, compound = "left", state="disabled", bg="white", pady=20)
step_3_button = tk.Button(jg_tab, text="Open diagrams folder",bg="white",anchor="w", padx=(15), font=buttonFont, command=openDiagramsDirectory,compound = "left")

nlist.pack()
selected_item_button.pack()
selected_item_label.pack()


gremlinLogo.grid(row=0, column=3)
bugLogo.grid(row=0, column=2)

step_1_info.grid(row=1, column=0)
chooseFile.grid(row=1, column=1)

step_2_info.grid(row=2, column=0)
step_2_button.grid(row=2, column=1)
step_2_secondary.grid(row=3, column=0)

step_3_info.grid(row=4, column=0)
step_3_button.grid(row=4, column=1)

version.grid(row=5,column=3)
info.grid(row=5,column=1)

root.mainloop()

print(helper.getVersion())

if config.gremlinconfig == "":
    print("Please edit config.cfg to specify your Joystick Gremlin config .XML file location")
    input("Press enter to exit")
else:
    pass
    #gremlin = gremlin.Gremlin(config.gremlinconfig)

    #devices = gremlin.createDictionary()

    #for joystick in devices:
    #    for mode in devices[joystick]:
    #        helper.exportDevice(devices, joystick, mode)

print("----------------FINISHED-------------------")
print("View your outputted files in /diagrams and open them in a web browser to print.")
print("-------------------------------------------")

input("Press enter to exit")
