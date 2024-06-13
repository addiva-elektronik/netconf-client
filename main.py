"""
Simple (and portable) NETCONF client

Copyright (c) 2024 Ejub Šabić <ejub1946@outlook.com>
"""
import sys
import signal
import customtkinter as ctk
from simple_netconf_client.gui.SimpleNetconfClient import SimpleNetconfClient
from simple_netconf_client import parse_args, setup_logging

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

if __name__ == "__main__":
    def signal_handler(sig, _):
        print(f"Caught signal {sig}, exiting.")
        app.quit()
        sys.exit(0)

    args = parse_args()
    setup_logging(args.debug)

    signal.signal(signal.SIGINT, signal_handler)

    app = SimpleNetconfClient()
    app.mainloop()
