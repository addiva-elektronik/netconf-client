# Simple NETCONF Client 

This application is a NETCONF client with a user-friendly UI, built with Python and customtkinter library, for interacting with NETCONF-enabled devices.

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

#### IMPORTANT: Add files named "disable-profinet.xml", "enable-profinet.xml", etc to root folder. These files should contain your Netconf commands.

## Running and Building
Application can be run on Windows, Linux & MacOS.
### Running app
``` 
py ./main.py
```
### Building .exe for Windows
``` 
pyinstaller --onefile --windowed --add-data "disable-profinet.xml:." --add-data "enable-profinet.xml:." main.py
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)