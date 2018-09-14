#!/usr/bin/env python3
# Usage {{{1
"""
Embalm Backups

Backs up the contents of a file hierarchy.  A front end for Duplicity's
encrypted incremental backup utility.

Usage:
    embalm [options] [<command> [<args>...]]

Options:
    -h, --help                        Output basic usage information.
    -c <cfgname>, --config <cfgname>  Specifies the configuration to use.
    -n, --narrate                     Send embalm and Duplicity narration to stdout.
    -t, --trial-run                   Run Duplicity in dry run mode.
    -v, --verbose                     Make Duplicity more verbose.

Commands:
{commands}

Use 'embalm help <command>' for information on a specific command.
Use 'embalm help' for list of available help topics.
"""

# License {{{1
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/.


# Imports {{{1
from .command import Command
from .settings import Settings, EMBALM_LOG_FILE
from inform import Inform, Error, cull, fatal, display, terminate, os_error
from docopt import docopt

# Main {{{1
def main():
    with Inform() as inform:
        # read command line
        cmdline = docopt(
            __doc__.format(commands=Command.summarize()),
            options_first=True
        )
        config = cmdline['--config']
        command = cmdline['<command>']
        args = cmdline['<args>']
        options = cull([
            'verbose' if cmdline['--verbose'] else '',
            'narrate' if cmdline['--narrate'] else '',
            'trial-run' if cmdline['--trial-run'] else '',
        ])
        if cmdline['--narrate']:
            inform.narrate = True

        try:
            cmd, name = Command.find(command)

            with Settings(config, cmd.REQUIRES_EXCLUSIVITY) as settings:
                cmd.execute(name, args, settings, options)

        except KeyboardInterrupt:
            display('Terminated by user.')
        except Error as err:
            err.terminate()
        except OSError as err:
            fatal(os_error(err))
        terminate()
