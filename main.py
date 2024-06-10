"""
Simple (and portable) NETCONF client

Copyright (c) 2024 Ejub Šabić <ejub1946@outlook.com>
"""
import os
import json
import re
import sys
import argparse
import subprocess
import functools
import datetime
import platform
import http.server
import socketserver
import socket
import logging
import threading
import tkinter as tk
import time
from xml.dom.minidom import parseString
import psutil
from tkinter import Menu, END, filedialog
from PIL import Image, ImageTk, ImageOps
import customtkinter as ctk
from customtkinter import CTkImage
import netifaces
from ncclient import manager
from ncclient.transport.errors import AuthenticationError, SSHError
from ncclient.xml_ import to_ele


APP_TITLE = "Simple NETCONF Client"
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

RPC_SYSTEM_RESTART = """<system-restart xmlns="urn:ietf:params:xml:ns:yang:ietf-system"/>"""
RPC_FACTORY_RESET = """<factory-reset xmlns="urn:ietf:params:xml:ns:yang:ietf-factory-default"/>"""
RPC_SET_DATETIME = f"""<set-current-datetime xmlns="urn:ietf:params:xml:ns:yang:ietf-system">
    <current-datetime>{datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()}</current-datetime>
</set-current-datetime>
"""
RPC_GET_OPER = """<get-data xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-nmda"
          xmlns:ds="urn:ietf:params:xml:ns:yang:ietf-datastores">
    <datastore>ds:operational</datastore>
    <subtree-filter>
        <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
        <system-state xmlns="urn:ietf:params:xml:ns:yang:ietf-system"/>
    </subtree-filter>
</get-data>
"""

class ConfigManager:
    def __init__(self, filename='.netconf_config.json'):
        self.filename = filename
        self.filepath = self._get_file()
        self.default_cfg = {
            'addr': '',
            'port': 830,
            'user': "admin",
            'pass': '',
            'ssh-agent': True,
            'theme': "System",
            'zoom': "100%",
            'server_iface': 'virbr0',
            'server_enabled': True,
            'server_path': '',
            'server_port': 8080
        }
        self.cfg = self.default_cfg.copy()
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
        # Merge default config with loaded config
        self._merge_defaults()

    def _merge_defaults(self):
        for key, value in self.default_cfg.items():
            if key not in self.cfg:
                self.cfg[key] = value


class NetconfConnection:
    def __init__(self, cfg, app):
        self.cfg = cfg
        self.app = app
        self.manager = None

    def __enter__(self):
        try:
            host = self.cfg['addr']
            port = self.cfg['port']
            self.app.status(f"Connecting to {host} port {port}, please wait ...")
            self.manager = manager.connect(host=host,
                                           port=port,
                                           username=self.cfg['user'],
                                           password=self.cfg['pass'],
                                           hostkey_verify=False,
                                           allow_agent=self.cfg['ssh-agent'],
                                           timeout=30)
            self.app.status(f"Connected to NETCONF server {host}.")
            return self.manager
        except AuthenticationError as err:
            self.app.error(f"Authentication with {host} failed: {err}")
        except SSHError as err:
            self.app.error(f"SSH connection to {host} port {port} failed: {err}")
        except Exception as err:
            self.app.error(f"An unexpected error occurred: {err}")
            raise err

    def __exit__(self, exc_type, exc_value, traceback):
        if self.manager is not None:
            self.manager.close_session()
            self.app.status("Disconnected from NETCONF server")


class App(ctk.CTk):
    def __init__(self):
        self.cfg_mgr = ConfigManager()
        self.cfg = self.cfg_mgr.cfg
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(f"{1100}x{580}")
        self.minsize(800, 600)  # Handle shrinking app window on zoom in/out

        # Create theme and zoom variables for menu interaction
        self.theme_var = ctk.StringVar(value=self.cfg['theme'])
        self.zoom_var = ctk.StringVar(value=self.cfg['zoom'])

        # Load icons
        self.load_icons()

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        self.menubar = Menu(self, tearoff=0, bd=0)
        self.config(menu=self.menubar)

        self.settings_menu = Menu(self.menubar, tearoff=0)
        self.file_menu = Menu(self.menubar, tearoff=0)

        self.settings_menu.add_radiobutton(label="System", variable=self.theme_var,
                                           command=lambda: self.change_theme_mode_event("System"))
        self.settings_menu.add_radiobutton(label="Light", variable=self.theme_var,
                                           command=lambda: self.change_theme_mode_event("Light"))
        self.settings_menu.add_radiobutton(label="Dark", variable=self.theme_var,
                                           command=lambda: self.change_theme_mode_event("Dark"))

        self.settings_menu.add_separator()

        self.settings_menu.add_command(label="Zoom In", accelerator="Ctrl++",
                                       command=self.zoom_in_event)
        self.bind_all("<Control-plus>", lambda event: self.zoom_in_event())

        self.settings_menu.add_command(label="Zoom Out", accelerator="Ctrl+-",
                                       command=self.zoom_out_event)
        self.bind_all("<Control-minus>", lambda event: self.zoom_out_event())

        self.file_menu.add_command(label="Open", underline=0,
                                   accelerator="Ctrl+O",
                                   command=self.open_file,
                                   image=self.load_icon, compound="left")
        self.bind_all("<Control-o>", lambda event: self.open_file)
        self.file_menu.add_command(label="Save", underline=0,
                                   accelerator="Ctrl+S",
                                   command=self.save_file,
                                   image=self.save_icon, compound="left")
        self.bind_all("<Control-s>", lambda event: self.save_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", underline=0,
                                   accelerator="Ctrl+Q",
                                   command=self.quit,
                                   image=self.exit_icon, compound="left")
        self.bind_all("<Control-q>", lambda event: self.quit())

        self.menubar.add_cascade(label="File", underline=0, menu=self.file_menu)
        self.menubar.add_cascade(label="Settings", underline=0, menu=self.settings_menu)

        self.update_menu_icons()

        # left sidebar with netconf RPCs ######################################
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=8, sticky="nsew")

        self.logo = ctk.CTkLabel(self.sidebar_frame, text="NETCONF Client",
                                 font=ctk.CTkFont(size=20, weight="bold"))
        self.logo.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.factory_reset = ctk.CTkButton(self.sidebar_frame,
                                           command=self.factory_reset_cb,
                                           text="Factory Reset")
        self.factory_reset.grid(row=1, column=0, padx=20, pady=10)

        self.reboot = ctk.CTkButton(self.sidebar_frame,
                                    command=self.reboot_cb,
                                    text="Reboot")
        self.reboot.grid(row=2, column=0, padx=20, pady=10)

        self.time_set = ctk.CTkButton(self.sidebar_frame,
                                      command=self.time_set_cb,
                                      text="Set System Time")
        self.time_set.grid(row=3, column=0, padx=20, pady=10)

        self.upgrade_file = None
        self.upgrade_button = ctk.CTkButton(self.sidebar_frame,
                                            command=self.upgrade_cb,
                                            text="Upgrade System")
        self.upgrade_button.grid(row=4, column=0, padx=20, pady=10)

        self.get_oper = ctk.CTkButton(self.sidebar_frame,
                                      command=self.get_oper_cb,
                                      text="Get Status")
        self.get_oper.grid(row=5, column=0, padx=20, pady=10)

        self.get_config_label = ctk.CTkLabel(self.sidebar_frame,
                                             text="Get configuration",
                                             anchor="w")
        self.get_config_label.grid(row=6, column=0, padx=20, pady=(30, 0))
        self.get_config_button = ctk.CTkOptionMenu(self.sidebar_frame,
                                                   command=self.get_config_cb,
                                                   values=["Running",
                                                           "Startup"])
        self.get_config_button.grid(row=7, column=0, padx=20, pady=0)

        self.profinet_label = ctk.CTkLabel(self.sidebar_frame,
                                           text="PROFINET Configuration",
                                           anchor="w")
        self.profinet_label.grid(row=8, column=0, padx=20, pady=(30, 0))
        self.profinet_button = ctk.CTkOptionMenu(self.sidebar_frame,
                                                 command=self.profinet_cb,
                                                 values=["Enable",
                                                         "Disable"])
        self.profinet_button.grid(row=9, column=0, padx=20, pady=0)

        # main XML textbox ####################################################
        self.textbox = ctk.CTkTextbox(self, width=250)
        self.textbox.grid(row=0, column=1, columnspan=2, rowspan=3,
                          padx=(10, 0), pady=(18, 0), sticky="nsew")

        self.status_label = ctk.CTkLabel(self, anchor="w")
        self.status_label.grid(row=3, column=1, columnspan=1, padx=(20, 0),
                               pady=(0, 0), sticky="we")
        self.status("Ready")

        self.send_button = ctk.CTkButton(master=self, fg_color="transparent",
                                         text="Send", border_width=2,
                                         text_color=("gray10", "#DCE4EE"),
                                         command=self.execute_netconf_command)
        self.send_button.grid(row=3, column=2, padx=(20, 0), pady=(20, 20),
                              sticky="nsew")

        # right sidebar with settings #########################################
        self.tabview = ctk.CTkTabview(self, width=230, height=300)
        self.tabview.grid(row=0, column=3, rowspan=8, padx=(10, 0), pady=(0, 0), sticky="nsew")
        self.tabview.add("Connection")
        self.tabview.add("Web Server")

        # Connection Parameters tab
        self.conn_param_frame = ctk.CTkFrame(self.tabview.tab("Connection"))
        self.conn_param_frame.pack(fill="both", expand=True)

        self.conn_param_label = ctk.CTkLabel(master=self.conn_param_frame,
                                             text="Connection Parameters",
                                             font=("Arial", 16))
        self.conn_param_label.grid(row=0, column=0, columnspan=2,
                                   padx=10, pady=10, sticky="")

        self.entries = {
            'Device Address': ('addr', 1),
            'Username': ('user', 2),
            'Password': ('pass', 3),
            'Port': ('port', 4)
        }

        for placeholder, (cfg_key, row) in self.entries.items():
            show_char = '*' if cfg_key == 'pass' else None
            entry = ctk.CTkEntry(self.conn_param_frame,
                                 placeholder_text=placeholder, show=show_char)
            if self.cfg[cfg_key]:
                entry.insert(0, self.cfg[cfg_key])
            entry.grid(row=row, column=0, pady=10, padx=10, sticky="ew")

        self.ssh_agent = ctk.CTkSwitch(self.conn_param_frame, text="Use SSH Agent")
        self.ssh_agent.grid(row=5, column=0, pady=10, padx=10, sticky="n")
        if self.cfg['ssh-agent']:
            self.ssh_agent.select()

        self.save_button = ctk.CTkButton(self.conn_param_frame,
                                         command=self.save_params, text="Save")
        self.save_button.grid(row=6, column=0, pady=10, padx=10, sticky="ew")

        # Web Server Settings tab
        self.web_server_frame = ctk.CTkFrame(self.tabview.tab("Web Server"))
        self.web_server_frame.pack(fill="both", expand=True)

        self.web_server_label = ctk.CTkLabel(self.web_server_frame,
                                             text="Web Server Settings",
                                             font=("Arial", 16))
        self.web_server_label.grid(row=0, column=0, columnspan=2,
                                   padx=10, pady=10, sticky="")

        self.interface_var = tk.StringVar()
        self.interface_menu = ctk.CTkOptionMenu(self.web_server_frame,
                                                variable=self.interface_var)
        self.interface_menu.grid(row=1, column=0, pady=10, padx=10, sticky="ew")
        self.update_interface_menu()

        self.server_port_entry = ctk.CTkEntry(self.web_server_frame, placeholder_text="Server Port")
        self.server_port_entry.insert(0, str(self.cfg['server_port']))
        self.server_port_entry.grid(row=2, column=0, pady=10, padx=10, sticky="ew")

        # Server directory row
        self.directory_frame = ctk.CTkFrame(self.web_server_frame)
        self.directory_frame.grid(row=3, column=0, pady=10, padx=10, sticky="ew")

        self.server_path_entry = ctk.CTkEntry(self.directory_frame)
        self.server_path_entry.insert(0, self.cfg['server_path'])
        self.server_path_entry.grid(row=0, column=0, sticky="ew")

        self.folder_icon = CTkImage(light_image=Image.open("icons/open.png")
                                    .resize((20, 20), Image.LANCZOS))
        self.directory_button = ctk.CTkButton(self.directory_frame,
                                              image=self.folder_icon,
                                              text="", width=40,
                                              command=self.select_directory)
        self.directory_button.grid(row=0, column=1, padx=(3, 0))

        self.directory_frame.grid_columnconfigure(0, weight=4)
        self.directory_frame.grid_columnconfigure(1, weight=1)

        if self.cfg['server_path']:
            self.server_path = self.cfg['server_path']

        self.server_enabled = ctk.CTkSwitch(self.web_server_frame, text="Enabled")
        self.server_enabled.grid(row=4, column=0, pady=10, padx=10, sticky="n")
        if self.cfg['server_enabled']:
            self.server_enabled.select()

        # Save button
        self.interface_save_button = ctk.CTkButton(self.web_server_frame,
                                                   text="Save",
                                                   command=self.save_server_settings)
        self.interface_save_button.grid(row=5, column=0, pady=20, padx=10, sticky="")

        # Check if theme is set to "System", otherwise use saved theme
        self.change_theme_mode_event(self.cfg['theme'])
        self.change_scaling_event(f"{self.cfg['zoom']}")

        # set default values
        self.rpc_cb = None
        self.textbox.delete(0.0, 'end')
        self.textbox.insert("0.0", "XML Command Goes here!")

        # Start the web server
        self.start_file_server()

    def select_directory(self):
        directory = filedialog.askdirectory(initialdir=self.server_path)
        if directory:
            self.server_path = directory
            self.cfg['server_path'] = self.server_path
            self.server_path_entry.delete(0, 'end')
            self.server_path_entry.insert(0, str(self.cfg['server_path']))
            self.cfg_mgr.save()
            self.restart_file_server()
            self.status(f"Serving files from: {self.server_path}")

    def get_interfaces(slf):
        interfaces = psutil.net_if_addrs()
        interface_list = []
        for interface in interfaces:
            for addr in interfaces[interface]:
                if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                    interface_list.append((interface, addr.address))
                    break
        return interface_list

    def select_default_interface(self):
        """Get default interface, either a saved one, or first Ethernet"""
        patterns = ["eth", "en", "local area connection"]
        interfaces = self.get_interfaces()

        for interface, ip in interfaces:
            if interface == self.cfg['server_iface']:
                return interface, ip

        for interface, ip in interfaces:
            nm = interface.lower()
            if any(pattern in nm for pattern in patterns):
                return interface, ip

        return interfaces[0] if interfaces else (None, None)

    def update_interface_menu(self):
        interfaces = self.get_interfaces()
        if interfaces:
            self.interface_menu.configure(values=[f"{name} ({ip})" for name, ip in interfaces])
            default_interface, default_ip = self.select_default_interface()
            if default_interface:
                self.interface_var.set(f"{default_interface} ({default_ip})")

    def get_iface_ip(self):
        match = re.match(r"(\w+)\s+\(([\d\.]+)\)", self.interface_var.get())
        return match.groups() if match else (None, None)

    def save_server_settings(self):
        (iface, _) = self.get_iface_ip()
        self.cfg['server_iface'] = iface
        self.cfg['server_path'] = self.server_path
        self.cfg['server_enabled'] = self.server_enabled.get()
        try:
            self.cfg['server_port'] = int(self.server_port_entry.get())
        except ValueError:
            self.error("Invalid server port. Please enter a valid number.")
            return
        self.cfg_mgr.save()
        if self.restart_file_server():
            self.status("Web server settings updated and server restarted.")
        else:
            self.status("Web server settings saved, server not running.")

    def start_file_server(self):
        if not self.cfg['server_enabled']:
            return False

        interface = self.cfg['server_iface']
        port = self.cfg['server_port']
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=self.server_path)
        self.server = socketserver.TCPServer(("", port), handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.status(f"Serving files on {interface}:{port}")
        return True

    def restart_file_server(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        return self.start_file_server()

    # UI METHODS
    def load_icons(self):
        self.icon_images = {
            'save': Image.open("icons/save.png"),
            'load': Image.open("icons/open.png"),
            'exit': Image.open("icons/close.png")
        }
        self.icons = {
            'save': ImageTk.PhotoImage(self.icon_images['save']),
            'load': ImageTk.PhotoImage(self.icon_images['load']),
            'exit': ImageTk.PhotoImage(self.icon_images['exit'])
        }
        self.load_icon = self.icons['load']
        self.save_icon = self.icons['save']
        self.exit_icon = self.icons['exit']

    def update_menu_icons(self):
        if ctk.get_appearance_mode() == "Dark":
            color = "white"
        else:
            color = "black"

        load_icon = self.change_icon_color(self.icon_images['load'], color)
        save_icon = self.change_icon_color(self.icon_images['save'], color)
        exit_icon = self.change_icon_color(self.icon_images['exit'], color)

        self.file_menu.entryconfig(0, image=load_icon)
        self.file_menu.entryconfig(1, image=save_icon)
        self.file_menu.entryconfig(3, image=exit_icon)

        # Keep a reference to prevent garbage collection
        self.load_icon = load_icon
        self.save_icon = save_icon
        self.exit_icon = exit_icon

    def change_icon_color(self, image, color):
        # Convert the color to RGBA
        r, g, b = Image.new("RGB", (1, 1), color).getpixel((0, 0))
        color = (r, g, b, 255)

        # Create a new image with the same size and an RGBA mode
        new_image = Image.new("RGBA", image.size)

        # Get the pixel data from the original image
        pixels = image.getdata()

        # Process each pixel
        new_pixels = []
        for pixel in pixels:
            if pixel[3] > 0:  # If not transparent
                new_pixels.append(color)  # Change to the new color
            else:
                new_pixels.append(pixel)  # Preserve transparency

        new_image.putdata(new_pixels)

        # Convert to PhotoImage
        return ImageTk.PhotoImage(new_image)

    def get_system_theme(self):
        try:
            # Check for dark mode on Linux Mint using gsettings
            result = subprocess.run(['gsettings', 'get',
                                     'org.cinnamon.desktop.interface',
                                     'gtk-theme'],
                                    capture_output=True,
                                    text=True)
            if result.returncode == 0:
                theme = result.stdout.strip().strip("'")
                if 'dark' in theme.lower():
                    return "Dark"
                return "Light"
        except Exception:
            pass

        try:
            # Check for dark mode on Gnome using gsettings
            result = subprocess.run(['gsettings', 'get',
                                     'org.gnome.desktop.interface',
                                     'color-scheme'],
                                    capture_output=True,
                                    text=True)
            if result.returncode == 0:
                theme = result.stdout.strip().strip("'")
                if 'dark' in theme.lower():
                    return "Dark"
                return "Light"
        except Exception:
            pass

        try:
            # Check for dark mode on Windows
            if platform.system() == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\"\
                      "Microsoft\Windows\CurrentVersion\Themes\Personalize')
                value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
                if value == 0:
                    return "Dark"
                return "Light"
        except Exception:
            pass

        # Fallback to Ctk detected system
        return "System"

    def get_menu_bg_color(self):
        if ctk.get_appearance_mode() == "Dark":
            return "#333333"
        else:
            return "#f0f0f0"

    def get_menu_fg_color(self):
        if ctk.get_appearance_mode() == "Dark":
            return "#ffffff"
        else:
            return "#000000"

    def update_menu_colors(self):
        bg = self.get_menu_bg_color()
        fg = self.get_menu_fg_color()
        self.menubar.configure(bg=bg, fg=fg)
        for menu in self.menubar.winfo_children():
            menu.configure(bg=bg, fg=fg)

    def _update_status(self, message, error=False):
        if error:
            self.status_label.configure(text=f"Error: {message}",
                                        text_color=("#FF0000", "#FF4C4C"))
        else:
            self.status_label.configure(text=message,
                                        text_color=("#000000", "#FFFFFF"))
        # Update GUI even if we run in an callback
        self.update_idletasks()

    def rpc(self, message, method):
        self._update_status(f"RPC: {message}", error=False)
        self.rpc_cb = method

    def status(self, message):
        self._update_status(f"Status: {message}", error=False)

    def error(self, message):
        self._update_status(message, error=True)

    def show(self, text):
        self.textbox.delete(0.0, 'end')
        self.textbox.insert("0.0", text)

    def open_input_dialog_event(self):
        dialog = ctk.CTkInputDialog(text="Type in a number:",
                                    title="CTkInputDialog")
        print("CTkInputDialog:", dialog.get_input())

    def change_theme_mode_event(self, theme: str):
        self.cfg['theme'] = theme
        self.cfg_mgr.save()
        if theme == 'System':
            theme = self.get_system_theme()
        ctk.set_appearance_mode(theme)
        self.update_menu_colors()
        self.update_menu_icons()

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)
        self.cfg['zoom'] = new_scaling
        self.cfg_mgr.save()

    def zoom_in_event(self):
        current_zoom = int(self.zoom_var.get().replace("%", ""))
        if current_zoom < 120:
            new_zoom = current_zoom + 10
            self.change_scaling_event(f"{new_zoom}%")
            self.zoom_var.set(f"{new_zoom}%")

    def zoom_out_event(self):
        current_zoom = int(self.zoom_var.get().replace("%", ""))
        if current_zoom > 80:
            new_zoom = current_zoom - 10
            self.change_scaling_event(f"{new_zoom}%")
            self.zoom_var.set(f"{new_zoom}%")

    def open_file(self):
        files = [('XML File', '*.xml')]
        file = filedialog.askopenfile(initialdir=self.server_path,
                                      filetypes=files, defaultextension=files)
        if file is not None:
            content = file.read()
            self.show(content)

    def save_file(self):
        files = [('XML File', '*.xml')]
        path = filedialog.asksaveasfilename(filetypes=files,
                                            defaultextension=files)
        if path:
            with open(path, "w") as file:
                file.write(self.textbox.get('1.0', END))

    # CONNECTION PARAMETERS METHODS
    def save_params(self):
        if self.address.get() == "" or self.port_select.get() == "" \
           or self.username.get() == "" or self.password.get() == "":
            self.error("Connection parameters cannot be empty!")
            return

        if not self.is_port_valid():
            self.error("Port must be in range 0-65535")
            return

        self.cfg['addr'] = self.address.get()
        self.cfg['port'] = self.port_select.get()
        self.cfg['user'] = self.username.get()
        self.cfg['pass'] = self.password.get()
        self.cfg['ssh-agent'] = self.ssh_agent.get()
        self.cfg_mgr.save()

        self.status("Connection parameters updated.")

    def is_port_valid(self):
        try:
            port_num = int(self.port_select.get())
            if 0 < port_num <= 65535:
                return True
            else:
                return False
        except Exception:
            return False

    def is_empty_connection_parameters(self):
        if self.cfg['addr'] == "" or self.cfg['port'] == "" \
           or self.cfg['user'] == "" or self.cfg['pass'] == "":
            return True
        return False

    def save_interface(self):
        self.cfg['server_iface'] = self.interface_entry.get()
        self.cfg_mgr.save()
        self.restart_file_server()
        self.status("Settings saved and web server restarted.")

    # PROFINET STATUS METHODS
    def _full_path(self, relative_path):
        """Local helper function to get full file path"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    def profinet_cb(self, status):
        xml_path = ""
        if status == "Enable":
            xml_path = self._full_path("enable-profinet.xml")
        else:
            xml_path = self._full_path("disable-profinet.xml")

        with open(xml_path, 'r') as file:
            xml_payload = file.read()
        self.show(xml_payload)

    # GET CONFIGURATION/DATASTORE METHOD
    def get_config_cb(self, config):
        if self.is_empty_connection_parameters():
            self.error("Connection parameters cannot be empty!")
            return

        config = str(config).lower()
        self.status(f"Fetching {config}-config ...")
        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return
            try:
                result = m.get_config(source=config)
                dom = parseString(result.xml)
                self.show(str(dom.toprettyxml()))
            except Exception as err:
                self.error(f"Failed fetching configuration: {err}")
                print(err)

    # Operational method(s)
    def get_oper_cb(self):
        """Show NETCONF get filter for operational data"""
        self.show(RPC_GET_OPER)
        self.rpc("Get operational status", self.execute_get_oper)

    def execute_get_oper(self):
        """Fetch operational data"""
        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return

            rpc = to_ele(self.textbox.get("1.0", END))
            self.show("")
            try:
                response = m.dispatch(rpc, source=None, filter=None)
                dom = parseString(response.xml)
                self.show(str(dom.toprettyxml()))
            except Exception as err:
                self.error(f"Failed fetching operational: {err}")
                print(err)

    # REBOOT METHODS
    def reboot_cb(self):
        self.show(RPC_SYSTEM_RESTART)
        self.rpc("Reboot device", self.execute_reboot)

    def execute_reboot(self):
        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return

            rpc = to_ele(self.textbox.get("1.0", END))
            self.show("")
            try:
                self.status("Please wait while device reboots ...")
                response = m.dispatch(rpc, source=None, filter=None)
                self.show(response)
            except Exception as err:
                self.error(f"Failed reboot: {err}")
                print(err)

    # FACTORY RESET METHODS
    def factory_reset_cb(self):
        self.show(RPC_FACTORY_RESET)
        self.rpc("Perform factory reset", self.execute_factory_reset)

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

    # TIME SETTING METHODS
    def time_set_cb(self):
        self.show(RPC_SET_DATETIME)
        self.rpc("Set system date/time", self.execute_time_set)

    def execute_time_set(self):
        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return

            rpc = to_ele(self.textbox.get("1.0", END))
            self.show("")
            try:
                response = m.dispatch(rpc, source=None, filter=None)
                self.show(response)
            except Exception as err:
                self.error(f"{err}")
                print(err)

    # UPGRADE METHODS
    def upgrade_cb(self):
        self.upgrade_file = filedialog.askopenfilename(
            initialdir=self.server_path,
            title="Select Upgrade Image",
            filetypes=[("Upgrade Package", "*.pkg")])
        if not self.upgrade_file:
            self.error("No upgrade image selected!")
            return

        (_, host_ip) = self.get_iface_ip()
        host_port = self.cfg['server_port']
        pkg = os.path.basename(self.upgrade_file)

        url = f"http://{host_ip}:{host_port}/{pkg}"
        logging.debug(f"Upgrade URL: {url}")

        rpc = f"""<install-bundle xmlns="urn:infix:system:ns:yang:1.0">
    <url>{url}</url>
</install-bundle>
"""
        self.show(rpc)
        self.rpc("Upgrade device", self.start_upgrade)

    def start_upgrade(self):
        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return

            rpc = to_ele(self.textbox.get("1.0", END))
            self.show("")
            try:
                response = m.dispatch(rpc)
                if '<ok/>' in response.xml:
                    self.status("Upgrade started successfully.")
                else:
                    dom = parseString(response.xml)
                    self.show(str(dom.toprettyxml()))
                    raise Exception("Failed starting upgrade!")
            except Exception as err:
                self.error(f"Failed starting upgrade: {err}")
                print(err)

    # NETCONF COMMANDS METHODS
    def execute_netconf_command(self):
        if self.is_empty_connection_parameters():
            self.error("Connection parameters cannot be empty!")
            return

        if self.rpc_cb:
            self.rpc_cb()
            self.rpc_cb = None
            return

        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return
            try:
                send_res = m.edit_config(target='running',
                                         config=self.textbox.get('1.0', END))
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


def parse_args():
    parser = argparse.ArgumentParser(description="Simple NETCONF Client")
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()

def setup_logging(debug_enabled):
    if debug_enabled:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO

    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.debug)

    app = App()
    app.mainloop()
