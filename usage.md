Usage
=====

Welcome to the Simple NETCONF Client!  It is a working demonstration
of how to can interact with networked devices with a NETCONF agent.
The application is written in Python with a CustomTkInter GUI and the
ncclient library.

 - <https://github.com/addiva-elektronik/netconf-client>
 - <https://github.com/ncclient/ncclient>

The primary purpose is to demonstrate NETCONF (XML over SSH) and a few
key commands to for basic set up, factory reset, and upgrade.

> **Note:** when run in debug mode the application outputs a lot of
> log messages to the console that can be useful to inspect when you
> debug your own NETCONF application.


Left Hand Pane
--------------

The buttons on the left holds NETCONF commands.  The top ones are RPCs
(remote procedure calls) specific to the device.  There are also
generic NETCONF RPCs, e.g., for fetching the device's current
configuration, the `running-config` and `startup-config`.

At the bottom left is a custom button for enabling and disabling a
PROFINET stack.  The program expects boh `enable-profinet.xml` and
`disable-profinet.xml` to be available.  Here is a generic example
of what could be put into these files, please see your device's
documentation for details:

```xml
<fieldbus xmlns="urn:ietf:params:xml:ns:yang:generic-fieldbus">
  <profinet>
    <enabled>true</enabled>
    <management>br0</management>
  </profinet>
</fieldbus>
<lldp xmlns="urn:ieee:std:802.1AB:yang:ieee802-dot1ab-lldp">
  <enabled xmlns="urn:infix:lldp:ns:yang:1.0">false</enabled>
</lldp>
```

Middle Pane
-----------

The middle of the program is primarily for showing the current command
or its output in XML syntax.   It can also show the documentation.

Clicking one of the buttons in the left-hand pane loads an RPC command
to the text area for inspection and, optionally, edit by the user.

To the left of the Send button is the status bar.  It shows the latest
status or error message of the program.

Example, clicking "Get Status" button loads the RPC command.  When the
Send button is clicked the application tries to connect to the device,
selected on the right-hand side, and send the command.  On success the
resulting device status is shown in the text area.

> **Note:** when using an mDNS name to connect to a device, e.g.,
> switch.local, the name resolution process can take a while during
> which time the application will be unresponsive.


Right Hand Pane
---------------

This is the configuration pane, it consists of two tabs, the default
is for connecting to the device, and the other is for an optional HTTP
server that can be used when asking the device to upgrade itself.

### Connection Parameters

To connect to a NETCONF device you need its address.  This is either a
DNS/mDNS name, e.g., `switch.local`, or an IP address.  Most networked
devices today support mDNS-SD (multicast DNS with service discovery),
and is supported in major operating systems, Windows 10 (build 1709).

The default SSH port for NETCONF (remember, NETCONF is just XML over
an SSH connection) is 830.  For some devices this may differ.

Devices that advertise their services over mDNS-SD, specifically the
`_netconf-ssh._tcp.local` service, can be browsed using the built-in
ZeroConf browser using the "Find Device" button.

To connect you also need a username and password.  The administrator
user for many devices is `admin`, so that comes filled in by default,
but the password you need to fill in yourself.

The last parameter is "Use SSH Agent", which may cause problems for
some users, hence this toggle.  Most users can leave this enabled.

Clicking "Apply & Save" activates the changes and saves them for the
next time the application in started.

### Web Server Settings

The web server (HTTP only) is bundled as a convenience for upgrading
devices.  The example Upgrade System RPC (on the left-hand side) use
the IP address of the selected interface in this view, followed by the
port (default 8080), and the `.pkg` file from the file selector that
pops up when starting Upgrade System.

> **Note:** by default the server is disabled.  To start it, please
> select a directory to act as the root of the web server, and the
> interface connected to the device.

To activate changes, click "Apply & Save".

