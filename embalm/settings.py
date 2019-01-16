# Settings

# License {{{1
# Copyright (C) 2016 Kenneth S. Kundert
#
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
from .collection import Collection
from .preferences import (
    ARCHIVE_DIR,
    CONFIG_DIR,
    DEFAULT_COMMAND,
    DEFAULT_WORKING_DIR,
    DUPLICITY_LOG_FILE,
    EMBALM_LOG_FILE,
    FULL_DATE_FILE,
    INCR_DATE_FILE,
    KNOWN_SETTINGS,
    LOCK_FILE,
    PROGRAM_NAME,
    RESTORE_DIR,
    SETTINGS_FILE,
)
from .python import PythonFile
from .utilities import gethostname, getusername
from shlib import cd, mkdir, Run, to_path
from inform import (
    Error,
    conjoin, full_stop, get_informer, is_str, narrate, warn,
)
from textwrap import dedent
from appdirs import user_config_dir
import arrow
import os


# Utilities {{{1
hostname = gethostname()
username = getusername()

# Settings class {{{1
class Settings:
    # Constructor {{{2
    def __init__(self, name=None, requires_exclusivity=True):
        self.requires_exclusivity = requires_exclusivity
        self.settings = {}
        self.read(name)
        self.check()

    # read() {{{2
    def read(self, name=None, path=None):
        """Recursively read configuration files.

        name (str):
            Name of desired configuration. Passed only when reading the top level
            settings file. Default is the default configuration as specified in the
            settings file, or if that is not specified then the first configuration
            given is used.
        path (str):
            Full path to settings file. Should not be given for the top level
            settings file (SETTINGS_FILE in CONFIG_DIR).
        """

        if path:
            settings = PythonFile(path).run()
            parent = path.parent
            includes = Collection(settings.get('include'))
        else:
            # this is generic settings file
            parent = CONFIG_DIR
            pf = PythonFile(parent, SETTINGS_FILE)
            settings_filename = pf.path
            settings = pf.run()
            configs = Collection(settings.get('configuration_files', ''))
            default = settings.get('default_configuration')
            if not name:
                name = default
            if name:
                if name not in configs:
                    raise Error(
                        'unknown configuration.',
                        culprit=(settings_filename, 'configuration_files', name)
                    )
                config = name
            else:
                if len(configs) > 1:
                    config = configs[0]
                else:
                    raise Error(
                        'no known configurations.',
                        culprit=(settings_filename, 'configuration_files')
                    )
            settings['config_name'] = config
            self.config_name = config
            includes = Collection(settings.get('include'))
            includes = [config] + list(includes.values())

        self.settings.update(settings)

        for include in includes:
            path = to_path(parent, include)
            self.read(path=path)

    # check() {{{2
    def check(self):
        # gather the string valued settings together (can be used by resolve)
        self.str_settings = {k:v for k, v in self.settings.items() if is_str(v)}

        # complain about required settings that are missing
        missing = []
        for each in [
            'dest_server', 'dest_dir', 'src_dir', 'ssh_backend_method',
        ]:
            if not self.settings.get(each):
                missing.append(each)
        if missing:
            missing = conjoin(missing)
            self.fail(f'{missing}: no value given.')

        # default the working_dir if it was not specified
        working_dir = self.settings.get('working_dir')
        if not working_dir:
            working_dir = self.resolve(DEFAULT_WORKING_DIR)
            self.settings['working_dir'] = working_dir
            self.str_settings['working_dir'] = working_dir

        # check the ssh_backend_method
        if self.ssh_backend_method not in ['option', 'protocol']:
            self.fail(
                f'{self.ssh_backend_method}:',
                'invalid value given for ssh_backend_method.',
            )

        # add the working directory to excludes
        excludes = self.settings.get('excludes', [])
        excludes.append(self.working_dir)
        self.settings['excludes'] = excludes

    # resolve {{{2
    def resolve(self, value):
        try:
            resolved = value.format(
                host_name=hostname, user_name=username, prog_name=PROGRAM_NAME,
                **self.str_settings
            )
        except KeyError as e:
            raise Error('unknown setting.', culprit=e)
        if resolved != value:
            resolved = self.resolve(resolved)
        return resolved

    # handle errors {{{2
    def fail(self, *msg, comment=''):
        msg = full_stop(' '.join(str(m) for m in msg))
        try:
            if self.notify:
                Run(
                    ['mail', f'-s "{PROGRAM_NAME}: {msg}"', self.notify],
                    stdin=dedent(f'''
                        {msg}
                        {comment}
                        config = {self.config_name}
                        source = {hostname}:{self.src_dir}
                        destination = {self.dest_server}:{self.dest_dir}
                    ''').lstrip(),
                    modes='soeW'
                )
        except OSError as e:
            pass
        try:
            if self.notifier:
                Run(
                    self.notifier.format(
                        msg=msg, host_name=hostname,
                        user_name=username, prog_name=PROGRAM_NAME,
                    ),
                    modes='soeW'
                )
        except OSError as e:
            pass
        except KeyError as e:
            warn('unknown key.', culprit=(self.settings_file, 'notifier', e))
        raise Error(msg)

    # get resolved value {{{2
    def value(self, name, default=''):
        """Gets fully resolved value of string setting."""
        return self.resolve(self.settings.get(name, default))

    # get resolved values {{{2
    def values(self, name):
        """Iterate though fully resolved values of a collection setting."""
        for value in Collection(self.settings.get(name)):
            yield self.resolve(value)

    # get attribute {{{2
    def __getattr__(self, name):
        return self.settings.get(name)

    # iterate through settins {{{2
    def __iter__(self):
        for key in sorted(self.settings.keys()):
            yield key, self.settings[key]

    # enter {{{2
    def __enter__(self):
        # change to working directory
        working_dir = self.value('working_dir')
        if not working_dir:
            working_dir = self.resolve(DEFAULT_WORKING_DIR)
        self.working_dir = to_path(working_dir)
        mkdir(self.working_dir)
        narrate('changing to working_dir:', working_dir)
        self.starting_dir = cd(self.working_dir).starting_dir

        # resolve src and dest directories
        src_dir = self.resolve(self.src_dir)
        self.src_dir = to_path(src_dir)
        dest_dir = self.resolve(self.dest_dir)
        self.dest_dir = to_path(dest_dir)

        # resolve other files and directories
        config_dir = self.resolve(CONFIG_DIR)
        self.config_dir = to_path(config_dir, config_dir)

        logfile = self.resolve(EMBALM_LOG_FILE)
        self.logfile = to_path(working_dir, logfile)

        incr_date_file = self.resolve(INCR_DATE_FILE)
        self.incr_date_file = to_path(working_dir, incr_date_file)

        full_date_file = self.resolve(FULL_DATE_FILE)
        self.full_date_file = to_path(working_dir, full_date_file)

        restore_dir = self.resolve(RESTORE_DIR)
        self.restore_dir = to_path(working_dir, restore_dir)

        archive_dir = self.resolve(ARCHIVE_DIR)
        self.archive_dir = to_path(working_dir, archive_dir)

        # perform locking
        if self.requires_exclusivity:
            # check for existance of lockfile
            lockfile = self.lockfile = to_path(working_dir, LOCK_FILE)
            if lockfile.exists():
                raise Error(f'currently running (see {lockfile} for details).')

            # create lockfile
            now = arrow.now()
            pid = os.getpid()
            lockfile.write_text(dedent(f'''
                started = {now!s}
                pid = {pid}
            ''').lstrip())

        # open logfile
        get_informer().set_logfile(self.logfile)

        return self

    # exit {{{2
    def __exit__(self, exc_type, exc_val, exc_tb):
        # delete lockfile
        if self.requires_exclusivity:
            self.lockfile.unlink()

