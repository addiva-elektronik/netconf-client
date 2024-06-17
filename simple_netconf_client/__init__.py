import os
import sys
import argparse
import logging
import git

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

def generate_version_file():
    r = git.repo.Repo(search_parent_directories=True)
    version_info = r.git.describe('--dirty', '--tags')
    with open(resource_path('version.txt'), 'w') as f:
        f.write(version_info)
        f.write('\n')
        f.close()

def get_version(should_regenerate_version_txt=False):
    try:
        # Deletes current version.txt file
        if os.path.exists(resource_path('version.txt')) and should_regenerate_version_txt:
            os.remove(resource_path('version.txt'))
        
        if not os.path.exists(resource_path('version.txt')) or should_regenerate_version_txt:
            generate_version_file()

        version_file_path = resource_path('version.txt')
        with open(version_file_path) as f:
            return f.readlines()[0].strip()
    except Exception:
        return "0.0.0"