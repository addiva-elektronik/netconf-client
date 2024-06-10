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
from tkinter import Menu, END, filedialog, messagebox, Listbox, \
    Toplevel, TclError
from xml.dom.minidom import parseString
from setuptools_scm import get_version
import markdown
import psutil
from zeroconf import ServiceBrowser, Zeroconf
from tkinterweb import HtmlFrame
from PIL import Image, ImageTk
import customtkinter as ctk
from ncclient import manager
from ncclient.transport.errors import AuthenticationError, SSHError
from ncclient.xml_ import to_ele
from lxml.etree import XMLSyntaxError, DocumentInvalid


APP_TITLE = "Simple NETCONF Client"
WELCOME = "Welcome to the NETCONF client!\n\n" \
    "Please use the buttons on the left to initiate commands.\n" \
    "They will show RPC commands in this window and pressing\n" \
    "the Send button will then connect to the device and show\n" \
    "the result here.  The File Open + Save use this window.\n\n" \
    "Connecting details for the device on the right."
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


class AboutDialog(ctk.CTkToplevel):
    def __init__(self, parent, width, height):
        super().__init__(parent)
        self.title("About")
        parent.center_dialog(self, width, height)
        about_message = (
            "Simple NETCONF Client\n"
            f"v{get_version()}\n"
            "\n"
            "Copyright (c) 2024 Ejub Šabić et al.\n"
            "\n"
            "This program is available for free as\n"
            "open source under the MIT license.\n"
        )
        label = ctk.CTkLabel(self, text=about_message)
        label.pack(padx=20, pady=20)
        close_button = ctk.CTkButton(self, text="Close", command=self.destroy)
        close_button.pack(pady=10)
        self.bind("<Control-w>", lambda event: self.destroy())
        self.bind("<Escape>", lambda event: self.destroy())

class LicenseDialog(ctk.CTkToplevel):
    def __init__(self, parent, width, height):
        super().__init__(parent)
        self.title("License")
        parent.center_dialog(self, width, height)
        license_message = (
            "MIT License\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the 'Software'), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n\n"
            "The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n\n"
            "THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."
        )
        label = ctk.CTkLabel(self, text=license_message, wraplength=580)
        label.pack(padx=20, pady=20)
        close_button = ctk.CTkButton(self, text="Close", command=self.destroy)
        close_button.pack(pady=10)
        self.bind("<Control-w>", lambda event: self.destroy())
        self.bind("<Escape>", lambda event: self.destroy())


class UsageDialog(ctk.CTkToplevel):
    def __init__(self, parent, content, width=800, height=600):
        super().__init__(parent)
        self.parent = parent

        self.title("Usage")
        parent.center_dialog(self, width, height)

        # Initialize history tracking
        self.history = []
        self.history_index = -1

        # Apply dark mode CSS if needed
        css = """
        body { font-family: Arial, sans-serif; }
        pre { background-color: #2e2e2e; color: #f8f8f2; padding: 10px; }
        code { background-color: #2e2e2e; color: #f8f8f2; }
        body { background-color: #1e1e1e; color: #f8f8f2; }
        a { color: #1e90ff; text-decoration: underline; }
        blockquote { border-left: 4px solid #1e90ff; padding-left: 10px; margin-left: 0; color: #888; }
        """ if ctk.get_appearance_mode() == "Dark" else """
        body { font-family: Arial, sans-serif; }
        pre { background-color: #f8f8f2; color: #2e2e2e; padding: 10px; }
        code { background-color: #f8f8f2; color: #2e2e2e; }
        body { background-color: #ffffff; color: #000000; }
        a { color: #0000ff; text-decoration: underline; }
        blockquote { border-left: 4px solid #0000ff; padding-left: 10px; margin-left: 0; color: #555; }
        """

        self.html_content = f"""
        <html>
        <head>
            <style>{css}</style>
        </head>
        <body>
            {markdown.markdown(content, extensions=['fenced_code', 'codehilite', 'extra'])}
        </body>
        </html>
        """

        self.html_frame = HtmlFrame(self, horizontal_scrollbar="auto", messages_enabled=False)
        self.html_frame.load_html(self.html_content)
        self.html_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Back and Forward buttons
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(fill="x", padx=10, pady=5)

        self.back_button = ctk.CTkButton(self.button_frame, text="Back", command=self.go_back)
        self.back_button.pack(side="left", padx=5)
        self.back_button.configure(state="disabled")

        self.forward_button = ctk.CTkButton(self.button_frame, text="Forward", command=self.go_forward)
        self.forward_button.pack(side="left", padx=5)
        self.forward_button.configure(state="disabled")

        self.close_button = ctk.CTkButton(self.button_frame, text="Close", command=self.destroy)
        self.close_button.pack(side="right", pady=10)

        # Add initial content to history
        self.add_to_history(self.html_content, is_url=False)

        # Hook into link loader
        self.html_frame.on_link_click(self.load_html_content)

        # Bind mouse back/forward buttons
        #self.bind("<Button-8>", self.on_back_button)
        #self.bind("<Button-9>", self.on_forward_button)

        self.html_frame.bind_all("<Alt-Left>", self.on_back_button)
        self.html_frame.bind_all("<Alt-Right>", self.on_forward_button)

        # Bind key events for scrolling and closing
        self.html_frame.bind_all("<Up>", lambda e: self.html_frame.yview_scroll(-5, "units"))
        self.html_frame.bind_all("<Down>", lambda e: self.html_frame.yview_scroll(5, "units"))
        self.html_frame.bind_all("<Prior>", lambda e: self.html_frame.yview_scroll(-1, "pages"))
        self.html_frame.bind_all("<Next>", lambda e: self.html_frame.yview_scroll(1, "pages"))
        self.html_frame.bind_all("<Home>", lambda e: self.html_frame.yview_moveto(0))
        self.html_frame.bind_all("<End>", lambda e: self.html_frame.yview_moveto(1))
        self.html_frame.bind("<Control-w>", lambda event: self.destroy())
        self.html_frame.bind("<Escape>", lambda event: self.destroy())

        # Bind right-click on links to copy URL
        self.html_frame.bind("<Button-3>", self.on_right_click)

        self.html_frame.focus_set()
        self.html_frame.focus_force()

    def add_to_history(self, content, is_url):
        if self.history_index == -1 or (self.history and self.history[self.history_index] != content):
            self.history = self.history[:self.history_index + 1]
            self.history.append((content, is_url))
            self.history_index += 1

        self.update_navigation_buttons()

    def load_html_content(self, content):
        if content.startswith("http://") or content.startswith("https://"):
            self.html_frame.load_url(content)
            self.add_to_history(content, is_url=True)
        else:
            self.html_frame.load_html(content)
            self.add_to_history(content, is_url=False)

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            content, is_url = self.history[self.history_index]
            if is_url:
                self.html_frame.load_url(content)
            else:
                self.html_frame.load_html(content)
        self.update_navigation_buttons()

    def go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            content, is_url = self.history[self.history_index]
            if is_url:
                self.html_frame.load_url(content)
            else:
                self.html_frame.load_html(content)
        self.update_navigation_buttons()

    def update_navigation_buttons(self):
        self.back_button.configure(state="normal" if self.history_index > 0 else "disabled")
        self.forward_button.configure(state="normal" if self.history_index < len(self.history) - 1 else "disabled")

    def on_back_button(self, event):
        self.go_back()

    def on_forward_button(self, event):
        self.go_forward()

    def on_right_click(self, event):
        url = self.html_frame.get_current_link(resolve=True)
        if url:
            self.clipboard_clear()
            self.clipboard_append(url)
            self.parent.status(f"copied {url} to clipboard.")


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
            'server_enabled': False,
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
            logging.info(f"Connected to NETCONF server {host}.")
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
            logging.info("Disconnected from NETCONF server")


class ZeroconfListener:
    def __init__(self, app):
        self.app = app
        self.devices = []

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            hostname = info.server if info.server else name
            for address in addresses:
                self.devices.append((hostname, address, info.port))
            self.app.update_device_list(self.devices)

    def update_service(self, zeroconf, type, name):
        pass

    def remove_service(self, zeroconf, type, name):
        pass


class ScanResultsDialog(ctk.CTkToplevel):
    def __init__(self, parent, devices):
        super().__init__(parent)
        self.title("Scan Results")
        self.geometry("400x300")
        self.devices = devices
        self.selected_device = None

        self.listbox = Listbox(self)
        self.listbox.pack(fill="both", expand=True, padx=10, pady=10)
        for name, ip, port in self.devices:
            name = name.rstrip('.')
            self.listbox.insert('end', f"{name} - {ip}:{port}")

        self.cancel_button = ctk.CTkButton(self, text="Cancel", command=self.on_cancel)
        self.cancel_button.pack(side="left", padx=10, pady=10)

        self.ok_button = ctk.CTkButton(self, text="OK", command=self.on_ok)
        self.ok_button.pack(side="right", padx=10, pady=10)

    def on_ok(self):
        selection = self.listbox.curselection()
        if selection:
            self.selected_device = self.devices[selection[0]]
        self.destroy()

    def on_cancel(self):
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        self.cfg_mgr = ConfigManager()
        self.cfg = self.cfg_mgr.cfg
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(f"{1100}x{640}")
        self.minsize(800, 640)  # Handle shrinking app window on zoom in/out

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
        self.help_menu = Menu(self.menubar, tearoff=0)

        self.settings_menu.add_radiobutton(label="System", variable=self.theme_var,
                                           command=lambda: self.change_theme_mode_event("System"))
        self.settings_menu.add_radiobutton(label="Light", variable=self.theme_var,
                                           command=lambda: self.change_theme_mode_event("Light"))
        self.settings_menu.add_radiobutton(label="Dark", variable=self.theme_var,
                                           command=lambda: self.change_theme_mode_event("Dark"))

        self.settings_menu.add_separator()

        self.settings_menu.add_command(label="Zoom In", accelerator="Ctrl++",
                                       command=self.zoom_in_event)
        self.settings_menu.add_command(label="Zoom Out", accelerator="Ctrl+-",
                                       command=self.zoom_out_event)
        self.settings_menu.add_command(label="Reset Zoom", accelerator="Ctrl+0",
                                       command=self.reset_zoom_event)

        self.file_menu.add_command(label="Open", underline=0,
                                   accelerator="Ctrl+O",
                                   command=self.open_file,
                                   image=self.load_icon, compound="left")
        self.file_menu.add_command(label="Save", underline=0,
                                   accelerator="Ctrl+S",
                                   command=self.save_file,
                                   image=self.save_icon, compound="left")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", underline=0,
                                   accelerator="Ctrl+Q",
                                   command=self.quit,
                                   image=self.exit_icon, compound="left")

        self.help_menu.add_command(label="Usage", underline=0,
                                   accelerator="Ctrl+H",
                                   command=self.show_usage,
                                   image=self.transparent_icon,
                                   compound="left")
        self.help_menu.add_command(label="License", command=self.show_license,
                                   image=self.transparent_icon,
                                   compound="left")
        self.help_menu.add_command(label="About", command=self.show_about,
                                   image=self.transparent_icon,
                                   compound="left")

        self.menubar.add_cascade(label="File", underline=0, menu=self.file_menu)
        self.menubar.add_cascade(label="Settings", underline=0, menu=self.settings_menu)
        self.menubar.add_cascade(label="Help", underline=0, menu=self.help_menu)

        self.update_menu_icons()

        # left sidebar with netconf RPCs ######################################
        self.sidebar_frame = ctk.CTkFrame(self, width=100, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=8, sticky="nsew")

        self.logo = ctk.CTkLabel(self.sidebar_frame, text="NETCONF Client",
                                 font=ctk.CTkFont(size=20, weight="bold"))
        self.logo.grid(row=0, column=0, padx=0, pady=(10, 10))

        self.factory_reset = ctk.CTkButton(self.sidebar_frame,
                                           command=self.factory_reset_cb,
                                           text="Factory Reset")
        self.factory_reset.grid(row=1, column=0, padx=10, pady=10)

        self.reboot = ctk.CTkButton(self.sidebar_frame,
                                    command=self.reboot_cb,
                                    text="Reboot")
        self.reboot.grid(row=2, column=0, padx=10, pady=10)

        self.time_set = ctk.CTkButton(self.sidebar_frame,
                                      command=self.time_set_cb,
                                      text="Set System Time")
        self.time_set.grid(row=3, column=0, padx=10, pady=10)

        self.upgrade_file = None
        self.upgrade_button = ctk.CTkButton(self.sidebar_frame,
                                            command=self.upgrade_cb,
                                            text="Upgrade System")
        self.upgrade_button.grid(row=4, column=0, padx=10, pady=10)

        self.get_oper = ctk.CTkButton(self.sidebar_frame,
                                      command=self.get_oper_cb,
                                      text="Get Status")
        self.get_oper.grid(row=5, column=0, padx=10, pady=10)

        self.get_config_label = ctk.CTkLabel(self.sidebar_frame,
                                             text="Get configuration",
                                             anchor="w")
        self.get_config_label.grid(row=6, column=0, padx=10, pady=(10, 0))
        self.get_config_button = ctk.CTkOptionMenu(self.sidebar_frame,
                                                   command=self.get_config_cb,
                                                   values=["Running",
                                                           "Startup"])
        self.get_config_button.grid(row=7, column=0, padx=10, pady=0)

        self.cp = ctk.CTkFrame(self.sidebar_frame,
                               fg_color=self.sidebar_frame.cget("fg_color"))
        self.cp.grid(row=8, column=0, pady=0, padx=0, sticky="ew")

        self.get_config_label = ctk.CTkLabel(self.cp,
                                             text="Put configuration",
                                             anchor="w")
        self.get_config_label.grid(row=0, column=0, columnspan=2,
                                   padx=10, pady=(10, 0))

        self.target = "running"
        self.put_config = ctk.CTkOptionMenu(self.cp,
                                            command=self.put_config_cb,
                                            width=98,
                                            values=["Running",
                                                    "Startup"])
        self.put_config.grid(row=1, column=0, padx=(16, 0), pady=10, sticky="w")

        self.save = ctk.CTkButton(self.cp, width=30,
                                  command=self.copy_config,
                                  text="Save")
        self.save.grid(row=1, column=1, padx=(0, 15), pady=10, sticky="w")

        self.profinet_label = ctk.CTkLabel(self.sidebar_frame,
                                           text="PROFINET Configuration",
                                           anchor="w")
        self.profinet_label.grid(row=10, column=0, padx=10, pady=(10, 0))
        self.profinet_button = ctk.CTkOptionMenu(self.sidebar_frame,
                                                 command=self.profinet_cb,
                                                 values=["Enable",
                                                         "Disable"])
        self.profinet_button.grid(row=11, column=0, padx=10, pady=0)

        # main XML textbox ####################################################
        self.textbox = ctk.CTkTextbox(self, width=250, font=("Courier", 13), undo=True)
        self.textbox.grid(row=0, column=1, columnspan=2, rowspan=3,
                          padx=(10, 0), pady=(18, 0), sticky="nsew")

        self.textbox.bind("<Control-z>", lambda event: self.undo())
        self.textbox.bind("<Control-Z>", lambda event: self.undo()) # Linux
        self.textbox.bind("<Control-y>", lambda event: self.redo())
        self.textbox.bind("<Control-Y>", lambda event: self.redo()) # Linux
        self.textbox.bind("<Control-a>", lambda event: self.select_all())
        self.textbox.bind("<Control-A>", lambda event: self.select_all()) # Linux

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

        self.entries = {}

        self.device_frame = ctk.CTkFrame(self.conn_param_frame)
        self.device_frame.grid(row=2, column=0, columnspan=2,
                               pady=0, padx=5, sticky="ew")

        self.user_label = ctk.CTkLabel(self.device_frame,
                                       text="Device Address",
                                       font=("Arial", 8))
        self.user_label.grid(row=0, column=0, pady=0, padx=10, sticky="w")

        self.address = ctk.CTkEntry(self.device_frame, width=198)
        self.address.grid(row=1, column=0, pady=0, padx=10, sticky="ew")
        self.entries['addr'] = self.address

        self.user_label = ctk.CTkLabel(self.device_frame,
                                       text="Port",
                                       font=("Arial", 8))
        self.user_label.grid(row=2, column=0, pady=0, padx=10, sticky="w")

        self.port_select = ctk.CTkEntry(self.device_frame, width=198)
        self.port_select.grid(row=3, column=0, pady=(0, 10), padx=10, sticky="ew")
        self.entries['port'] = self.port_select

        self.scan_button = ctk.CTkButton(self.device_frame, text="Find Device",
                                         width=198,
                                         command=self.scan_devices)
        self.scan_button.grid(row=4, column=0, columnspan=2,
                              pady=(0, 10), padx=10, sticky="ew")

        self.creds_frame = ctk.CTkFrame(self.conn_param_frame)
        self.creds_frame.grid(row=3, column=0,
                              pady=10, padx=5, sticky="ew")

        self.user_label = ctk.CTkLabel(self.creds_frame, text="Username", font=("Arial", 8))
        self.user_label.grid(row=0, column=0, pady=0, padx=10, sticky="w")

        self.username = ctk.CTkEntry(self.creds_frame, width=198)
        self.username.grid(row=1, column=0, pady=0, padx=10, sticky="ew")
        self.entries['user'] = self.username

        self.pass_label = ctk.CTkLabel(self.creds_frame, text="Password", font=("Arial", 8))
        self.pass_label.grid(row=2, column=0, pady=0, padx=10, sticky="w")

        self.password = ctk.CTkEntry(self.creds_frame, width=198, show='*')
        self.password.grid(row=3, column=0, pady=(0, 10), padx=10, sticky="ew")
        self.entries['pass'] = self.password

        if self.cfg['addr']:
            self.entries['addr'].insert(0, self.cfg['addr'])
        if self.cfg['port']:
            self.entries['port'].insert(0, str(self.cfg['port']))
        if self.cfg['user']:
            self.entries['user'].insert(0, self.cfg['user'])
        if self.cfg['pass']:
            self.entries['pass'].insert(0, self.cfg['pass'])

        self.ssh_agent = ctk.CTkSwitch(self.conn_param_frame, text="Use SSH Agent")
        self.ssh_agent.grid(row=5, column=0, pady=10, padx=10, sticky="n")
        if self.cfg['ssh-agent']:
            self.ssh_agent.select()

        self.save_button = ctk.CTkButton(self.conn_param_frame, width=218,
                                         text="Apply & Save",
                                         command=self.save_params)
        self.save_button.grid(row=6, column=0, pady=5, padx=5, sticky="ew")

        # Web Server Settings tab
        self.web_server_frame = ctk.CTkFrame(self.tabview.tab("Web Server"))
        self.web_server_frame.pack(fill="both", expand=True)

        self.web_server_label = ctk.CTkLabel(self.web_server_frame,
                                             text="Web Server Settings",
                                             font=("Arial", 16))
        self.web_server_label.grid(row=0, column=0, columnspan=2,
                                   padx=10, pady=10, sticky="")

        self.server_frame = ctk.CTkFrame(self.web_server_frame)
        self.server_frame.grid(row=2, column=0, pady=0, padx=5, sticky="ew")
        self.server_frame.grid_columnconfigure(0, weight=0)
        self.server_frame.grid_columnconfigure(1, weight=1)

        self.server_label = ctk.CTkLabel(self.server_frame,
                                         text="Server Interface (Address)",
                                         font=("Arial", 8))
        self.server_label.grid(row=0, column=0, pady=0, padx=10, sticky="w")
        self.interface_var = tk.StringVar()
        self.interface_menu = ctk.CTkOptionMenu(self.server_frame,
                                                variable=self.interface_var)
        self.interface_menu.grid(row=1, column=0, pady=(0, 5), padx=10, sticky="ew")
        self.update_interface_menu()

        self.port_label = ctk.CTkLabel(self.server_frame, text="Server Port",
                                       font=("Arial", 8))
        self.port_label.grid(row=2, column=0, pady=0, padx=10, sticky="w")
        self.server_port_entry = ctk.CTkEntry(self.server_frame)
        self.server_port_entry.insert(0, str(self.cfg['server_port']))
        self.server_port_entry.grid(row=3, column=0, pady=(0, 5), padx=10, sticky="ew")

        self.dir_frame = ctk.CTkFrame(self.server_frame, fg_color=self.server_frame.cget("fg_color"))
        self.dir_frame.grid(row=4, column=0, pady=0, padx=0, sticky="ew")

        self.dir_label = ctk.CTkLabel(self.dir_frame,
                                      text="Server Directory",
                                      font=("Arial", 8))
        self.dir_label.grid(row=0, column=0, pady=0, padx=10, sticky="w")

        self.server_path_entry = ctk.CTkEntry(self.dir_frame, width=180)
        self.server_path_entry.insert(0, self.cfg['server_path'])
        self.server_path_entry.grid(row=1, column=0, pady=(0, 5),
                                    padx=(10, 0), sticky="w")

        self.dir_button = ctk.CTkButton(self.dir_frame,
                                        text="..", width=20,
                                        command=self.select_directory)
        self.dir_button.grid(row=1, column=1, pady=(0, 5), padx=(3, 5), sticky="w")

        if self.cfg['server_path']:
            self.server_path = self.cfg['server_path']

        self.server_enabled = ctk.CTkSwitch(self.server_frame, text="Server Enabled")
        self.server_enabled.grid(row=6, column=0, pady=(0, 10), padx=10, sticky="n")
        if self.cfg['server_enabled']:
            self.server_enabled.select()

        # Save button
        self.interface_save_button = ctk.CTkButton(self.web_server_frame,
                                                   text="Apply & Save",
                                                   command=self.save_server_settings)
        self.interface_save_button.grid(row=5, column=0, pady=20, padx=10, sticky="ew")

        # Check if theme is set to "System", otherwise use saved theme
        self.change_theme_mode_event(self.cfg['theme'])
        self.change_scaling_event(f"{self.cfg['zoom']}")

        # set default values
        self.rpc_cb = None
        self.textbox.delete(0.0, 'end')
        self.textbox.insert("0.0", WELCOME)

        self.bind("<Control-plus>", lambda event: self.zoom_in_event())
        self.bind("<Control-minus>", lambda event: self.zoom_out_event())
        self.bind("<Control-0>", lambda event: self.reset_zoom_event())
        self.bind("<Control-o>", lambda event: self.open_file())
        self.bind("<Control-s>", lambda event: self.save_file())
        self.bind("<Control-q>", lambda event: self.quit())
        self.bind("<Control-h>", lambda event: self.show_usage())

        self.focus_set()

        # Start the web server if enabled in a previous run.
        self.start_file_server()

    def scan_devices(self):
        # Initialize Zeroconf and start scanning for _netconf-ssh._tcp devices
        self.zeroconf = Zeroconf()
        self.listener = ZeroconfListener(self)
        self.browser = ServiceBrowser(self.zeroconf, "_netconf-ssh._tcp.local.", self.listener)
        self.status("Scanning for devices...")

    def update_device_list(self, devices):
        # Create a dialog to show the list of devices
        dialog = ScanResultsDialog(self, devices)
        self.wait_window(dialog)
        if dialog.selected_device:
            name, ip, port = dialog.selected_device
            name = name.rstrip('.')
            self.cfg['addr'] = ip
            self.cfg['port'] = port
            self.entries['addr'].delete(0, 'end')
            self.entries['addr'].insert(0, ip)
            self.entries['port'].delete(0, 'end')
            self.entries['port'].insert(0, str(port))
            self.status(f"using {name} ({ip}:{port})")
        else:
            self.status("canceled.")

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
    def undo(self):
        try:
            self.textbox.edit_undo()
        except TclError:
            pass  # Ignore the error if there's nothing to undo

    def redo(self):
        try:
            self.textbox.edit_redo()
        except TclError:
            pass  # Ignore the error if there's nothing to redo

    def select_all(self):
        self.textbox.tag_add("sel", "1.0", "end")
        return 'break'  # Prevent default behavior

    def load_icons(self):
        self.icon_images = {
            'save': Image.open("icons/save.png"),
            'load': Image.open("icons/open.png"),
            'exit': Image.open("icons/close.png"),
            'tran': Image.open("icons/transparent.png")
        }
        self.icons = {
            'save': ImageTk.PhotoImage(self.icon_images['save']),
            'load': ImageTk.PhotoImage(self.icon_images['load']),
            'exit': ImageTk.PhotoImage(self.icon_images['exit']),
            'tran': ImageTk.PhotoImage(self.icon_images['tran'])
        }
        self.load_icon = self.icons['load']
        self.save_icon = self.icons['save']
        self.exit_icon = self.icons['exit']
        self.transparent_icon = self.icons['tran']

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

    def center_dialog(self, dialog, width, height):
        """Utility method to center the dialogs"""
        dialog_width = width
        dialog_height = height

        # Calculate the position to center the dialog over the main application window
        main_x = self.winfo_rootx()
        main_y = self.winfo_rooty()
        main_width = self.winfo_width()
        main_height = self.winfo_height()

        position_right = int(main_x + (main_width - dialog_width) / 2)
        position_down = int(main_y + (main_height - dialog_height) / 2)

        # Set the geometry of the dialog to center it on the main application window
        dialog.geometry(f"{dialog_width}x{dialog_height}+{position_right}+{position_down}")

    def _update_status(self, message, error=False):
        if error:
            self.status_label.configure(text=f"Error: {message}",
                                        text_color=("#FF0000", "#FF4C4C"))
            logging.error(message)
        else:
            self.status_label.configure(text=message,
                                        text_color=("#000000", "#FFFFFF"))
            logging.info(message)
        # Update GUI even if we run in an callback
        self.update_idletasks()

    def rpc(self, message, method):
        self._update_status(f"RPC: {message}", error=False)
        self.rpc_cb = method

    def status(self, message):
        self._update_status(f"Status: {message}", error=False)

    def error(self, message):
        self._update_status(message, error=True)

    def clear(self):
        self.textbox.delete(0.0, 'end')

    def show(self, text):
        self.clear()
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

    def reset_zoom_event(self):
        self.change_scaling_event("100%")
        self.zoom_var.set("100%")

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

    def show_about(self):
        AboutDialog(self, 320, 260)

    def show_license(self):
        LicenseDialog(self, 720, 450)

    def show_usage(self):
        fn = self._full_path("usage.md")
        try:
            with open(fn, "r") as file:
                content = file.read()
                UsageDialog(self, content, 800, 700)
        except FileNotFoundError:
            self.error(f"file {fn} not found.")


    def show_html_dialog(self, title, html_content):
        dialog = Toplevel(self)
        dialog.title(title)

        # Set the desired size of the dialog
        dialog_width = 800
        dialog_height = 600

        # Calculate the position to center the dialog over the main application window
        main_x = self.winfo_rootx()
        main_y = self.winfo_rooty()
        main_width = self.winfo_width()
        main_height = self.winfo_height()

        position_right = int(main_x + (main_width - dialog_width) / 2)
        position_down = int(main_y + (main_height - dialog_height) / 2)

        # Set the geometry of the dialog to center it on the main application window
        dialog.geometry(f"{dialog_width}x{dialog_height}+{position_right}+{position_down}")

        html_frame = HtmlFrame(dialog, horizontal_scrollbar="auto", messages_enabled = False)
        html_frame.load_html(html_content)
        html_frame.pack(fill="both", expand=True, padx=10, pady=10)

        close_button = ctk.CTkButton(dialog, text="Close", command=dialog.destroy)
        close_button.pack(pady=10)

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
        try:
            with open(xml_path, 'r') as file:
                xml_payload = file.read()
            self.show(xml_payload)
        except FileNotFoundError:
            self.error(f"file {xml_path} not found!")

    # Get configuration/datastore method(s)
    def extract_xml_data(self, xml_string):
        try:
            dom = parseString(xml_string)
            data_element = dom.getElementsByTagName("data")[0]
            # Create a new DOM document to pretty print the inner content
            pretty_dom = parseString(data_element.toxml())
            pretty_xml = pretty_dom.toprettyxml(indent="    ")  # 4 spaces

            # Remove the XML declaration and <data> tags
            lines = pretty_xml.split("\n")[2:-2]

            # Remove leading indentation
            min_indent = float('inf')
            for line in lines:
                stripped_line = line.lstrip()
                if stripped_line:
                    indent = len(line) - len(stripped_line)
                    min_indent = min(min_indent, indent)
            lines = [line[min_indent:] if line.strip() else line for line in lines]

            inner_xml = "\n".join(lines)
            return inner_xml
        except Exception as e:
            self.error(f"Error extracting data from XML: {e}")
            return None

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
                response = m.get_config(source=config)
                data = self.extract_xml_data(response.xml)
                self.show(data)
                self.status(f"showing {config}-config.")
            except Exception as err:
                self.error(f"Failed fetching configuration: {err}")
                print(err)

    def put_config_cb(self, config):
        config = str(config).lower()
        fn = filedialog.askopenfilename(
            title="Select config file",
            filetypes=[("XML files", "*.xml")]
        )
        if fn:
            try:
                with open(fn, 'r') as file:
                    data = file.read()
                self.show(data)
                self.target = config
                self.rpc(f"Copy (backup) file to {config}-config",
                         self.execute_put_config)
            except Exception as e:
                self.error(f"Failed to load config file {fn}: {e}")

    def execute_put_config(self):
        self.status(f"Restoring {self.target} configuration, please wait ...")

        # Wrap the extracted data in the required XML framing
        config_data = f"""
        <nc:config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
            {self.textbox.get("1.0", END)}
        </nc:config>
        """
        self.clear()

        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return

            try:
                m.edit_config(target=self.target, config=config_data)
                self.status(f"Configuration saved to {self.target}-config!")
            except Exception as err:
                self.error(f"Failed to save {self.target}-config: {err}")
                print(err)

    def copy_config(self):
        self.clear()
        self.status("Calling 'copy running-config startup-config', please wait ...")
        with NetconfConnection(self.cfg, self) as m:
            if m is None:
                return
            try:
                # Copy running configuration to startup configuration
                m.copy_config(source='running', target='startup')
                self.status("running configuration saved to startup.")
            except Exception as err:
                self.error(f"Failed to save configuration: {err}")
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
                data = self.extract_xml_data(response.xml)
                self.show(data)
                self.status("showing (filtered) operational datastore.")
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
                self.status("done.")
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
                self.status("done.")
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
                self.status("done.")
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
                # Generic RPC composed manually
                try:
                    rpc = to_ele(self.textbox.get('1.0', END))
                except XMLSyntaxError as err:
                    self.error(f"XML Syntax Error: {err}")
                    return
                except DocumentInvalid as err:
                    self.error(f"Document Invalid: {err}")
                    return
                except TypeError as err:
                    self.error(f"Type Error: {err}")
                    return

                response = m.dispatch(rpc, source=None, filter=None)
                if response.ok:
                    data = self.extract_xml_data(response.xml)
                    self.show(data)
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
