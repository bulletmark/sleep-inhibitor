## SLEEP-INHIBITOR
[![PyPi](https://img.shields.io/pypi/v/sleep-inhibitor)](https://pypi.org/project/sleep-inhibitor/)
[![AUR](https://img.shields.io/aur/version/sleep-inhibitor)](https://aur.archlinux.org/packages/sleep-inhibitor/)

This is a simple program to inhibit sleep/suspend on
[systemd](https://www.freedesktop.org/wiki/Software/systemd/) based
Linux systems (or on compatible systems running
[elogind](https://github.com/elogind/elogind)). Some examples of the
default plugins provided are:

1. Plugin to inhibit sleep while any audio is playing.

2. Plugin to inhibit sleep while [Plex](https://plex.tv/) media server is serving
   content.

3. Plugin to inhibit sleep while [Jellyfin](https://jellyfin.org/) media server is serving
   content.

4. Plugin to inhibit sleep while a specified process is running. I
   use this to prevent sleep while my home backup is running.

You can also create your own custom plugins. They are extremely trivial
to create as can be seen in the [provided
examples](https://github.com/bulletmark/sleep-inhibitor/tree/master/plugins).
A plugin can be created in shell script or any programming language. It
must simply return an exit code to indicate whether the system should can be
slept/suspended, or not. _Sleep-inhibitor_ runs each plugin at the
period you specify (or the default 5 minutes) and checks the result to
inhibit sleep or not until at least the next check period.

The latest version of this document and code is available at
https://github.com/bulletmark/sleep-inhibitor.

:warning: **Warning**: Unfortunately this program is currently
handicapped due to [this systemd
issue](https://github.com/systemd/systemd/issues/14812). Until this
issue is addressed, your system may not automatically [re-]suspend after
it has been inhibited, even though _sleep-inhibitor_ has removed the
inhibit.

### Motivation

When looking for a solution for this issue I found the
[autosuspend](https://autosuspend.readthedocs.io/en/3.0/index.html)
package but, apart from providing plugins, that package actually
implements the complete sleep, resume, and wakeup logic. I also found
the configuration and documentation confusing. I am happy with and
prefer to use the native sleep systems and I desired a simpler more
lightweight approach that merely provided the ability to inhibit sleep
for some special situations.

1. On Linux desktop systems, I prefer to use the standard GNOME power
   management GUI tools to automatically manage sleep/suspend (via
   systemd). All the major DE's provide similar GUI tools.

2. On Linux server systems, I prefer to use standard
[systemd](https://www.freedesktop.org/wiki/Software/systemd/) power
management to manage sleep/suspend, configured via
[`logind.conf`](https://www.freedesktop.org/software/systemd/man/logind.conf.html)
and
[`sleep.conf`](https://www.freedesktop.org/software/systemd/man/systemd-sleep.conf.html).

These native approaches work well, and are easy to configure.
_Sleep-inhibitor_ assumes you are using the native systemd based sleep
facilities and merely adds the ability to add/create tiny plugins to
inhibit sleep for specified conditions. _Sleep-inhibitor_ uses
[`systemd-inhibit`](https://www.freedesktop.org/software/systemd/man/systemd-inhibit.html)
to execute the sleep inhibition lock.

### Installation

[Arch](https://www.archlinux.org/) users can just install
[_sleep-inhibitor_ from the
AUR](https://aur.archlinux.org/packages/sleep-inhibitor) then skip to
the next Configuration section.

Python 3.6 or later is required. The 3rd party ruamel.yaml package is
also required. Note [_sleep-inhibitor_ is on
PyPI](https://pypi.org/project/sleep-inhibitor/) so just ensure that
`python3-pip` and `python3-wheel` are installed then type the following
to install (or upgrade):

    $ sudo pip3 install -U sleep-inhibitor

If you want to install it yourself from the source repository:

    $ git clone https://github.com/bulletmark/sleep-inhibitor.git
    $ cd sleep-inhibitor
    $ sudo pip3 install -U .

To uninstall:

    $ sudo pip3 uninstall sleep-inhibitor

Some plugins require other software to be installed. E.g. If you use the
[`plex-media-server`](https://github.com/bulletmark/sleep-inhibitor/blob/master/plugins/plex-media-server)
or
[`jellyfin-server`](https://github.com/bulletmark/sleep-inhibitor/blob/master/plugins/jellyfin-server)
plugins then you must install [`curl`](https://curl.se/).

### Configuration

To start, copy the sample
[`sleep-inhibitor.conf`](https://github.com/bulletmark/sleep-inhibitor/blob/master/sleep-inhibitor.conf)
configuration file to `/etc/sleep-inhibitor.conf` and then edit the
sample settings in that target file to add/configure plugins to your
requirements. The instructions and a description of all configuration
options are fully documented in the [sample configuration
file](https://github.com/bulletmark/sleep-inhibitor/blob/master/sleep-inhibitor.conf).

    $ sudo cp /usr/share/sleep-inhibitor/sleep-inhibitor.conf /etc
    $ sudo vim /etc/sleep-inhibitor.conf

### Automatic Startup as systemd Service

If you installed from source or via `pip` then copy the included
[`sleep-inhibitor.service`](https://github.com/bulletmark/sleep-inhibitor/blob/master/sleep-inhibitor.service)
to `/etc/systemd/system/` (note that [Arch](https://www.archlinux.org/)
users who installed from
[AUR](https://aur.archlinux.org/packages/sleep-inhibitor) can skip this
first step):

    $ sudo cp /usr/share/sleep-inhibitor/sleep-inhibitor.service /etc/systemd/system/

Start sleep-indicator and enable it to automatically start at reboot with:

    $ sudo systemctl enable --now sleep-inhibitor

If you change the configuration file then restart with:

    $ sudo systemctl restart sleep-inhibitor

To see status and logs:

    $ systemctl status sleep-inhibitor
    $ journalctl -u sleep-inhibitor

### Plugins

To use the [standard
plugins](https://github.com/bulletmark/sleep-inhibitor/tree/master/plugins)
distributed with this package just specify the plugin name (i.e. the
file name) as the `path` parameter in the [configuration
file](https://github.com/bulletmark/sleep-inhibitor/blob/master/sleep-inhibitor.conf).
To use your own custom plugins, just specify the absolute path to that
plugin. E.g. you can put your custom plugin at `/home/user/bin/myplugin`
and just specify that full path in the [configuration
file](https://github.com/bulletmark/sleep-inhibitor/blob/master/sleep-inhibitor.conf).

A plugin can be any executable script/program which simply returns exit
code 254 to inhibit suspend, or anything else (usually 0 of course) to
not suspend. They can be very trivial to create as the provided [example
plugins](https://github.com/bulletmark/sleep-inhibitor/tree/master/plugins)
demonstrate. A plugin can be created in any language you prefer such as
Shell, Python, Ruby, C/C++, etc.

The plugin does not normally receive any arguments although you can
choose to specify arbitrary arguments to any plugin via the configuration
file, e.g. a sensitive token/password as the example
[`plex-media-server`](https://github.com/bulletmark/sleep-inhibitor/blob/master/plugins/plex-media-server)
plugin requires, or the process name for the example
[`is-process-running`](https://github.com/bulletmark/sleep-inhibitor/blob/master/plugins/is-process-running)
plugin.

### Command Line Usage

```
usage: sleep-inhibitor [-h] [-c CONFIG] [-p PLUGIN_DIR]

Program to run plugins to inhibit system sleep/suspend.

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        alternative configuration file
  -p PLUGIN_DIR, --plugin-dir PLUGIN_DIR
                        alternative plugin dir
```

### License

Copyright (C) 2020 Mark Blakeney. This program is distributed under the
terms of the GNU General Public License. This program is free software:
you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation,
either version 3 of the License, or any later version. This program is
distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License at
<https://www.gnu.org/licenses/> for more details.

<!-- vim: se ai syn=markdown: -->
