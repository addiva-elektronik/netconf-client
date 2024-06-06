import tkinter
import os
import re
import json
import subprocess
import customtkinter
from tkinter import *
from tkinter import messagebox, filedialog
from PIL import ImageTk, Image
from ncclient import manager
from ncclient.transport.errors import AuthenticationError, SSHError
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

class NetconfConnection:
    def __init__(self, cfg, app):
        self.cfg = cfg
        self.app = app
        self.manager = None

    def __enter__(self):
        try:
            self.manager = manager.connect(host=self.cfg['addr'],
                                           port=self.cfg['port'],
                                           username=self.cfg['user'],
                                           password=self.cfg['pass'],
                                           hostkey_verify=False,
                                           allow_agent=False,
                                           timeout=30)
            self.app.status("Connected to NETCONF server")
            return self.manager
        except AuthenticationError as err:
            self.app.error(f"Authentication failed: {err}")
        except SSHError as err:
            self.app.error(f"SSH connection failed: {err}")
        except Exception as err:
            self.app.error(f"An unexpected error occurred: {err}")
            raise err

    def __exit__(self, exc_type, exc_value, traceback):
        if self.manager is not None:
            self.manager.close_session()
            self.app.status("Disconnected from NETCONF server")

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


        self.menubar = Menu(self, tearoff=0, bd=0)
        self.config(menu=self.menubar)

        edit_menu = Menu(self.menubar, tearoff=0)
        file_menu = Menu(self.menubar, tearoff=0)

        theme_submenu = Menu(edit_menu, tearoff=0)
        theme_submenu.add_command(label="Light", command = lambda: self.change_theme_mode_event("Light"))
        theme_submenu.add_command(label="Dark", command = lambda: self.change_theme_mode_event("Dark"))
        edit_menu.add_cascade(label='Theme', menu=theme_submenu, underline=0)

        zoom_submenu = Menu(edit_menu, tearoff=0)
        zoom_submenu.add_command(label="80%", command =  lambda: self.change_scaling_event("80%"))
        zoom_submenu.add_command(label="90%", command = lambda: self.change_scaling_event("90%"))
        zoom_submenu.add_command(label="100%", command = lambda: self.change_scaling_event("100%"))
        zoom_submenu.add_command(label="110%", command = lambda: self.change_scaling_event("110%"))
        zoom_submenu.add_command(label="120%", command = lambda: self.change_scaling_event("120%"))

        edit_menu.add_cascade(label='Zoom', menu=zoom_submenu, underline=0)

        file_menu.add_command(label="Import XML", underline=0, command=self.import_xml_file)
        file_menu.add_command(label="Export XML", underline=0, command=self.export_xml_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", underline=0, command=self.exit_app_func)

        self.menubar.add_cascade(label="File", underline=0, menu=file_menu)
        self.menubar.add_cascade(label="Edit", underline=0, menu=edit_menu)


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

        # create textbox
        self.textbox = customtkinter.CTkTextbox(self, width=250)
        self.textbox.grid(row=0, column=1, columnspan=2, rowspan=3, padx=(20, 0), pady=(20, 0), sticky="nsew")

        self.status_label = customtkinter.CTkLabel(self, anchor="w")
        self.status_label.grid(row=3, column=1, columnspan=1, padx=(20, 0), pady=(0, 0), sticky="we")
        self.status("Ready")

        self.send_button = customtkinter.CTkButton(master=self, fg_color="transparent", text="Send", border_width=2, text_color=("gray10", "#DCE4EE"), command=self.execute_netconf_command)
        self.send_button.grid(row=3, column=2, padx=(20, 0), pady=(20, 20), sticky="nsew")

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
        self.set_system_theme()
        self.change_scaling_event("100%")
        self.textbox.delete(0.0,'end')
        self.textbox.insert("0.0", "XML Command Goes here!" )

    #UI METHODS
    def set_system_theme(self):
        try:
            # Check for dark mode on Linux Mint using gsettings
            result = subprocess.run(['gsettings', 'get', 'org.cinnamon.desktop.interface', 'gtk-theme'], capture_output=True, text=True)
            if result.returncode == 0:
                theme = result.stdout.strip().strip("'")
                if 'dark' in theme.lower():
                    self.change_theme_mode_event("Dark")
                else:
                    self.change_theme_mode_event("Light")
                return
        except Exception:
            pass

        try:
            # Check for dark mode on Gnome using gsettings
            result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'], capture_output=True, text=True)
            if result.returncode == 0:
                theme = result.stdout.strip().strip("'")
                if 'dark' in theme.lower():
                    self.change_theme_mode_event("Dark")
                else:
                    self.change_theme_mode_event("Light")
                return
        except Exception:
            pass

        try:
            # Check for dark mode on Windows
            if platform.system() == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize')
                value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
                if value == 0:
                    self.change_theme_mode_event("Dark")
                else:
                    self.change_theme_mode_event("Light")
                return
        except Exception:
            pass

        # Fallback to CustomTkinter detected system
        print("Falling back to ctk system theme")
        self.change_theme_mode_event("System")

    def get_menu_bg_color(self):
        if customtkinter.get_appearance_mode() == "Dark":
            return "#333333"
        else:
            return "#f0f0f0"

    def get_menu_fg_color(self):
        if customtkinter.get_appearance_mode() == "Dark":
            return "#ffffff"
        else:
            return "#000000"

    def update_menu_colors(self):
        self.menubar.configure(bg=self.get_menu_bg_color(), fg=self.get_menu_fg_color())
        for menu in self.menubar.winfo_children():
            menu.configure(bg=self.get_menu_bg_color(), fg=self.get_menu_fg_color())

    def _update_status(self, message, error=False):
        if error:
            self.status_label.configure(text=f"Error: {message}",
                                        text_color=("#FF0000", "#FF4C4C"))
        else:
            self.status_label.configure(text=f"Status: {message}",
                                        text_color=("#000000", "#FFFFFF"))

    def status(self, message):
        self._update_status(message, error=False)

    def error(self, message):
        self._update_status(message, error=True)

    def show(self, text):
        self.textbox.delete(0.0, 'end')
        self.textbox.insert("0.0", text)

    def open_input_dialog_event(self):
        dialog = customtkinter.CTkInputDialog(text="Type in a number:", title="CTkInputDialog")
        print("CTkInputDialog:", dialog.get_input())

    def change_theme_mode_event(self, theme: str):
        customtkinter.set_appearance_mode(theme)
        self.update_menu_colors()

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
            self.show(content)

    def export_xml_file(self):
        files = [('XML File', '*.xml')]
        file_path = filedialog.asksaveasfilename(filetypes=files, defaultextension=files)  
        if file_path:
            with open(file_path, "w") as xmlOutput:
                xmlOutput.write(self.textbox.get('1.0', END))

    #CONNECTION PARAMETERS METHODS
    def save_connection_parameters(self):
        if self.address.get() == "" or self.port_select.get() == "" or self.username.get()=="" or self.password.get()=="":
            self.error("Connection parameters cannot be empty!")
            return

        if not self.is_port_valid():
            self.error("Port must be in range 0-65535")
            return

        self.cfg['addr'] = self.address.get()
        self.cfg['port'] = self.port_select.get()
        self.cfg['user'] = self.username.get()
        self.cfg['pass'] = self.password.get()
        self.cfg_mgr.save()

        self.status("Connection parameters updated.")

    def is_port_valid(self):
        try:
            port_num = int(self.port_select.get())
            if 0 < port_num <= 65535:
                return True
            else:
                return False
        except:
            return False

    def is_empty_connection_parameters(self):
        if self.cfg['addr'] == "" or self.cfg['port'] == "" or self.cfg['user']=="" or self.cfg['pass']=="":
            return True
        return False

    #PROFINET STATUS METHODS
    def profinet_status_func(self, status):
        xml_path = ""
        if status == "Enable":
            xml_path = resource_path("enable-profinet.xml")
        else:
            xml_path = resource_path("disable-profinet.xml")

        with open(xml_path, 'r') as file:
            xml_payload = file.read()
        self.show(xml_payload)

    #GET CONFIGURATION METHOD    
    def getconfiguration_func(self, conf_type):
        if self.is_empty_connection_parameters():
            self.error("Connection parameters cannot be empty!")
            return

        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return
            try:
                conf_type = str(conf_type).lower()
                fetch_res = m.get_config(source=conf_type)
                dom = parseString(fetch_res.xml)
                self.show(str(dom.toprettyxml()))
            except Exception as err:
                self.error(f"Failed fetching configuration: {err}")
                print(err)

    #REBOOT METHODS
    def reboot_func(self):
        self.show("""<system-restart xmlns="urn:ietf:params:xml:ns:yang:ietf-system"/>""")
    
    def execute_reboot(self):
        rpc = to_ele(self.textbox.get("1.0", END))
        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return
            try:
                response = m.dispatch(rpc, source=None, filter=None)
                self.show(response)
            except Exception as err:
                self.error(f"Failed reboot: {err}")
                print(err)

    #FACTORY RESET METHODS
    def factory_reset_func(self):
        self.show("""<factory-reset xmlns="urn:ietf:params:xml:ns:yang:ietf-factory-default"/>""" )
    
    def execute_factory_reset(self):
        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return
            try:
                rpc = to_ele(self.textbox.get("1.0", END))
                response = m.dispatch(rpc, source=None, filter=None)
                self.show(response)
            except Exception as err:
                self.error(f"Failed factory reset: {err}")
                print(err)

    #TIME SETTING METHODS
    def time_set_func(self):
        self.show(f"""<set-current-datetime xmlns="urn:ietf:params:xml:ns:yang:ietf-system">
    <current-datetime>{get_current_time()}</current-datetime>
</set-current-datetime>""")

    def execute_time_set(self):
        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return
            try:
                rpc = to_ele(self.textbox.get("1.0", END))
                response = m.dispatch(rpc, source=None, filter=None)
                self.show(response)
            except Exception as err:
                self.error(f"{err}")
                print(err)

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
            self.error("Connection parameters cannot be empty!")
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

        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return
            try:
                send_res = m.edit_config(target='running', config=self.textbox.get('1.0', END))
                dom = parseString(send_res.xml)
                print(dom.toprettyxml())
                response = m.copy_config(source='running', target='startup')

                if response.ok:
                    self.status("Command run successfully!")
                else:
                    self.error(str(response))
            except Exception as err:
                self.error("Command failed! Check connection parameters.")
                print(err)


if __name__ == "__main__":
    app = App()
    app.mainloop()
