import tkinter
import os
import re
import customtkinter
from tkinter import *
from PIL import ImageTk, Image
from ncclient import manager
from xml.dom.minidom import parseString
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

class App(customtkinter.CTk):
    def __init__(self):
        self.ipinuse=""
        self.portinuse=""
        self.passwordinuse=""
        self.usernameinuse=""
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(f"{1100}x{580}")

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=10, sticky="nsew")
        
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="NETCONF Client", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.factory_reset_button = customtkinter.CTkButton(self.sidebar_frame, command=self.factory_reset_func, text="Factory Reset")
        self.factory_reset_button.grid(row=1, column=0, padx=20, pady=10)
        
        self.reboot_button = customtkinter.CTkButton(self.sidebar_frame, command=self.reboot_func, text="Reboot")
        self.reboot_button.grid(row=2, column=0, padx=20, pady=10)
        
        self.profinet_label = customtkinter.CTkLabel(self.sidebar_frame, text="Profinet Status:", anchor="w")
        self.profinet_label.grid(row=3, column=0, padx=20, pady=(10, 0))
        self.enable_profinet_button = customtkinter.CTkOptionMenu(self.sidebar_frame, command=self.profinet_status_func, values=["Enable","Disable"])
        self.enable_profinet_button.grid(row=4, column=0, padx=20, pady=10)

        self.change_password_button = customtkinter.CTkButton(self.sidebar_frame, command=self.change_password_func, text="Change Password")
        self.change_password_button.grid(row=5, column=0, padx=20, pady=10)

        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=6, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=7, column=0, padx=20, pady=(10, 10))
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="Zoom:", anchor="w")
        self.scaling_label.grid(row=8, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"],
                                                               command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=9, column=0, padx=20, pady=(10, 20))

        self.execute_command_button = customtkinter.CTkButton(master=self, fg_color="transparent", text="Execute Command",border_width=2, text_color=("gray10", "#DCE4EE"), command=self.execute_netconf_command)
        self.execute_command_button.grid(row=3, column=3, padx=(20, 20), pady=(20, 20), sticky="nsew")

        # create textbox
        self.textbox = customtkinter.CTkTextbox(self, width=250)
        self.textbox.grid(row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

        # create radiobutton frame
        self.connection_parameters_frame = customtkinter.CTkFrame(self)
        self.connection_parameters_frame.grid(row=0, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")
        self.radio_var = tkinter.IntVar(value=0)
        self.label_radio_group = customtkinter.CTkLabel(master=self.connection_parameters_frame, text="Connection Parameters:")
        self.label_radio_group.grid(row=0, column=2, columnspan=1, padx=10, pady=10, sticky="", )
        self.ipaddress= customtkinter.CTkEntry(master=self.connection_parameters_frame,placeholder_text="127.0.0.1")
        self.ipaddress.grid(row=1, column=2, pady=10, padx=20, sticky="n")
        self.username = customtkinter.CTkEntry(master=self.connection_parameters_frame, placeholder_text="Username")
        self.username.grid(row=2, column=2, pady=10, padx=20, sticky="n")
        self.password = customtkinter.CTkEntry(master=self.connection_parameters_frame, placeholder_text="Password", show="*")
        self.password.grid(row=3, column=2, pady=10, padx=20, sticky="n")
        self.port_select =  customtkinter.CTkEntry(master=self.connection_parameters_frame, placeholder_text="Port")
        self.port_select.grid(row=4, column=2, pady=10, padx=20, sticky="n")
        self.save_connection_parameters_button =  customtkinter.CTkButton(self.connection_parameters_frame, command=self.save_connection_parameters, text="Save Parameters")
        self.save_connection_parameters_button.grid(row=5, column=2, pady=(200,0), padx=20, sticky="n")
        #default values for connection parameters
        self.username.delete(0,'end')
        self.username.insert(0,"admin")
        self.port_select.delete(0, 'end')
        self.port_select.insert(0, "830")

        # set default values
        self.appearance_mode_optionemenu.set("System")
        self.change_appearance_mode_event("System")
        self.scaling_optionemenu.set("100%")
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

    def open_popup(self,popup_title, popup_message):
        top=Toplevel(self)
        top.geometry("750x250")
        top.title(APP_TITLE+": "+popup_title)
        Label(top, text= popup_message, font="Arial 20").place(x=80,y=80)
    
    #CONNECTION PARAMETERS METHODS
    def save_connection_parameters(self):
        if self.ipaddress.get() == "" or self.port_select.get() == "" or self.username.get()=="" or self.password.get()=="":
            self.open_popup("ERROR","ERROR: Connection parameters cannot be empty!")
            return

        if not self.is_ip_valid():
            self.open_popup("ERROR","ERROR: IP Format invalid!")
            return

        if not self.is_port_valid():
            self.open_popup("ERROR","Port must be in range 0-65535")
            return

        self.ipinuse = self.ipaddress.get()
        self.portinuse = self.port_select.get()
        self.usernameinuse = self.username.get()
        self.passwordinuse = self.password.get()

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
        
        if re.fullmatch(ip_pattern, self.ipaddress.get()):
            octets = self.ipaddress.get().split('.')
            for octet in octets:
                if not (0 <= int(octet) <= 255):
                    return False
            return True
        return False

    def is_empty_connection_parameters(self):
        if self.ipinuse == "" or self.portinuse == "" or self.usernameinuse=="" or self.passwordinuse=="":
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
        
        
    #FACTORY RESET METHODS
    def factory_reset_func(self):
        print("factory reset called")
    
    #REBOOT METHODS
    def reboot_func(self):
        print("reboot called")

    #CHANGE PASSWORD METHODS
    def change_password_func(self):
        print("change password called")    
    #NETCONF COMMANDS METHODS
    def execute_netconf_command(self):
        if self.is_empty_connection_parameters():
            self.open_popup("ERROR","ERROR: Connection parameters cannot be empty!")
            return
        try:
            with manager.connect(host=self.ipinuse, port=self.portinuse, username=self.usernameinuse, password=self.passwordinuse, hostkey_verify=False) as m:
                send_res = m.edit_config(target='running', config=self.textbox.get('1.0', END))
                dom = parseString(send_res.xml)
                print(dom.toprettyxml())
                response = m.copy_config(source='running', target='startup')

                if response.ok:
                    self.open_popup("SUCCESS","Command Run Succesfully!")
                else:    
                    self.open_popup("ERROR", str(response))
        except Exception as err:
            self.open_popup("ERROR","Command failed! Check connection parameters.")
            print(err)

        

if __name__ == "__main__":
    app = App()
    app.mainloop()