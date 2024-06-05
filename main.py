import tkinter
import os
import re
import json
import customtkinter
from tkinter import *
from tkinter import messagebox, filedialog
from PIL import ImageTk, Image
from ncclient import manager
from xml.dom.minidom import parseString
from ncclient.xml_ import to_ele
from enum import Enum
import datetime

def get_current_time():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

class CommandType(Enum):
    FACTORY_RESET = 0
    REBOOT = 1
    TIME_SET = 2
    DEFAULT = 3

APP_TITLE="Simple NETCONF Client"
customtkinter.set_appearance_mode("System") 
customtkinter.set_default_color_theme("blue")

#FUNCTION TO GET FULL FILE PATH
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class ConfigManager:
    def __init__(self, filename='.netconf_config.json'):
        self.filename = filename
        self.filepath = self._get_file()
        self.cfg = {
            'addr': '',
            'port': 830,
            'user': 'admin',
            'pass': ''
        }
        self.load()

    def _get_file(self):
        home_dir = os.path.expanduser('~')
        return os.path.join(home_dir, self.filename)

    def save(self):
        with open(self.filepath, 'w') as file:
            json.dump(self.cfg, file)

    def load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as file:
                self.cfg = json.load(file)

class App(customtkinter.CTk):
    def __init__(self):
        self.cfg_mgr = ConfigManager()
        self.cfg = self.cfg_mgr.cfg
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(f"{1100}x{580}")

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)


        menubar = Menu(self)
        self.config(menu=menubar)

        appearance_menu = Menu(menubar)
        file_menu = Menu(menubar)    

        appearance_submenu = Menu(appearance_menu)
        appearance_submenu.add_command(label="Light", command = lambda: self.change_appearance_mode_event("Light"))
        appearance_submenu.add_command(label="Dark", command = lambda: self.change_appearance_mode_event("Dark"))
        appearance_submenu.add_command(label="System", command = lambda: self.change_appearance_mode_event("System"))
        appearance_menu.add_cascade(label='Appearance Mode', menu=appearance_submenu, underline=0)

        zoom_submenu = Menu(appearance_menu)
        zoom_submenu.add_command(label="80%", command =  lambda: self.change_scaling_event("80%"))
        zoom_submenu.add_command(label="90%", command = lambda: self.change_scaling_event("90%"))
        zoom_submenu.add_command(label="100%", command = lambda: self.change_scaling_event("100%"))
        zoom_submenu.add_command(label="110%", command = lambda: self.change_scaling_event("110%"))
        zoom_submenu.add_command(label="120%", command = lambda: self.change_scaling_event("120%"))

        appearance_menu.add_cascade(label='Zoom Level', menu=zoom_submenu, underline=0)
        appearance_menu.add_separator()

        file_menu.add_command(label="Import XML", underline=0, command=self.import_xml_file)
        file_menu.add_separator()
        file_menu.add_command(label="Export XML", underline=0, command=self.export_xml_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", underline=0, command=self.exit_app_func)
        file_menu.add_separator()

        menubar.add_cascade(label="File", underline=0, menu=file_menu)
        menubar.add_cascade(label="Appearance", underline=0, menu=appearance_menu)


        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=8, sticky="nsew")
        
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="NETCONF Client", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.factory_reset_button = customtkinter.CTkButton(self.sidebar_frame, command=self.factory_reset_func, text="Factory Reset")
        self.factory_reset_button.grid(row=1, column=0, padx=20, pady=10)
        
        self.reboot_button = customtkinter.CTkButton(self.sidebar_frame, command=self.reboot_func, text="Reboot")
        self.reboot_button.grid(row=2, column=0, padx=20, pady=10)
        
        self.time_set_button = customtkinter.CTkButton(self.sidebar_frame, command=self.time_set_func, text="Set System Time")
        self.time_set_button.grid(row=3, column=0, padx=20, pady=10)

        self.profinet_label = customtkinter.CTkLabel(self.sidebar_frame, text="Profinet Status:", anchor="w")
        self.profinet_label.grid(row=4, column=0, padx=20, pady=(30, 0))
        self.enable_profinet_button = customtkinter.CTkOptionMenu(self.sidebar_frame, command=self.profinet_status_func, values=["Enable","Disable"])
        self.enable_profinet_button.grid(row=5, column=0, padx=20, pady=0)

        self.getconfiguration_label = customtkinter.CTkLabel(self.sidebar_frame, text="Get configuration", anchor="w")
        self.getconfiguration_label.grid(row=6, column=0, padx=20, pady=(30, 0))
        self.getconfiguraiton_button = customtkinter.CTkOptionMenu(self.sidebar_frame, command=self.getconfiguration_func, values=["Running","Startup"])
        self.getconfiguraiton_button.grid(row=7, column=0, padx=20, pady=0)

        self.execute_command_button = customtkinter.CTkButton(master=self, fg_color="transparent", text="Send",border_width=2, text_color=("gray10", "#DCE4EE"), command=self.execute_netconf_command)
        self.execute_command_button.grid(row=3, column=3, padx=(20, 20), pady=(20, 20), sticky="nsew")

        # create textbox
        self.textbox = customtkinter.CTkTextbox(self, width=250)
        self.textbox.grid(row=0, column=1, rowspan=3, padx=(20, 0), pady=(20, 0), sticky="nsew")

        # create radiobutton frame
        self.connection_parameters_frame = customtkinter.CTkFrame(self)
        self.connection_parameters_frame.grid(row=0, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")
        self.radio_var = tkinter.IntVar(value=0)
        self.label_radio_group = customtkinter.CTkLabel(master=self.connection_parameters_frame, text="Connection Parameters:")
        self.label_radio_group.grid(row=0, column=2, columnspan=1, padx=10, pady=10, sticky="", )
        self.address = customtkinter.CTkEntry(self.connection_parameters_frame, placeholder_text="Device Address")
        if self.cfg['addr']:
            self.address.insert(0, self.cfg['addr'])
        self.address.grid(row=1, column=2, pady=10, padx=20, sticky="n")
        self.username = customtkinter.CTkEntry(self.connection_parameters_frame)
        if self.cfg['user']:
            self.username.insert(0, self.cfg['user'])
        self.username.grid(row=2, column=2, pady=10, padx=20, sticky="n")
        self.password = customtkinter.CTkEntry(self.connection_parameters_frame, placeholder_text="Password", show="*")
        if self.cfg['pass']:
            self.password.insert(0, self.cfg['pass'])
        self.password.grid(row=3, column=2, pady=10, padx=20, sticky="n")
        self.port_select = customtkinter.CTkEntry(self.connection_parameters_frame)
        self.port_select.grid(row=4, column=2, pady=10, padx=20, sticky="n")
        if self.cfg['port']:
            self.port_select.insert(0, self.cfg['port'])

        self.save_connection_parameters_button =  customtkinter.CTkButton(self.connection_parameters_frame, command=self.save_connection_parameters, text="Save Parameters")
        self.save_connection_parameters_button.grid(row=9, column=2, pady=(10,0), padx=20, sticky="n")

        # set default values
        self.change_appearance_mode_event("System")
        self.change_scaling_event("100%")
        self.textbox.delete(0.0,'end')
        self.textbox.insert("0.0", "XML Command Goes here!" )

    #UI METHODS
    def open_input_dialog_event(self):
        dialog = customtkinter.CTkInputDialog(text="Type in a number:", title="CTkInputDialog")
        print("CTkInputDialog:", dialog.get_input())

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

    def exit_app_func(self):
        self.quit()

    def import_xml_file(self):
        files = [('XML File', '*.xml')]
        file = filedialog.askopenfile(filetypes=files, defaultextension=files)  
        if file is not None:
            content = file.read()
            self.textbox.delete(0.0,'end')
            self.textbox.insert("0.0", content )

    def export_xml_file(self):
        files = [('XML File', '*.xml')]
        file_path = filedialog.asksaveasfilename(filetypes=files, defaultextension=files)  
        if file_path:
            with open(file_path, "w") as xmlOutput:
                xmlOutput.write(self.textbox.get('1.0', END))

    #CONNECTION PARAMETERS METHODS
    def save_connection_parameters(self):
        if self.address.get() == "" or self.port_select.get() == "" or self.username.get()=="" or self.password.get()=="":
            messagebox.showerror(APP_TITLE, "ERROR: Connection parameters cannot be empty!")            
            return

        if not self.is_ip_valid():
            messagebox.showerror(APP_TITLE, "ERROR: IP Format invalid!")            
            return

        if not self.is_port_valid():
            messagebox.showerror(APP_TITLE, "ERROR: Port must be in range 0-65535")            
            return

        self.cfg['addr'] = self.address.get()
        self.cfg['port'] = self.port_select.get()
        self.cfg['user'] = self.username.get()
        self.cfg['pass'] = self.password.get()
        self.cfg_mgr.save()

        messagebox.showinfo(APP_TITLE, "Connection parameters updated successfully!")

    def is_port_valid(self):
        try:
            port_num = int(self.port_select.get())
            if 0 < port_num <= 65535:
                return True
            else:
                return False
        except:
            return False

    def is_ip_valid(self):
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        
        if re.fullmatch(ip_pattern, self.address.get()):
            octets = self.address.get().split('.')
            for octet in octets:
                if not (0 <= int(octet) <= 255):
                    return False
            return True
        return False

    def is_empty_connection_parameters(self):
        if self.cfg['addr'] == "" or self.cfg['port'] == "" or self.cfg['user']=="" or self.cfg['pass']=="":
            return True
        return False

    #PROFINET STATUS METHODS
    def profinet_status_func(self, status):
        xml_path =""
        if(status=="Enable"):
            xml_path = resource_path("enable-profinet.xml")
        else:
            xml_path = resource_path("disable-profinet.xml")

        with open(xml_path, 'r') as file:
            xml_payload = file.read()
        
        self.textbox.delete(0.0,'end')
        self.textbox.insert("0.0", xml_payload )

    #GET CONFIGURATION METHOD    
    def getconfiguration_func(self, conf_type):
        if self.is_empty_connection_parameters():
            messagebox.showerror(APP_TITLE, "ERROR: Connection parameters cannot be empty!")            
            return
        conf_type = str(conf_type).lower()
        with manager.connect_ssh(host=self.cfg['addr'], port=self.cfg['port'], username=self.cfg['user'], password=self.cfg['pass'], hostkey_verify=False) as m:
            fetch_res = m.get_config(source=conf_type)
            dom = parseString(fetch_res.xml)
            self.textbox.delete(0.0,'end')
            self.textbox.insert("0.0", str(dom.toprettyxml()) )
        
    #REBOOT METHODS
    def reboot_func(self):
        self.textbox.delete(0.0,'end')
        self.textbox.insert("0.0", """<system-restart xmlns="urn:ietf:params:xml:ns:yang:ietf-system"/>""" )
    
    def execute_reboot(self):
        factory_reset_rpc = to_ele(self.textbox.get("1.0", END))
        with manager.connect(host=self.cfg['addr'], port=self.cfg['port'], username=self.cfg['user'], password=self.cfg['pass'], hostkey_verify=False) as m:
            response = m.dispatch(factory_reset_rpc, source=None, filter=None)

    #FACTORY RESET METHODS
    def factory_reset_func(self):
        self.textbox.delete(0.0,'end')
        self.textbox.insert("0.0", """<factory-reset xmlns="urn:ietf:params:xml:ns:yang:ietf-factory-default"/>""" )
    
    def execute_factory_reset(self):
        factory_reset_rpc = to_ele(self.textbox.get("1.0", END))
        with manager.connect(host=self.cfg['addr'], port=self.cfg['port'], username=self.cfg['user'], password=self.cfg['pass'], hostkey_verify=False) as m:
            response = m.dispatch(factory_reset_rpc, source=None, filter=None)

    #TIME SETTING METHODS
    def time_set_func(self):
        self.textbox.delete(0.0,'end')
        self.textbox.insert("0.0", """<set-current-datetime xmlns="urn:ietf:params:xml:ns:yang:ietf-system">
                                <current-datetime>"""+get_current_time()+"""</current-datetime>
                            </set-current-datetime>""" )
    def execute_time_set(self):
        factory_reset_rpc = to_ele(self.textbox.get("1.0", END))
        with manager.connect(host=self.cfg['addr'], port=self.cfg['port'], username=self.cfg['user'], password=self.cfg['pass'], hostkey_verify=False) as m:
            response = m.dispatch(factory_reset_rpc, source=None, filter=None)

    #NETCONF COMMANDS METHODS
    def get_type_of_command(self):
        if "<system-restart xmlns" in str(self.textbox.get("1.0", END)):
            return CommandType.REBOOT.value
        if "<factory-reset xmlns" in str(self.textbox.get("1.0", END)):
            return CommandType.FACTORY_RESET.value
        if "<set-current-datetime xmlns" in str(self.textbox.get("1.0", END)):
            return CommandType.TIME_SET.value
        return CommandType.DEFAULT.value

    def execute_netconf_command(self):
        if self.is_empty_connection_parameters():
            messagebox.showerror(APP_TITLE, "ERROR: Connection parameters cannot be empty!")            
            return

        if self.get_type_of_command() == CommandType.REBOOT.value:
            self.execute_reboot()
            return
        
        if self.get_type_of_command() == CommandType.FACTORY_RESET.value:
            self.execute_factory_reset()
            return
        
        if self.get_type_of_command() == CommandType.TIME_SET.value:
            self.execute_time_set()
            return

        try:
            with manager.connect(host=self.cfg['addr'], port=self.cfg['port'], username=self.cfg['user'], password=self.cfg['pass'], hostkey_verify=False) as m:
                send_res = m.edit_config(target='running', config=self.textbox.get('1.0', END))
                dom = parseString(send_res.xml)
                print(dom.toprettyxml())
                response = m.copy_config(source='running', target='startup')

                if response.ok:
                    messagebox.showinfo(APP_TITLE, "Command Run Succesfully!")            
                else:   
                    messagebox.showerror(APP_TITLE, str(response))
        except Exception as err:
            messagebox.showerror(APP_TITLE,"Command failed! Check connection parameters.")
            print(err)

        

if __name__ == "__main__":
    app = App()
    app.mainloop()
