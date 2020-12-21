#!/usr/bin/python3
'Program to run plugins to inhibit system sleep/suspend.'
# Requires python 3.6+
# Mark Blakeney, Jul 2020.

# Standard packages
import sys
import argparse
import subprocess
import threading
import time
import shlex
from pathlib import Path

# Return code which indicates plugin wants to inhibit suspend
SUSP_CODE = 254

# Default check period in minutes if not specified for plugin in config
DEF_PERIOD = 5

# On some non-systemd systems, systemd-inhibit emulators are used
# instead. The first found below is the one we use:
SYSTEMD_SLEEP_PROGS = (
    'elogind-inhibit',
    'systemd-inhibit',
)

class Plugin:
    'Class to manage each plugin'
    loglock = threading.Lock()
    threads = []

    def __init__(self, index, prog, conf, plugin_dir, inhibitor_prog):
        'Constructor'
        pathstr = conf.get('path')
        if not pathstr:
            sys.exit(f'Plugin #{index}: path must be defined')

        path = Path(pathstr)
        name = conf.get('name', path.name)
        self.name = f'Plugin {name}'

        if not path.is_absolute():
            if not plugin_dir:
                sys.exit(f'{self.name}: path "{path}" is relative but '
                        'could not determine distribution plugin dir')

            path = plugin_dir / path

        path = path.resolve()
        if not path.exists():
            sys.exit(f'{self.name}: "{path}" does not exist')

        period = float(conf.get('period', DEF_PERIOD))
        self.period = period * 60
        self.is_inhibiting = None

        cmd = str(path)
        args = conf.get('args')
        if args:
            cmd += f' {args}'

        # The normal periodic check command
        self.cmd = shlex.split(cmd)

        whatval = conf.get('what')
        what = f' --what="{whatval}"' if whatval else ''

        # While inhibiting, we run outself again via systemd-inhibit to
        # run the plugin in a loop which keeps the inhibit on while the
        # inhibit state is returned.
        self.icmd = shlex.split(f'{inhibitor_prog}{what} --who="{prog.name}" '
                f'--why="{self.name}" {prog} -s {self.period} -i "{cmd}"')

        print(f'{self.name} [{path}] configured @ {period} minutes')

        # Each plugin periodic check runs in it's own thread
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()
        self.threads.append(thread)

    def run(self):
        'Worker function which runs it its own thread'
        while True:
            res = subprocess.run(self.cmd)
            while res.returncode == SUSP_CODE:
                if not self.is_inhibiting:
                    self.is_inhibiting = True
                    self.log(f'{self.name} is inhibiting '
                            f'suspend (return={res.returncode})')

                res = subprocess.run(self.icmd)

            if not (self.is_inhibiting is False):
                self.is_inhibiting = False
                self.log(f'{self.name} is not inhibiting '
                        f'suspend (return={res.returncode})')

            time.sleep(self.period)

    @classmethod
    def log(cls, msg):
        'Thread locked print()'
        if not msg.endswith('\n'):
            msg += '\n'

        # Use a lock so thread messages do not get interleaved
        with cls.loglock:
            sys.stdout.write(msg)

def init():
    'Program initialisation'
    # Process command line options
    opt = argparse.ArgumentParser(description=__doc__.strip())
    opt.add_argument('-c', '--config',
            help='alternative configuration file')
    opt.add_argument('-p', '--plugin-dir',
            help='alternative plugin dir')
    opt.add_argument('-s', '--sleep', type=float, help=argparse.SUPPRESS)
    opt.add_argument('-i', '--inhibit', help=argparse.SUPPRESS)
    args = opt.parse_args()

    # This instance may be a child invocation merely to run and check
    # the plugin while it is inhibiting.
    if args.inhibit:
        cmd = shlex.split(args.inhibit)
        while True:
            time.sleep(args.sleep)
            res = subprocess.run(cmd)
            if res.returncode != SUSP_CODE:
                sys.exit(res.returncode)

    prog = Path(sys.argv[0]).resolve()

    # Work out what sleep inhibitor program to use
    inhibitor_prog = None
    for iprog in SYSTEMD_SLEEP_PROGS:
        try:
            res = subprocess.run(f'{iprog} --version'.split(),
                    check=True, universal_newlines=True,
                    stderr=subprocess.DEVNULL, stdout=subprocess.PIPE)
        except Exception:
            continue

        vers = res.stdout.split('\n')[0].strip()
        print(f'{prog.name} using {iprog}, {vers}')
        inhibitor_prog = iprog

    if not inhibitor_prog:
        opts = ' or '.join(SYSTEMD_SLEEP_PROGS)
        sys.exit(f'No systemd-inhibitor app installed from one of {opts}.')

    # Work out plugin and base dirs for this installation
    for bdir in (f'/usr/share/{prog.name}', f'/usr/local/share/{prog.name}'):
        plugin_dir = Path(bdir) / 'plugins'
        if plugin_dir.exists():
            base_dir = plugin_dir.parent
            break
    else:
        plugin_dir = None
        base_dir = None

    # Determine config file path
    cname = prog.name + '.conf'
    cfile = Path(args.config).expanduser() if args.config else \
            Path(f'/etc/{cname}')

    if not cfile.exists():
        print(f'{prog.name} configuration file {cfile} does not exist.',
                file=sys.stderr)
        if base_dir and not args.config:
            print(f'Copy {base_dir}/{cname} to /etc and edit appropriately.',
                    file=sys.stderr)
        sys.exit()

    from ruamel.yaml import YAML
    conf = YAML(typ='safe').load(cfile)

    plugins = conf.get('plugins')
    if not plugins:
        sys.exit('No plugins configured')

    # Work out plugin dir
    plugin_dir = args.plugin_dir or conf.get('plugin_dir', plugin_dir)

    # Iterate to create each configured plugins
    for index, plugin in enumerate(plugins, 1):
        Plugin(index, prog, plugin, plugin_dir, inhibitor_prog)

def main():
    'Main entry'
    init()

    # Wait for each thread to finish (i.e. wait forever)
    for thread in Plugin.threads:
        thread.join()

if __name__ == '__main__':
    sys.exit(main())
