import os
import sys
import argparse
import logging
from importlib.metadata import version, PackageNotFoundError


try:
    __version__ = version("netconf-client")
except PackageNotFoundError:
    # package is not installed
    __version__ = "0.0.0"

def get_version():
    return __version__

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

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
