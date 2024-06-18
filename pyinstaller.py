import os
import PyInstaller.__main__
import simple_netconf_client

if __name__ == '__main__':
    simple_netconf_client.get_version(should_regenerate_version_txt=True)
    # Builds production version (no debug console window)
    PyInstaller.__main__.run([
        'main.spec'
    ])  