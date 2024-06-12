import os
import socket
import json
import logging
import customtkinter as ctk
from ncclient import manager
from ncclient.transport.errors import AuthenticationError, SSHError

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
            logging.info("Connected to NETCONF server %s.", host)
            return self.manager
        except AuthenticationError as err:
            self.app.error(f"Authentication with {host} failed: {err}")
        except SSHError as err:
            self.app.error(f"SSH connection to {host}:{port} failed: {err}")
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
        self.devices = {}

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            hostname = info.server if info.server else name
            for address in addresses:
                self.devices[name] = (hostname, address, info.port)

            self.app.update_device_list(self.devices)

    def update_service(self, zeroconf, type, name):
        pass

    def remove_service(self, zeroconf, type, name):
        if name in self.devices:
            del self.devices[name]
            self.app.update_device_list(self.devices.values())


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