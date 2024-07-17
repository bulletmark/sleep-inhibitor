#!/usr/bin/python3

'Program to run plugins to inhibit system sleep/suspend.'
# Mark Blakeney, Jul 2020.

import argparse
import asyncio
import shlex
import subprocess
import sys
import time
from pathlib import Path

# Return code which indicates plugin wants to inhibit suspend
SUSP_CODE = 254

# On some non-systemd systems, systemd-inhibit emulators are used
# instead. The first found below is the one we use:
SYSTEMD_SLEEP_PROGS = (
    'elogind-inhibit',
    'systemd-inhibit',
)

TIMEMULTS = {'s': 1, 'm': 60, 'h': 3600}

def log(msg):
    print(msg, flush=True)

def conv_to_secs(val):
    'Convert given time string to float seconds'
    # Default input time value (without qualifier) is minutes
    mult = isinstance(val, str) and TIMEMULTS.get(val[-1])
    if mult:
        valf = val[:-1]
    else:
        mult = 60
        valf = val

    try:
        valf = float(valf)
    except Exception:
        sys.exit(f'Invalid time string "{val}".')

    return valf * mult

class Plugin:
    'Class to manage each plugin'
    def __init__(self, index, prog, progname, period, period_on,
                 def_what, conf, plugin_dir, inhibitor_prog):
        'Constructor'
        pathstr = conf.get('path')
        if not pathstr:
            sys.exit(f'Plugin #{index}: path must be defined')

        path = Path(pathstr)
        name = conf.get('name', path.stem)
        self.name = f'Plugin {name}'

        if not path.is_absolute():
            if not plugin_dir:
                sys.exit(f'{self.name}: path "{path}" is relative but '
                        'could not determine distribution plugin dir')

            path = plugin_dir / path

        path = path.resolve()
        if not path.exists():
            sys.exit(f'{self.name}: "{path}" does not exist')

        period_str = conf.get('period', period)
        self.period = conv_to_secs(period_str)

        period_on_str = conf.get('period_on', period_on)
        period_on = conv_to_secs(period_on_str)
        if period_on > self.period:
            period_on = self.period
            period_on_str = period_str

        self.is_inhibiting = None

        cmd = str(path)
        args = conf.get('args')
        if args:
            cmd += f' {args}'

        # The normal periodic check command
        self.cmd = shlex.split(cmd)

        whatval = conf.get('what', def_what)
        what = f' --what="{whatval}"' if whatval else ''

        # While inhibiting, we run outself again via systemd-inhibit to
        # run the plugin in a loop which keeps the inhibit on while the
        # inhibit state is returned.
        self.icmd = shlex.split(f'{inhibitor_prog}{what} --who="{progname}" '
                f'--why="{self.name}" {prog} -s {period_on} -i "{cmd}"')

        log(f'{self.name} [{path}] configured @ {period_str}/{period_on_str}')

    async def run(self):
        'Worker function which runs as a asyncio task for each plugin'
        while True:
            proc = await asyncio.create_subprocess_exec(*self.cmd)
            return_code = await proc.wait()

            while return_code == SUSP_CODE:
                if self.is_inhibiting is not True:
                    self.is_inhibiting = True
                    log(f'{self.name} is inhibiting '
                        f'suspend (return={return_code})')

                proc = await asyncio.create_subprocess_exec(*self.icmd)
                return_code = await proc.wait()

            if self.is_inhibiting is not False:
                self.is_inhibiting = False
                log(f'{self.name} is not inhibiting '
                    f'suspend (return={return_code})')

            await asyncio.sleep(self.period)

def init():
    'Program initialisation'
    # Process command line options
    opt = argparse.ArgumentParser(description=__doc__.strip())
    opt.add_argument('-c', '--config',
            help='alternative configuration file')
    opt.add_argument('-p', '--plugin-dir',
            help='alternative plugin dir')
    opt.add_argument('-P', '--package-dir', action='store_true',
            help='just show directory where sample conf/service files, '
                     'and default plugins can be found')
    opt.add_argument('-s', '--sleep', type=float, help=argparse.SUPPRESS)
    opt.add_argument('-i', '--inhibit', help=argparse.SUPPRESS)
    args = opt.parse_args()

    base_dir = Path(__file__).resolve().parent

    if args.package_dir:
        log(base_dir)
        sys.exit()

    # This instance may be a child invocation merely to run and check
    # the plugin while it is inhibiting.
    if args.inhibit:
        cmd = shlex.split(args.inhibit)
        while True:
            time.sleep(args.sleep)
            res = subprocess.run(cmd)
            if res.returncode != SUSP_CODE:
                sys.exit(res.returncode)

    # Don't run if this system does not support sleep
    pstate = Path('/sys/power/state')
    if not pstate.exists() or not pstate.read_text().strip():
        sys.exit('System does not support any sleep states, quitting.')

    prog = Path(sys.argv[0]).resolve()
    progname = prog.stem.replace('_', '-')

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
        log(f'{progname} using {iprog}, {vers}')
        inhibitor_prog = iprog

    if not inhibitor_prog:
        opts = ' or '.join(SYSTEMD_SLEEP_PROGS)
        sys.exit(f'No systemd-inhibitor app installed from one of {opts}.')

    # Determine config file path
    cname = progname + '.conf'
    cfile = Path(args.config).expanduser() if args.config else \
            Path(f'/etc/{cname}')

    if not cfile.exists():
        err = f'Configuration file {cfile} does not exist.'
        if not args.config:
            err += f' Copy {base_dir}/{cname} to /etc and edit appropriately.'
        sys.exit(err)

    from ruamel.yaml import YAML  # type: ignore
    conf = YAML(typ='safe').load(cfile)

    plugins = conf.get('plugins')
    if not plugins:
        sys.exit('No plugins configured')

    # Work out plugin dir
    plugin_dir = base_dir / 'plugins'
    plugin_dir = str(plugin_dir) if plugin_dir.is_dir() else None
    plugin_dir = args.plugin_dir or conf.get('plugin_dir', plugin_dir)

    # Get some global defaults
    period = conf.get('period', '5m')
    period_on = conf.get('period_on', period)
    what = conf.get('what')

    # Iterate to create each configured plugins
    return [Plugin(index, prog, progname, period, period_on, what, plugin,
                   plugin_dir, inhibitor_prog)
            for index, plugin in enumerate(plugins, 1)]

async def run(tasks):
    'Wait for each plugin task to finish (i.e. wait forever)'
    await asyncio.gather(*(t.run() for t in tasks))

def main():
    'Main entry'
    tasks = init()
    asyncio.run(run(tasks))

if __name__ == '__main__':
    main()
