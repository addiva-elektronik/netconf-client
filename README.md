# Simple NETCONF Client 

This application is a NETCONF client with a user-friendly UI, built with
Python and customtkinter library, for interacting with NETCONF-enabled
devices.

## Cloning

Use git to clone this repository:

```bash
git clone https://github.com/addiva-elektronik/netconf-client.git
```

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install foobar.

```bash
pip install requirments.txt
```

> When done, call `deactivate` to "detach" from the venv.

#### IMPORTANT INFORMATION!

The program has pre-programmed buttons to enable/disable PROFINET.  This
requires two custom files to be added to the root folder:

 - `enable-profinet.xml`
 - `disable-profinet.xml`

These files should contain the NETCONF xml configuration to enable and
disable PROFINET on the target device.

## Running and Building

Application can be run on Windows, Linux & MacOS.

### Running app
``` 
~/src/netconf-client(main)$ python main.py
```

### Building .exe for Windows
``` 
pyinstaller --onefile --windowed --add-data "disable-profinet.xml:." --add-data "enable-profinet.xml:." main.py
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
